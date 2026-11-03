"""The four things ISDi asks of an iPhone, with two ways of doing them.

* `IosLibrary` (Linux, macOS, Windows): pymobiledevice3 as a Python library,
  in this process. No subprocesses, and errors come back as exceptions.
* `IosCli` (limited support: WSL, Termux): the pymobiledevice3 command-line
  tool. WSL cannot reach USB devices, so it runs the Windows `pymobiledevice3.exe`;
  Termux runs it through ISDi's usbmuxd-path wrapper. The afc2 jailbreak check
  is not available this way.

Both produce the same dump file, {"apps": {...}, "devinfo": {...}}, encoded the way
`pymobiledevice3 apps list` / `lockdown info` print it, so stored dumps and
parse_dump are unaffected by which one ran.
"""

import asyncio
import datetime
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Sequence

from isdi.scanner import runcmd

LIST_TIMEOUT = 30
DUMP_TIMEOUT = 300
AFC2_TIMEOUT = 5.0


class IosDeviceError(RuntimeError):
    pass


def json_default(obj: Any) -> Any:
    """Same encoding as pymobiledevice3's own JSON output (cli_common.default_json_encoder)."""
    if isinstance(obj, bytes):
        return {"$hex": obj.hex()}
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Cannot encode {type(obj).__name__}")


def run_async(coro, timeout: float):
    """Run a coroutine from ISDi's (synchronous, threaded) code."""
    async def bounded():
        return await asyncio.wait_for(coro, timeout)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(bounded())
    with ThreadPoolExecutor(max_workers=1) as pool:   # called from inside a loop
        return pool.submit(asyncio.run, bounded()).result()


class IosLibrary:
    """pymobiledevice3 11.x, used directly."""

    name = "library"
    supports_afc2 = True

    @staticmethod
    async def describe(device) -> Dict[str, Any]:
        """lockdown short_info for a usbmux MuxDevice, or an "untrusted" placeholder."""
        from pymobiledevice3.lockdown import create_using_usbmux

        try:
            lockdown = await create_using_usbmux(
                device.serial, autopair=False, connection_type=device.connection_type)
        except Exception as exc:
            # Plugged in but locked, never trusted, or the trust prompt is pending.
            logging.info("iOS device %s not ready: %s", device.serial, type(exc).__name__)
            return {"Identifier": device.serial, "_state": "untrusted"}
        try:
            return lockdown.short_info
        finally:
            await lockdown.close()

    async def _list(self) -> List[Dict[str, Any]]:
        from pymobiledevice3 import usbmux

        return [await self.describe(device) for device in await usbmux.list_devices()]

    def list_devices(self) -> List[Dict[str, Any]]:
        try:
            return run_async(self._list(), LIST_TIMEOUT)
        except Exception as exc:
            # usbmuxd not running / Apple Mobile Device Support missing, or a timeout.
            logging.warning("Could not list iOS devices: %s: %s", type(exc).__name__, exc)
            return []

    async def _dump(self, serial: str) -> Dict[str, Any]:
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.installation_proxy import InstallationProxyService

        lockdown = await create_using_usbmux(serial=serial, autopair=False)
        try:
            async with InstallationProxyService(lockdown=lockdown) as proxy:
                apps = await proxy.get_apps(application_type="Any", calculate_sizes=False)
            return {"apps": apps, "devinfo": lockdown.all_values}
        finally:
            await lockdown.close()

    def dump(self, serial: str) -> Dict[str, Any]:
        try:
            return run_async(self._dump(serial), DUMP_TIMEOUT)
        except Exception as exc:
            raise IosDeviceError(f"{type(exc).__name__}: {exc}") from exc

    async def _uninstall(self, serial: str, appid: str) -> None:
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.installation_proxy import InstallationProxyService

        lockdown = await create_using_usbmux(serial=serial, autopair=False)
        try:
            async with InstallationProxyService(lockdown=lockdown) as proxy:
                await proxy.uninstall(appid)
        finally:
            await lockdown.close()

    def uninstall(self, serial: str, appid: str) -> bool:
        try:
            run_async(self._uninstall(serial, appid), 120)
            return True
        except Exception as exc:
            logging.warning("iOS uninstall of %s failed: %s: %s", appid, type(exc).__name__, exc)
            return False

    async def _afc2(self, serial: str) -> bool:
        from pymobiledevice3.lockdown import create_using_usbmux

        lockdown = await create_using_usbmux(serial=serial, autopair=False)
        try:
            service = await lockdown.start_lockdown_service("com.apple.afc2")
            await service.close()
            return True
        finally:
            await lockdown.close()

    def afc2_active(self, serial: str) -> Optional[bool]:
        """True if the jailbreak-only afc2 service starts, False if not, None on timeout."""
        try:
            return run_async(self._afc2(serial), AFC2_TIMEOUT)
        except asyncio.TimeoutError:
            return None
        except Exception as exc:
            logging.info("afc2 not available on %s: %s", serial, type(exc).__name__)
            return False


