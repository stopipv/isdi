"""Know which phones are plugged in without polling the device tools.

The home page asks for the attached phones every few seconds. Answering by
running `adb devices` and opening a lockdown session to every iPhone each time
costs real CPU on small machines (a thin client can spend most of a core on it).
Instead, two background threads subscribe to the device daemons and keep the
current list in memory:

* `AdbWatcher` keeps `adb track-devices -l` running; adb writes the full device
  list whenever it changes and is silent otherwise.
* `UsbmuxWatcher` sends usbmuxd a `Listen` request; usbmuxd then pushes Attached,
  Detached and Paired messages. Each newly attached iPhone is asked for its
  model once. Only while an iPhone is waiting for "Trust" is it re-checked,
  every few seconds.

When the daemon is not running (usbmuxd not installed, adb missing) a watcher
retries with backoff and logs once, not every few seconds. `snapshot()` returns
None before the first answer, and for adb while it is down; callers then list
devices directly. Without usbmuxd it returns [] (no iPhones), since listing
directly would fail the same way.
"""

import asyncio
import logging
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional, Sequence

RETRY_MIN = 2.0
RETRY_MAX = 30.0
UNTRUSTED_RECHECK = 3.0


class _Watcher(threading.Thread):
    def __init__(self, name: str):
        super().__init__(name=name, daemon=True)
        self._lock = threading.Lock()
        self._devices: Optional[List[Dict]] = None
        self._stopping = threading.Event()
        self._failing_logged = False

    def snapshot(self) -> Optional[List[Dict]]:
        """The current device records, or None if there is no live subscription."""
        with self._lock:
            return None if self._devices is None else list(self._devices)

    def _set(self, devices: Optional[List[Dict]]) -> None:
        with self._lock:
            self._devices = devices

    # What snapshot() says while the daemon is unreachable: None lets callers
    # poll the tool instead; [] means "no devices" (polling would fail the same way).
    down_snapshot: Optional[List[Dict]] = None

    def _failed(self, what: str, exc: object) -> None:
        self._set(self.down_snapshot)
        if not self._failing_logged:
            logging.warning("%s: %s (retrying in the background)", what, exc)
            self._failing_logged = True

    def _recovered(self) -> None:
        if self._failing_logged:
            logging.info("%s: connected again", self.name)
            self._failing_logged = False

    def stop(self) -> None:
        self._stopping.set()


def read_frame(stream, size: int) -> Optional[bytes]:
    """Read one `track-devices` frame of `size` bytes, or None at end of stream.

    adb.exe on Windows writes "\n" as "\r\n" but counts only the "\n" in the
    length prefix, so carriage returns are dropped and not counted; otherwise
    every frame leaves bytes behind and the next length is read from the middle
    of a serial number. Device lines never contain a real "\r".
    """
    body = bytearray()
    while len(body) < size:
        chunk = stream.read(size - len(body))
        if not chunk:
            return None
        body += chunk.replace(b"\r", b"")
    return bytes(body)


