#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phone scanner module - handles Android and iOS device scanning.
- cli: Command path (adb for Android, pymobiledevice3 for iOS)
- run_command(): Returns subprocess.Popen object
- catch_err(): Takes Popen object, waits & returns string output
"""

from math import perm
import os
import json
import shlex
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional, List, Tuple, Dict, Any

from isdi.config import get_config

from . import blocklist
from . import parse_dump
from .android_permissions import all_permissions
from .runcmd import catch_err, run_command

cfg = get_config()


class AppScanner:
    """Base class for device scanners (Android/iOS)."""

    app_info_conn: Optional[sqlite3.Connection] = None

    def __init__(self, dev_type: str, cli: str):
        """
        Initialize scanner.

        Args:
            dev_type: 'android', 'ios', or 'test'
            cli: Command path (e.g., 'adb' or 'pymobiledevice3')
        """
        assert dev_type in cfg.DEV_SUPPORTED, f"Device type {dev_type} not supported"
        self.device_type: str = dev_type
        self.cli: str = cli
        self.ddump: Optional[parse_dump.PhoneDump] = None

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

    def get_apps(self, serialno: str) -> List[str]:
        """Return list of installed app package IDs."""
        raise NotImplementedError()

    def get_system_apps(self, serialno: str) -> List[str]:
        """Return list of system app package IDs (Android only)."""
        if not self.ddump:
            return []
        return self.ddump.system_apps()

    def get_offstore_apps(self, serialno: str) -> List[str]:
        """Return list of offstore/sideloaded app package IDs (Android only)."""
        if not self.ddump:
            return []
        return self.ddump.offstore_apps()

    def get_app_titles(self, serialno: str) -> Dict[str, str]:
        """Return dict of app package IDs and titles: {appId: title}."""
        return {}

    def dump_path(self, serial: str) -> str:
        """Get the file path for a device's dump."""
        hmac_serial = cfg.hmac_serial(serial)
        fkind = "json" if self.device_type == "ios" else "txt"
        return os.path.join(cfg.DUMP_DIR, f"{hmac_serial}_{self.device_type}.{fkind}")

    def _load_dump(self, serialno: str) -> Optional[parse_dump.PhoneDump]:
        """Load device dump from file, creating it if needed."""
        if isinstance(self.ddump, parse_dump.PhoneDump):
            return self.ddump

        dumpf = self.dump_path(serialno)
        if not os.path.exists(dumpf):
            if not self._dump_phone(serialno):
                return None

        try:
            if self.device_type == "android":
                self.ddump = parse_dump.AndroidDump(dumpf)
            elif self.device_type == "ios":
                self.ddump = parse_dump.IosDump(dumpf)
            return self.ddump
        except Exception as e:
            logging.error(f"Error loading dump {dumpf}: {e}")
            return None

    def _dump_phone(self, serial: str) -> bool:
        """Dump device info by running shell script."""
        dumpf = self.dump_path(serial)
        os.makedirs(os.path.dirname(dumpf), exist_ok=True)

        # Resolve script path
        script_path = cfg.SCRIPT_DIR / f"{self.device_type}_scan.sh"
        if not script_path.exists():
            logging.error(f"Script not found: {script_path}")
            return False

        logging.info(f"Dumping {self.device_type} device {serial}...")

        # Run script: bash script.sh <serial> <output_file>
        p = run_command(
            "bash {script} {ser} {dump_file}",
            script=str(script_path),
            ser=serial,
            dump_file=dumpf,
            nowait=False,
        )

        # run_command() with nowait=False already waits and sets returncode
        if p.returncode != 0:
            logging.error(f"Dump failed with returncode {p.returncode}")
            return False

        logging.info(f"Dump completed successfully: {dumpf}")
        return os.path.exists(dumpf)

    def get_multiple_app_details(self, serialno: str, appids: List[str]) -> Dict[str, Tuple[Dict, Dict]]:
        """Get details for multiple apps at once, returning dict keyed by appId."""

        def _process_app_row(appid: str, d: Dict) -> Tuple[Dict, Dict]:
            permissions = d.get("permissions")
            if isinstance(permissions, str):
                d["permissions"] = [p.strip() for p in permissions.split(",") if p.strip()]
            elif not permissions:
                d["permissions"] = []

            description = ""
            for col in ("description", "description_html", "descriptionhtml", "summary"):
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

            d["descriptionHTML"] = description
            d.setdefault("summary", d.get("title", ""))

            info = self.ddump.info(appid) if self.ddump else None
            return d, info or {}

        if not appids:
            return {}

        if not self.ddump:
            self._load_dump(serialno)

        if not AppScanner.app_info_conn:
            return {appid: ({}, {}) for appid in appids}

        conn = AppScanner.app_info_conn
        if conn.row_factory is None:
            conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ",".join("?" * len(appids))
        cur.execute(f"SELECT * FROM apps WHERE appid IN ({placeholders})", appids)

        details: Dict[str, Tuple[Dict, Dict]] = {}
        for row in cur.fetchall():
            d = dict(row)
            appid = d.get("appid") or d.get("appId") or ""
            if appid:
                details[appid] = _process_app_row(appid, d)

        for appid in appids:
            details.setdefault(appid, ({}, {}))
        return details


    def app_details(self, serialno: str, appid: str) -> Tuple[Dict, Dict]:
        """Get detailed info for an app."""
        details = self.get_multiple_app_details(serialno, [appid])
        return details.get(appid, ({}, {}))

    def find_spyapps(self, serialno: str) -> Dict[str, Dict[str, Any]]:
        """
        Optimized find_spyapps for iOS that caches app titles lookup.
        
        The original isdi.scanner.find_spyapps calls get_app_titles() inside the loop
        for iOS, causing it to be called once per app. This optimized version
        pre-loads app titles once and reuses them.
        """
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

        # Pre-load app titles once for iOS instead of in the loop
        app_titles_cache = None
        if self.device_type == "ios":
            try:
                app_titles_cache = self.get_app_titles(serialno)
            except Exception as e:
                logging.warning(f"Failed to get app titles cache: {e}")
                app_titles_cache = {}

        # Convert to dict with appId as key
        result = {}
        for app in flagged_apps:
            appid = app.get("appId", "")
            if not appid:
                continue
            title = app.get("title", "") or ""
            flags = app.get("flags", [])

            # Get app titles from database (Android)
            if self.device_type == "android" and AppScanner.app_info_conn and not title:
                try:
                    cursor = AppScanner.app_info_conn.cursor()
                    cursor.execute("SELECT title FROM apps WHERE appid = ?", (appid,))
                    row = cursor.fetchone()
                    if row:
                        title = row[0] or ""
                except Exception as e:
                    logging.error(f"Error getting title for {appid}: {e}")
            elif self.device_type == "ios" and app_titles_cache:
                # Use cached titles from iOS dump (loaded once, not in loop)
                title = app_titles_cache.get(appid, "") or title

            # ASCII encode/decode to handle special characters
            title = title.encode("ascii", errors="ignore").decode("ascii")

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
        super().__init__("android", cfg.ADB_PATH)

    def setup(self) -> None:
        """Initialize ADB server."""
        p = run_command("{cli} kill-server; {cli} start-server", cli=self.cli)
        if p.returncode != 0:
            logging.error(f"ADB setup failed with returncode {p.returncode}")

    def devices(self) -> List[str]:
        """Get list of connected Android devices."""
        cmd = "{cli} devices | tail -n +2"
        p = run_command(cmd, cli=self.cli)
        output = catch_err(p, cmd=cmd).strip()

        devices = []
        for line in output.split("\n"):
            parts = line.split()
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def get_apps(self, serialno: str) -> List[str]:
        """Get installed apps from dump."""
        result = self._load_dump(serialno)
        if not result or not self.ddump:
            logging.error(f"Cannot load dump for {serialno}")
            return []
        return self.ddump.all_apps()

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
                cmd = "{cli} -s {serial} shell getprop {prop}"
                p = run_command(cmd, cli=self.cli, serial=serial, prop=prop)
                output = catch_err(p, cmd=cmd).strip()
                m[key] = output or "Unknown"

            m["last_full_charge"] = datetime.now().isoformat()

            info_str = f"{m['brand']} {m['model']} (Android {m['version']})"
            return info_str, m
        except Exception as e:
            logging.error(f"Error getting device info: {e}")
            return "Unknown Device", {}

    def isrooted(self, serial: str) -> Tuple[bool, List[str]]:
        """Check if Android device is rooted."""
        root_indicators = [
            ("su", "command -v su"),
            ("frida", "ps -A | grep frida"),
            ("magisk", "ls -la /data/adb/magisk"),
        ]

        reasons: List[str] = []
        for name, cmd_str in root_indicators:
            cmd = "{cli} -s {serial} shell '{cmd_str}'"
            try:
                p = run_command(cmd, cli=self.cli, serial=serial, cmd_str=cmd_str)
                output = catch_err(p, cmd=cmd, msg_on_err=f"not found {name}").strip()
                if output and "not found" not in output.lower():
                    reasons.append(f"Found {name}")
            except Exception as e:
                logging.debug(f"Root check failed: {e}")

        return len(reasons) > 0, reasons

    def uninstall(self, serial: str, appid: str) -> bool:
        """Uninstall an app."""
        cmd = "{cli} -s {serial} uninstall {appid}"
        p = run_command(cmd, cli=self.cli, serial=serial, appid=appid)
        output = catch_err(p, cmd=cmd)
        return "Success" in output