class IosCli:
    """Limited support: the pymobiledevice3 command line (WSL: the Windows .exe)."""

    name = "cli"
    supports_afc2 = False

    def __init__(self, cli: Sequence[str], env: Optional[Dict[str, str]] = None, termux: bool = False):
        self.cli = list(cli)
        self.env = env
        self.termux = termux

    def _json(self, args: List[str], timeout: float, expect: str) -> Any:
        p = runcmd.run([*self.cli, *args], env=self.env, timeout=timeout)
        out = p.stdout or ""
        # Skip anything printed before the JSON (e.g. update notices).
        start = out.find(expect)
        if p.returncode != 0 or start == -1:
            raise IosDeviceError(f"`{' '.join(args)}` failed: {(p.stderr or out).strip()[-300:]}")
        return json.loads(out[start:])

    def list_devices(self) -> List[Dict[str, Any]]:
        try:
            return self._json(["usbmux", "list"], LIST_TIMEOUT, "[")
        except (IosDeviceError, ValueError) as exc:
            logging.warning("Could not list iOS devices: %s", exc)
            return []

    def _start_termux_usbmuxd(self) -> None:
        listing = runcmd.output(["termux-usb", "-l"], timeout=10)
        try:
            devices = json.loads(listing or "[]")
        except ValueError:
            devices = []
        if devices:
            runcmd.run(["termux-usb", "-r", "-E", "-e", "usbmuxd -f -v", devices[0]], timeout=30)

    def dump(self, serial: str) -> Dict[str, Any]:
        if self.termux:
            self._start_termux_usbmuxd()
        try:
            apps = self._json(["apps", "list", "--udid", serial], DUMP_TIMEOUT, "{")
            info = self._json(["lockdown", "info", "--udid", serial], 60, "{")
        except ValueError as exc:
            raise IosDeviceError(f"Unreadable output from pymobiledevice3: {exc}") from exc
        return {"apps": apps, "devinfo": info}

    def uninstall(self, serial: str, appid: str) -> bool:
        p = runcmd.run([*self.cli, "apps", "uninstall", "--udid", serial, appid], env=self.env, timeout=120)
        return p.returncode == 0

    def afc2_active(self, serial: str) -> Optional[bool]:
        return None   # `lockdown service` opens an interactive shell; not attempted here


def get_tool(cfg):
    if cfg.PLATFORM == "wsl" or os.environ.get("PREFIX"):
        return IosCli(cfg.IOS_CLI, cfg.IOS_CLI_ENV, termux=bool(os.environ.get("PREFIX")))
    return IosLibrary()


def write_dump(path: str, dump: Dict[str, Any]) -> None:
    """Write atomically so a reader never sees a half-written dump."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(dump, fh, sort_keys=True, indent=4, default=json_default, ensure_ascii=False)
    os.replace(tmp, path)
