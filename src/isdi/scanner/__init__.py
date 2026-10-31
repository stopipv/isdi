#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phone scanner module - handles Android and iOS device scanning.
- cli: argv prefix of the device tool (adb for Android, pymobiledevice3 for iOS)
- runcmd.run()/runcmd.output(): run an argv list without a shell
"""

import os
import json
import re
import sqlite3
import logging
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional, List, Tuple, Dict, Any

from markupsafe import Markup, escape

from isdi.config import get_config

from . import blocklist
from . import parse_dump

from .android_permissions import all_permissions, get_all_accessibility_apps
from . import runcmd

cfg = get_config()

# Android package names and iOS bundle IDs: letters, digits, '.', '_', '-'.
_APPID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")




_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
# Google account databases are named after the account, e.g. alice_gmail.com.db
_DB_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+_gmail\.com")


def redact_emails(text: str) -> str:
    """Replace email addresses (and gmail-named databases) in dump output."""
    text = _EMAIL_RE.sub("<email>", text)
    return _DB_EMAIL_RE.sub("<db_email>", text)


_BR_RE = re.compile(r"&lt;br\s*/?&gt;", re.IGNORECASE)


def sanitize_description(text: str) -> Markup:
    """HTML-escape an app store description, keeping only <br> line breaks.

    Descriptions come from app-info.db, which is downloaded, so they must
    not be able to inject markup or scripts into the page.
    """
    return Markup(_BR_RE.sub("<br>", str(escape(text or ""))))


def valid_appid(appid: str) -> bool:
    """True if appid looks like an Android package name or iOS bundle ID."""
    return bool(appid) and bool(_APPID_RE.match(appid))


class AppScanner:
    """Base class for device scanners (Android/iOS)."""

    app_info_conn: Optional[sqlite3.Connection] = None

    def __init__(self, dev_type: str, cli: List[str], cli_env=None):
        """
        Initialize scanner.

        Args:
            dev_type: 'android', 'ios', or 'test'
            cli: argv prefix of the device tool (e.g., ['adb'] or ['pymobiledevice3'])
            cli_env: environment to run the tool with (None inherits)
        """
        assert dev_type in cfg.DEV_SUPPORTED, f"Device type {dev_type} not supported"
        self.device_type: str = dev_type
        self.cli: List[str] = list(cli)
        self.cli_env = cli_env
        # Parsed dumps keyed by dump file path (one per device), and when this
        # process last dumped each serial.
        self._dumps: Dict[str, parse_dump.PhoneDump] = {}
        self._dumped_at: Dict[str, float] = {}
        # When is_connected() last saw each serial connected.
        self._seen: Dict[str, float] = {}

        # Initialize database connection once
        if AppScanner.app_info_conn is None:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite connection for app info database."""
        try:
            db_path = cfg.APP_INFO_SQLITE_FILE.replace("sqlite:///", "")
            AppScanner.app_info_conn = sqlite3.connect(db_path, check_same_thread=False)
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            AppScanner.app_info_conn = None

    def setup(self) -> None:
        """Device-specific setup (e.g., ADB server)."""
        pass

    def devices(self) -> List[str]:
        """Return list of connected device serial numbers."""
        raise NotImplementedError()

    def connected_devices(self) -> List[Dict[str, str]]:
        """Return attached devices as {"serial", "label", "state"} dicts.

        state is "ready" if the device can be scanned; otherwise it says why
        not (e.g. "unauthorized" for an Android phone that has not yet
        allowed USB debugging).
        """
        return [{"serial": s, "label": s, "state": "ready"} for s in self.devices()]

    def is_connected(self, serial: str) -> bool:
        """True if serial is one of the currently connected devices.

        Every serial that comes from an HTTP request must pass this check
        before it is handed to a device tool. Listing devices can take
        seconds (pymobiledevice3), so a serial seen in the last 30 seconds is
        accepted without listing again.
        """
        if not serial:
            return False
        if time.time() - self._seen.get(serial, 0) < 30:
            return True
        listed = self.devices()
        now = time.time()
        for s in listed:
            self._seen[s] = now
        return serial in listed

    def connected_serial_for_hmac(self, hmac_serial: str) -> Optional[str]:
        """Return the connected device serial whose HMAC is hmac_serial."""
        for serial in self.devices():
            if cfg.hmac_serial(serial) == hmac_serial:
                return serial
        return None

    def get_apps(self, serialno: str) -> List[str]:
        """Return list of installed app package IDs."""
        raise NotImplementedError()

    def get_system_apps(self, serialno: str) -> List[str]:
        """Return list of system app package IDs (Android only)."""
        ddump = self._get_dump(serialno)
        return ddump.system_apps() if ddump else []

    def get_offstore_apps(self, serialno: str) -> List[str]:
        """Return list of offstore/sideloaded app package IDs (Android only)."""
        ddump = self._get_dump(serialno)
        return ddump.offstore_apps() if ddump else []

    def app_titles(
        self, serialno: str, appids: List[str], hashed: bool = False
    ) -> Dict[str, str]:
        """Names of appids from app-info.db, then app-flags.csv (unknown apps are left out).

        Reads stored data only, so it works for past scans too; serialno is
        the HMAC if hashed.
        """
        if not appids:
            return {}
        titles = {}
        conn = AppScanner.app_info_conn
        if conn:
            placeholders = ",".join("?" * len(appids))
            try:
                rows = conn.execute(
                    f"SELECT appid, title FROM apps WHERE appid IN ({placeholders})",
                    appids,
                ).fetchall()
                titles = {r[0]: r[1] for r in rows if r[1]}
            except sqlite3.Error as e:
                logging.error(f"Error getting app titles: {e}")
        return {**blocklist.titles(appids), **titles}

    def dump_path(self, serial: str, hashed: bool = False) -> str:
        """Get the file path for a device's dump.

        serial is the device serial, or its HMAC if hashed is True.
        """
        hmac_serial = serial if hashed else cfg.hmac_serial(serial)
        fkind = "json" if self.device_type == "ios" else "txt"
        return os.path.join(cfg.DUMP_DIR, f"{hmac_serial}_{self.device_type}.{fkind}")

    def _forget_dump(self, serial: str) -> None:
        self._dumps.pop(self.dump_path(serial), None)
        self._dumped_at.pop(serial, None)

    def _get_dump(
        self, serial: str, hashed: bool = False
    ) -> Optional[parse_dump.PhoneDump]:
        """Parse (or return the cached parse of) the dump file for this serial.

        Never runs device commands; returns None if there is no dump file.
        """
        dumpf = self.dump_path(serial, hashed=hashed)
        if dumpf in self._dumps:
            return self._dumps[dumpf]
        if not os.path.exists(dumpf):
            return None
        try:
            if self.device_type == "android":
                ddump = parse_dump.AndroidDump(dumpf)
            elif self.device_type == "ios":
                ddump = parse_dump.IosDump(dumpf)
            else:
                return None
        except Exception as e:
            logging.error(f"Error loading dump {dumpf}: {e}")
            return None
        self._dumps[dumpf] = ddump
        return ddump

    def _fresh_dump(
        self, serialno: str, max_age: float = 300
    ) -> Optional[parse_dump.PhoneDump]:
        """Dump the device unless this process already did so in the last max_age seconds."""
        if time.time() - self._dumped_at.get(serialno, 0) > max_age:
            if not self._dump_phone(serialno):
                return None
        return self._get_dump(serialno)

    def _dump_phone(self, serial: str) -> bool:
        """Dump device info by running shell script."""
        dumpf = self.dump_path(serial)
        os.makedirs(os.path.dirname(dumpf), exist_ok=True)

        # Delete stale JSON cache so load_file re-parses the fresh txt dump
        json_cache = dumpf.rsplit(".", 1)[0] + ".json"
        if os.path.exists(json_cache):
            os.unlink(json_cache)
        self._forget_dump(serial)

        # Resolve script path
        script_path = cfg.SCRIPT_DIR / f"{self.device_type}_scan.sh"
        if not script_path.exists():
            logging.error(f"Script not found: {script_path}")
            return False

        logging.info(f"Dumping {self.device_type} device {serial}...")

        # Run script: bash script.sh <serial> <output_file>
        p = runcmd.run(["bash", str(script_path), serial, dumpf], timeout=300)
        if p.returncode != 0:
            logging.error(f"Dump failed with returncode {p.returncode}")
            return False

        logging.info(f"Dump completed successfully: {dumpf}")
        if not os.path.exists(dumpf):
            return False
        self._dumped_at[serial] = time.time()
        return True

    def get_multiple_app_details(
        self, serialno: str, appids: List[str], hashed: bool = False
    ) -> Dict[str, Tuple[Dict, Dict]]:
        """Get details for multiple apps at once, returning dict keyed by appId.

        Device info comes from the stored dump of serialno (its HMAC if
        hashed); no device commands are run.
        """
        ddump = self._get_dump(serialno, hashed=hashed)

        def _process_app_row(appid: str, d: Dict) -> Tuple[Dict, Dict]:
            permissions = d.get("permissions")
            if isinstance(permissions, str):
                d["permissions"] = [
                    p.strip() for p in permissions.split(",") if p.strip()
                ]
            elif not permissions:
                d["permissions"] = []

            description = ""
            for col in (
                "description",
                "description_html",
                "descriptionhtml",
                "summary",
            ):
                if d.get(col):
                    description = str(d[col])
                    break
            if not description:
                description = next(
                    (
                        str(v)
                        for k, v in d.items()
                        if v and ("description" in k.lower() or "summary" in k.lower())
                    ),
                    "",
                )

            d["descriptionHTML"] = sanitize_description(description)
            info = (ddump.info(appid) if ddump else None) or {}
            if not d.get("title"):
                d["title"] = info.get("title") or appid
            d.setdefault("summary", d["title"])
            return d, info

        if not appids:
            return {}

        # Store data (title, description) from app-info.db, which only covers
        # apps of interest; apps missing from it still get the device's info.
        rows: Dict[str, Dict] = {}
        conn = AppScanner.app_info_conn
        if conn:
            if conn.row_factory is None:
                conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            placeholders = ",".join("?" * len(appids))
            cur.execute(f"SELECT * FROM apps WHERE appid IN ({placeholders})", appids)
            for row in cur.fetchall():
                d = dict(row)
                appid = d.get("appid") or d.get("appId") or ""
                if appid:
                    rows[appid] = d

        return {appid: _process_app_row(appid, rows.get(appid, {})) for appid in appids}


    def app_details(
        self, serialno: str, appid: str, hashed: bool = False
    ) -> Tuple[Dict, Dict]:
        """Get detailed info for an app."""
        details = self.get_multiple_app_details(serialno, [appid], hashed=hashed)
        return details.get(appid, ({}, {}))

    def find_spyapps(self, serialno: str) -> Dict[str, Dict[str, Any]]:
        """Installed apps of the device with their names, flags and scores."""
        installed_apps = self.get_apps(serialno)
        if not installed_apps:
            return {}

        # Get offstore and system apps (Android only - iOS returns empty)
        offstore = self.get_offstore_apps(serialno)
        system = self.get_system_apps(serialno)

        # Get app flags from blocklist
        flagged_apps = blocklist.app_title_and_flag(
            [{"appId": appid} for appid in installed_apps],
            offstore_apps=offstore,
            system_apps=system,
        )

        titles = self.app_titles(serialno, list(installed_apps))

        # Convert to dict with appId as key
        result = {}
        for app in flagged_apps:
            appid = app.get("appId", "")
            if not appid:
                continue
            title = titles.get(appid, "")
            flags = app.get("flags", [])

            # Classify and score
            score_val = blocklist.score(flags)
            class_val = blocklist.assign_class(flags)
            html_flags = blocklist.flag_str(flags)

            result[appid] = {
                "title": title,
                "flags": flags,
                "score": score_val,
                "class_": class_val,
                "html_flags": html_flags,
            }

        # Device owner detection (Android only — queries dpm list-owners on the live device)
        if self.device_type == "android" and hasattr(self, "get_device_owner_apps"):
            for appid in self.get_device_owner_apps(serialno):
                if appid in result:
                    flags = result[appid]["flags"]
                    if "device-owner" not in flags:
                        flags = flags + ["device-owner"]
                        result[appid] = {
                            **result[appid],
                            "flags": flags,
                            "score": blocklist.score(flags),
                            "class_": blocklist.assign_class(flags),
                            "html_flags": blocklist.flag_str(flags),
                        }

        # Accessibility detection (Android only)
        if self.device_type == "android" and self.ddump:
            for appid in get_all_accessibility_apps(self.ddump):
                if appid in result:
                    flags = result[appid]["flags"]
                    if "accessibility" not in flags:
                        flags = flags + ["accessibility"]
                        result[appid] = {
                            **result[appid],
                            "flags": flags,
                            "score": blocklist.score(flags),
                            "class_": blocklist.assign_class(flags),
                            "html_flags": blocklist.flag_str(flags),
                        }

        # Sort by risk score descending, then by appId ascending
        sorted_apps = sorted(result.items(), key=lambda x: (-x[1]["score"], x[0]))

        # Return as dict keyed by appId
        return {appid: app_info for appid, app_info in sorted_apps}

    def device_info(self, serial: str) -> Tuple[str, Dict]:
        """Get human-readable device info string and dict."""
        return "", {}

    def isrooted(self, serial: str) -> Tuple[bool, List[str]]:
        """Check if device is rooted/jailbroken."""
        return False, []

    def uninstall(self, serial: str, appid: str) -> bool:
        """Uninstall an app (not implemented in base class)."""
        return False