class IosScanner(AppScanner):
    """Scanner for iOS devices using pymobiledevice3."""

    def __init__(self):
        super().__init__("ios", cfg.LIBIMOBILEDEVICE_PATH)

    def devices(self) -> List[str]:
        """Get list of connected iOS devices."""
        cmd = "{cli} usbmux list"
        p = run_command(cmd, cli=self.cli)
        output = catch_err(p, cmd=cmd).strip()

        try:
            if not output:
                return []
            data = json.loads(output)
            return [d.get("Identifier", "") for d in data if "Identifier" in d]
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse device list: {e}. output={output}")
            return []

    def get_apps(self, serialno: str) -> List[str]:
        """Get installed apps from dump."""
        if not self._dump_phone(serialno):
            logging.error("Failed to dump iOS device")
            return []

        result = self._load_dump(serialno)
        if not result or not self.ddump:
            logging.error("Failed to load iOS dump")
            return []

        return self.ddump.installed_apps()

    def get_app_titles(self, serialno: str) -> Dict[str, str]:
        """Get iOS app titles as dict: {appId: title}."""
        if not self.ddump:
            return {}
        titles_df = self.ddump.installed_apps_titles()
        # If it returns a DataFrame-like object, convert to dict
        # if hasattr(titles_df, 'to_dict'):
        #     # It's a DataFrame, convert to our dict format
        #     result = {}
        #     for appid, title in zip(titles_df.get('appId', []), titles_df.get('title', [])):
        #         result[appid] = title
        #     return result
        if isinstance(titles_df, dict):
            # Already a dict
            return titles_df
        else:
            # Try to iterate
            try:
                return {
                    item.get("appId"): item.get("title") for item in titles_df if item
                }
            except:
                return {}

    def device_info(self, serial: str) -> Tuple[str, Dict]:
        """Get iOS device info."""
        if not self._dump_phone(serial):
            return "Unknown iOS Device", {}

        self._load_dump(serial)
        if self.ddump:
            return self.ddump.device_info()
        return "Unknown iOS Device", {}

    def isrooted(self, serial: str) -> Tuple[bool, List[str]]:
        """Check if iOS device is jailbroken."""
        # Jailbreak detection not yet implemented
        return False, ["Jailbreak detection not implemented"]

    def uninstall(self, serial: str, appid: str) -> bool:
        """Uninstall an app."""
        cmd = "{cli} apps uninstall --udid {serial} {appid}"
        p = run_command(cmd, cli=self.cli, serial=serial, appid=appid)
        output = catch_err(p, cmd=cmd)
        return "Success" in output or "uninstalled" in output.lower()


class TestScanner(AppScanner):
    """Test scanner using mock data."""

    def __init__(self):
        super().__init__("android", "test")

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