class AdbWatcher(_Watcher):
    """Follow `adb track-devices -l` (each update: 4 hex digits of length, then the list)."""

    def __init__(self, adb_argv: Sequence[str], parse: Callable[[List[str]], List[Dict]]):
        super().__init__("adb-watch")
        self.adb_argv = [str(a) for a in adb_argv]
        self.parse = parse
        self.proc: Optional[subprocess.Popen] = None

    def run(self) -> None:
        delay = RETRY_MIN
        while not self._stopping.is_set():
            started = time.monotonic()
            try:
                self._follow()
            except Exception as exc:   # adb missing, unreadable output
                self._failed("Could not watch Android devices", exc)
            else:
                # adb exits when its server is killed or restarted (AndroidScanner.setup).
                self._failed("adb track-devices ended", f"exit code {self.proc and self.proc.poll()}")
            delay = RETRY_MIN if time.monotonic() - started > 60 else min(delay * 2, RETRY_MAX)
            self._stopping.wait(delay)

    def _follow(self) -> None:
        self.proc = subprocess.Popen(
            [*self.adb_argv, "track-devices", "-l"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        try:
            out = self.proc.stdout
            while not self._stopping.is_set():
                head = out.read(4)
                if len(head) < 4:
                    return
                size = int(head, 16)
                body = read_frame(out, size)
                if body is None:
                    return
                self._set(self.parse(body.decode("utf-8", "replace").splitlines()))
                self._recovered()
        finally:
            if self.proc.poll() is None:
                self.proc.kill()
            self.proc.wait()

    def stop(self) -> None:
        super().stop()
        if self.proc and self.proc.poll() is None:
            self.proc.kill()


class UsbmuxWatcher(_Watcher):
    """Subscribe to usbmuxd and keep each attached iPhone's lockdown short_info."""

    down_snapshot: Optional[List[Dict]] = []   # no usbmuxd: no iPhone can be listed

    def __init__(self, describe):
        """describe: async (MuxDevice) -> record, e.g. IosLibrary.describe."""
        super().__init__("usbmux-watch")
        self.describe = describe
        self._info: Dict[str, Dict] = {}   # serial -> record

    def run(self) -> None:
        asyncio.run(self._main())

    async def _main(self) -> None:
        from pymobiledevice3.usbmux import create_mux

        while not self._stopping.is_set():
            mux = None
            try:
                mux = await create_mux()
                await mux.listen()
                self._recovered()
                await self._follow(mux)
            except Exception as exc:   # usbmuxd not running, or it went away
                self._info.clear()
                self._failed(
                    "usbmuxd is not running (it normally starts when an iPhone is plugged in; "
                    "if iPhones never show up, install the usbmuxd package)", type(exc).__name__)
            finally:
                if mux is not None:
                    await mux.close()
            # No backoff: Debian/Ubuntu start usbmuxd only while an iPhone is
            # plugged in, so a missing socket is the normal idle state, and
            # trying to connect to it is a single cheap system call.
            await asyncio.sleep(RETRY_MIN)

    async def _follow(self, mux) -> None:
        # usbmuxd answers Listen with an Attached message for every phone already
        # plugged in, so mux.devices fills up without a separate ListDevices.
        loop = asyncio.get_running_loop()
        read = loop.create_task(mux.receive_device_state_update())
        try:
            while not self._stopping.is_set():
                await self._refresh(mux.devices)
                untrusted = any(r.get("_state") == "untrusted" for r in self._info.values())
                # Never cancel a read mid-message: wait on it with a timeout instead.
                done, _ = await asyncio.wait({read}, timeout=UNTRUSTED_RECHECK if untrusted else 60)
                if read in done:
                    read.result()   # raises if usbmuxd closed the connection
                    read = loop.create_task(mux.receive_device_state_update())
                # Ask untrusted phones again: on a timeout, or after any message
                # (usbmuxd sends "Paired" when a phone has just been trusted).
                for serial, rec in list(self._info.items()):
                    if rec.get("_state") == "untrusted":
                        del self._info[serial]
        finally:
            read.cancel()

    async def _refresh(self, mux_devices) -> None:
        # One entry per phone: a phone can be listed over USB and over Wi-Fi.
        by_serial = {}
        for dev in mux_devices:
            if dev.serial not in by_serial or dev.connection_type == "USB":
                by_serial[dev.serial] = dev
        for serial in list(self._info):
            if serial not in by_serial:
                del self._info[serial]
        for serial, dev in by_serial.items():
            if serial not in self._info:
                self._info[serial] = await self.describe(dev)
        self._set(list(self._info.values()))


_started: Dict[str, _Watcher] = {}
_start_lock = threading.Lock()


def get(kind: str, factory: Callable[[], _Watcher]) -> _Watcher:
    """The running watcher for kind ("android"/"ios"), starting it on first use."""
    with _start_lock:
        w = _started.get(kind)
        if w is None or not w.is_alive():
            w = factory()
            w.start()
            _started[kind] = w
        return w