class AndroidScanner(AppScanner):
    """Scanner for Android devices using adb."""

    def __init__(self):
        super().__init__("android", [cfg.ADB_PATH])

    def _adb(self, serial: str, *args: str, timeout: float = 60) -> str:
        """Run `adb -s <serial> <args...>` and return stdout ("" on failure)."""
        return runcmd.output([*self.cli, "-s", serial, *args], timeout=timeout)

    def setup(self) -> None:
        """Initialize ADB server."""
        runcmd.run([*self.cli, "kill-server"])
        p = runcmd.run([*self.cli, "start-server"])
        if p.returncode != 0:
            logging.error(f"ADB setup failed with returncode {p.returncode}")

    def _dump_phone(self, serial: str) -> bool:
        """Dump Android device info by running adb commands directly.

        Runs adb via self.cli (cfg.ADB_PATH) so the same binary Python uses
        is used here, avoiding bash-environment adb detection issues on WSL.
        """
        dumpf = self.dump_path(serial)
        os.makedirs(os.path.dirname(dumpf), exist_ok=True)

        json_cache = dumpf.rsplit(".", 1)[0] + ".json"
        if os.path.exists(json_cache):
            os.unlink(json_cache)
        self._forget_dump(serial)

        logging.info(f"Dumping android device {serial}...")

        services = [
            "package",
            "location",
            "media.camera",
            "netpolicy",
            "mount",
            "cpuinfo",
            "dbinfo",
            "meminfo",
            "procstats",
            "batterystats",
            "netstats detail",
            "usagestats",
            "activity",
            "appops",
        ]

        def _run(*args, timeout=120) -> str:
            return runcmd.run([*self.cli, "-s", serial, *args], timeout=timeout).stdout

        try:
            with open(dumpf, "w", encoding="utf-8", errors="replace") as f:
                for svc in services:
                    f.write(f"\nDUMP OF SERVICE {svc}\n")
                    f.write(redact_emails(_run("shell", "dumpsys", *svc.split())))

                f.write("\nDUMP OF SERVICE net_stats\n")
                f.write(
                    _run(
                        "shell", "cat", "/proc/net/xt_qtaguid/stats", timeout=30
                    ).replace(" ", ",")
                )

                for ns in ("secure", "system", "global"):
                    f.write(f"\nDUMP OF SETTINGS {ns}\n")
                    f.write(redact_emails(_run("shell", "settings", "list", ns, timeout=30)))

            size = os.path.getsize(dumpf)
            if size < 5000:
                logging.error(
                    f"Android dump too small ({size} bytes) — "
                    f"{self.cli} may not be reaching device {serial}"
                )
                return False
            logging.info(f"Dump completed: {dumpf} ({size} bytes)")
            self._dumped_at[serial] = time.time()
            return True
        except Exception as e:
            logging.error(f"Android dump failed: {e}")
            return False

    def get_device_owner_apps(self, serialno: str) -> set:
        """Return package names that hold device owner privilege on the device."""
        s = self._adb(serialno, "shell", "dpm", "list-owners")
        device_owner_apps = set()
        if not s:
            return device_owner_apps
        for line in s.splitlines():
            if "DeviceOwner" in line and "admin=" in line:
                m = re.search(r"admin=([a-zA-Z0-9_.]+)/", line)
                if m:
                    device_owner_apps.add(m.group(1))
        return device_owner_apps

    def devices(self) -> List[str]:
        """Get list of connected Android devices."""
        return [d["serial"] for d in self.connected_devices() if d["state"] == "ready"]

    def connected_devices(self) -> List[Dict[str, str]]:
        """Parse `adb devices -l`, e.g. "SERIAL device usb:1-1 model:Pixel_7 ..."."""
        output = runcmd.output([*self.cli, "devices", "-l"], timeout=30)

        found = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            if state == "no":  # "no permissions (...)": adb cannot open the USB device
                state = "no permissions"
            props = dict(p.split(":", 1) for p in parts[2:] if ":" in p)
            found.append(
                {
                    "serial": serial,
                    "label": props.get("model", "Android device").replace("_", " "),
                    "state": "ready" if state == "device" else state,
                }
            )
        return found

    def get_apps(self, serialno: str) -> List[str]:
        """Get installed apps from dump."""
        # Always start with a fresh dump (_dump_phone also drops the stale JSON cache).
        ddump = self._dump_phone(serialno) and self._get_dump(serialno)
        if not ddump:
            logging.error(f"Cannot load dump for {serialno}")
            return []
        return ddump.all_apps()

    def device_info(self, serial: str) -> Tuple[str, Dict]:
        """Get Android device info."""
        m: Dict[str, str] = {}
        try:
            props = {
                "brand": "ro.product.brand",
                "model": "ro.product.model",
                "version": "ro.build.version.release",
            }

            for key, prop in props.items():
                m[key] = self._adb(serial, "shell", "getprop", prop).strip() or "Unknown"

            m["last_full_charge"] = datetime.now().isoformat()

            info_str = f"{m['brand']} {m['model']} (Android {m['version']})"
            return info_str, m
        except Exception as e:
            logging.error(f"Error getting device info: {e}")
            return "Unknown Device", {}

    def isrooted(self, serial: str) -> Tuple[bool, List[str]]:
        """Check if Android device is rooted."""
        from isdi.scanner.root_check import check_android_root

        return check_android_root(serial, self.cli)

    def uninstall(self, serial: str, appid: str) -> bool:
        """Uninstall an app."""
        if not valid_appid(appid):
            return False
        return "Success" in self._adb(serial, "uninstall", appid)


