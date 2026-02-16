#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phone scanner module - handles Android and iOS device scanning.
- cli: Command path (adb for Android, pymobiledevice3 for iOS)
- run_command(): Returns subprocess.Popen object
- catch_err(): Takes Popen object, waits & returns string output
"""

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
import pandas as pd

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
        if self.device_type != "android" or not self.ddump:
            return []
        return self.ddump.system_apps()

    def get_offstore_apps(self, serialno: str) -> List[str]:
        """Return list of offstore/sideloaded app package IDs (Android only)."""
        if self.device_type != "android" or not self.ddump:
            return []
        return self.ddump.offstore_apps()

    def get_app_titles(self, serialno: str) -> pd.DataFrame:
        """Return DataFrame of app package IDs and titles."""
        return pd.DataFrame()

    def dump_path(self, serial: str) -> str:
        """Get the file path for a device's dump."""
        hmac_serial = cfg.hmac_serial(serial)
        fkind = 'json' if self.device_type == 'ios' else 'txt'
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

    def app_details(self, serialno: str, appid: str) -> Tuple[Dict, Dict]:
        """Get detailed info for an app."""
        if not self.ddump:
            self._load_dump(serialno)
        
        if not AppScanner.app_info_conn:
            return {}, {}
        
        # Query the database for app info
        conn = AppScanner.app_info_conn
        if conn.row_factory is None:
            conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM apps WHERE appid=?", (appid,))
        row = cur.fetchone()
        if row is None:
            logging.warning(f"No app info found for {appid}")
            return {}, {}

        d = dict(row)

        # Handle permissions - convert string to list if needed
        perm = d.get("permissions", "")
        if perm and isinstance(perm, str):
            d["permissions"] = [p.strip() for p in perm.split(",")]
        elif not perm:
            d["permissions"] = []

        # Handle description - look for various possible column names
        description = ""
        for col in ["description", "description_html", "descriptionhtml", "summary"]:
            if d.get(col):
                description = str(d[col])
                break

        if not description:
            # Try camelCase variants used in template
            for col in d.keys():
                if "description" in col.lower() or "summary" in col.lower():
                    if d.get(col):
                        description = str(d[col])
                        break

        d["descriptionHTML"] = description
        if "summary" not in d:
            d["summary"] = d.get("title", "")

        # Get device-specific info if dump is available
        info = {}
        if self.ddump:
            info = self.ddump.info(appid) or {}

        return d, info

    def find_spyapps(self, serialno: str) -> pd.DataFrame:
        """Find spyware apps using blocklist."""
        installed_apps = self.get_apps(serialno)
        if not installed_apps:
            return pd.DataFrame(columns=["title", "flags", "score", "class_", "html_flags"])
        
        # Get offstore and system apps (Android only - iOS returns empty)
        offstore = self.get_offstore_apps(serialno)
        system = self.get_system_apps(serialno)
        
        # Get app flags
        r = blocklist.app_title_and_flag(
            pd.DataFrame({"appId": installed_apps}),
            offstore_apps=offstore,
            system_apps=system,
        )
        
        r["title"] = r.title.fillna("")
        
        # Get app titles from database
        if self.device_type == "android" and AppScanner.app_info_conn:
            try:
                td = pd.read_sql(
                    "SELECT appid AS appId, title FROM apps WHERE appid IN ({})".format(
                        ",".join("?" * len(installed_apps))
                    ),
                    AppScanner.app_info_conn,
                    params=installed_apps,
                    index_col="appId",
                )
                r.set_index("appId", inplace=True)
                r.loc[td.index, "title"] = td["title"]
                r.reset_index(inplace=True)
            except Exception as e:
                logging.error(f"Error getting titles: {e}")
        elif self.device_type == "ios":
            td = self.get_app_titles(serialno)
            if not td.empty:
                r.set_index("appId", inplace=True)
                r.loc[td.index, "title"] = td["title"]
                r.reset_index(inplace=True)
        
        # Classify apps
        r["class_"] = r["flags"].apply(blocklist.assign_class)
        r["score"] = r["flags"].apply(blocklist.score)
        r["title"] = r.title.str.encode("ascii", errors="ignore").str.decode("ascii")
        r["title"] = r.title.fillna("")
        r["html_flags"] = r["flags"].apply(blocklist.flag_str)
        
        # Sort by risk score
        r.sort_values(by=["score", "appId"], ascending=[False, True], na_position="last", inplace=True)
        r.set_index("appId", inplace=True)
        
        return r[["title", "flags", "score", "class_", "html_flags"]]

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
                output = catch_err(p, cmd=cmd).strip()
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
            logging.error(f"Failed to parse device list: {e}")
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

    def get_app_titles(self, serialno: str) -> pd.DataFrame:
        """Get iOS app titles."""
        if not self.ddump:
            return pd.DataFrame()
        return self.ddump.installed_apps_titles()

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