class IosScanner(AppScanner):
    """Scanner for iOS devices using pymobiledevice3."""

    def __init__(self):
        super().__init__("ios", cfg.IOS_CLI, cfg.IOS_CLI_ENV)

    def devices(self) -> List[str]:
        """Get list of connected iOS devices."""
        return [d["serial"] for d in self.connected_devices()]

    def connected_devices(self) -> List[Dict[str, str]]:
        """Parse `pymobiledevice3 usbmux list` (a JSON list of devices)."""
        output = runcmd.output(
            [*self.cli, "usbmux", "list"], env=self.cli_env, timeout=30
        ).strip()

        try:
            if not output:
                return []
            # Strip any non-JSON preamble (e.g. download warnings from pymobiledevice3)
            json_start = output.find('[')
            if json_start == -1:
                return []
            data = json.loads(output[json_start:])
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse device list: {e}. output={output}")
            return []

        found = []
        for d in data:
            if "Identifier" not in d:
                continue
            label = self._model_names().get(
                d.get("ProductType", ""), d.get("DeviceClass", "iOS device")
            )
            if d.get("ProductVersion"):
                label += f" (iOS {d['ProductVersion']})"
            found.append({"serial": d["Identifier"], "label": label, "state": "ready"})
        return found

    def _model_names(self) -> Dict[str, str]:
        """ProductType -> marketing name, e.g. "iPhone10,1" -> "iPhone 8"."""
        if not hasattr(self, "_models"):
            try:
                with open(os.path.join(cfg.STATIC_DATA, "ios_device_identifiers.json")) as fh:
                    self._models = json.load(fh)
            except (OSError, json.JSONDecodeError):
                self._models = {}
        return self._models

    def get_apps(self, serialno: str) -> List[str]:
        """Get installed apps from dump."""
        # device_info() dumps the device first in a scan; reuse that dump.
        ddump = self._fresh_dump(serialno)
        if not ddump:
            logging.error("Failed to dump or load iOS device")
            return []

        return ddump.installed_apps()

    def app_titles(
        self, serialno: str, appids: List[str], hashed: bool = False
    ) -> Dict[str, str]:
        """Names from the device's stored dump, then app-info.db."""
        ddump = self._get_dump(serialno, hashed=hashed)
        on_device = ddump.installed_apps_titles() if ddump else {}
        titles = {a: on_device[a] for a in appids if on_device.get(a)}
        missing = [a for a in appids if a not in titles]
        return {**super().app_titles(serialno, missing), **titles}

    def device_info(self, serial: str) -> Tuple[str, Dict]:
        """Get iOS device info."""
        ddump = self._fresh_dump(serial)
        if ddump:
            return ddump.device_info()
        return "Unknown iOS Device", {}

    def isrooted(self, serial: str) -> Tuple[Optional[bool], List[str]]:
        """Check if iOS device is jailbroken."""
        from isdi.scanner.root_check import check_ios_jailbreak

        ddump = self._get_dump(serial)
        apps = ddump.appinfo if ddump else []
        return check_ios_jailbreak(serial, self.cli, apps)

    def uninstall(self, serial: str, appid: str) -> bool:
        """Uninstall an app."""
        if not valid_appid(appid):
            return False
        p = runcmd.run(
            [*self.cli, "apps", "uninstall", "--udid", serial, appid],
            env=self.cli_env,
        )
        return p.returncode == 0


class TestScanner(AppScanner):
    """Test scanner using mock data."""

    def __init__(self):
        super().__init__("android", ["test"])

    def devices(self) -> List[str]:
        return ["testdevice1", "testdevice2"]

    def get_apps(self, serialno: str) -> List[str]:
        """Load test app list."""
        try:
            with open(str(cfg.TEST_APP_LIST), "r") as f:
                return f.read().strip().split("\n")
        except Exception as e:
            logging.error(f"Cannot load test apps: {e}")
            return []

    def get_system_apps(self, serialno: str) -> List[str]:
        return self.get_apps(serialno)[:10]

    def get_offstore_apps(self, serialno: str) -> List[str]:
        return self.get_apps(serialno)[-4:]

    def uninstall(self, serial: str, appid: str) -> bool:
        return True
