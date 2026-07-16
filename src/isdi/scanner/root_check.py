from typing import Tuple, List, Optional
import logging
from isdi.scanner.runcmd import run_command, catch_err

ANDROID_ROOT_INDICATORS = [
    {
        # low confidence, easily spoofed by Magisk/KernelSU build prop editors
        "name": "build_tags",
        "cmd_str": "getprop ro.build.tags",
        "expected": "release-keys",
        "desc": "Build tags indicate a custom ROM or test build",
    },
    {
        # high confidence if found, low if not. all modern roots maintain enforcing.
        "name": "selinux_permissive",
        "cmd_str": "getenforce",
        "expected": "Enforcing",
        "desc": "SELinux status is set to Permissive instead of Enforcing",
    },
    {
        # high confidence if found, low if not. Can be spoofed
        "name": "ro_debuggable",
        "cmd_str": "getprop ro.debuggable",
        "expected": "0",
        "desc": "Kernel compiled with debug flag. All running processes are exposed to USB debugger (adb).",
    },
    {
        # same as ro_debuggable
        "name": "ro_secure",
        "cmd_str": "getprop ro.secure",
        "expected": "1",
        "desc": "ADB shell defaults to root. Any USB connection has full system access.",
    },
    {
        # high confidence, hard to spoof without re-locking the bootloader and triggering a data wipe
        "name": "bootloader_unlocked",
        "cmd_str": "getprop ro.boot.flash.locked",
        "expected": "1",
        "desc": "Bootloader is unlocked. Custom ROMs or kernels could be flashed directly.",
    },
    {
        # high confidence
        "name": "verified_boot_state",
        "cmd_str": "getprop ro.boot.verifiedbootstate",
        "expected": "green",
        "desc": "Verified boot state is compromised (orange = unlocked bootloader, yellow = self-signed OS",
    },
    {
        # i think this is pretty high confidence but not sure. not my area of expertise
        "name": "samsung_knox_warranty_bit",
        "cmd_str": "getprop ro.boot.warranty_bit",
        "expected": "0",
        "skip_if_missing": True,
        "desc": "Samsung Knox security features are permanently disabled",
    },
    {
        # high confidence if found, low if not found. systemless root hides these paths from standard shells
        "name": "su_binary",
        "cmd_str": "command -v su",
        "expected": "",
        "desc": "Superuser executable ('su') found in PATH",
    },
    {
        "name": "su_binary2",
        "cmd_str": "ls /system/bin/su /system/xbin/su /sbin/su /data/local/xbin/su /data/local/bin/su 2>/dev/null",
        "expected": "",
        "desc": "Superuser executable ('su') found in common locations",
    },
    {
        # low confidence if not found, magisk can rename itself
        "name": "root_package",
        "cmd_str": "pm list packages | grep -E 'magisk|kernelsu|apatch|supersu'",
        "expected": "",
        "desc": "Root manager package detected",
    },
    {
        "name": "frida_server",
        "cmd_str": "ps -A 2>/dev/null | grep [f]rida || ps | grep [f]rida",
        "expected": "",
        "desc": "Frida is running on the device",
    },
]


IOS_JAILBREAK_PACKAGES = {
    "com.saurik.Cydia": "Cydia",
    "org.swiftapps.sileo": "Sileo",
    "org.coolstar.SileoStore": "Sileo",
    "xyz.willy.Zebra": "Zebra",
    "com.tigisoftware.Filza": "Filza",
}

# ----------------------------------------------------------------


def check_android_root(serial: str, cli_path: str) -> Tuple[bool, List[str]]:
    """Runs standard integrity/root checks on an Android device."""
    reasons: List[str] = []

    for check in ANDROID_ROOT_INDICATORS:
        cmd = "{cli} -s {serial} shell '{cmd_str}'"
        cmd_run = cmd.format(cli=cli_path, serial=serial, cmd_str=check["cmd_str"])
        try:
            p = run_command(cmd, cli=cli_path, serial=serial, cmd_str=check["cmd_str"])
            output = catch_err(p, cmd=cmd).strip()

            if output == "" and check.get("skip_if_missing", False):
                continue

            is_existence_check = check["expected"] == ""

            if p.returncode != 0:
                if not is_existence_check:
                    logging.error(
                        f"Unexpected failure in root check '{check['name']}'! "
                        f"This command ('{check['cmd_str']}') should always run successfully on any standard Android device. "
                        f"Failure usually indicates an ABD/USB authorization issue, a locked screen, or a super old device. "
                        f"Command: '{cmd_run}' (Exit code: {p.returncode}). "
                        f"Details: {output}"
                    )
                continue

            output_lower = output.lower()
            expected_lower = check["expected"].lower()
            failed_check = output_lower != expected_lower

            if failed_check:
                clean_output = output.replace("package:", "")
                if is_existence_check:
                    msg = (
                        f"Failed rootcheck '{check['name']}'. "
                        f"Detected: '{clean_output}'. "
                        f"{check['desc']}. "
                        f"Command to reproduce: `{cmd_run}`"
                    )
                else:
                    msg = (
                        f"Failed rootcheck '{check['name']}'. "
                        f"Output was '{clean_output}' but expected '{check['expected']}'. "
                        f"{check['desc']}. "
                        f"Command to reproduce: `{cmd_run}`"
                    )
                reasons.append(msg)

        except Exception as e:
            logging.debug(f"Root check {check['name']} failed: {e}")

    return len(reasons) > 0, reasons


# ----------------------------------------------------------------


def check_ios_jailbreak(serial: str, cli_path: str) -> Tuple[Optional[bool], List[str]]:
    """checks afc2 service and common jailbreak package managers"""
    reasons: List[str] = []

    # Check if afc2 is active (indicates root filesystem access over USB)
    try:
        from pymobiledevice3.lockdown import LockdownClient

        client = LockdownClient(udid=serial)
        client.start_service("com.apple.afc2")

        msg = (
            f"Failed rootcheck 'afc2_service'. "
            f"Detected: 'com.apple.afc2 active'. "
            f"Apple File Conduit 2 (afc2) service is active. This permits full root filesystem access over a USB connection. "
            f"Command to reproduce: `{cli_path} lockdown service com.apple.afc2 --udid {serial}`"
        )
        reasons.append(msg)
    except Exception:
        pass  # fails on stock devices

    cmd = "{cli} apps list --udid {serial}"
    cmd_run = cmd.format(cli=cli_path, serial=serial)
    try:
        import json

        p = run_command(cmd, cli=cli_path, serial=serial)
        output = catch_err(p, cmd=cmd).strip()
        json_start = output.find("[")
        if json_start != -1:
            apps = json.loads(output[json_start:])
            for app in apps:
                appid = app.get("Identifier", "")
                if appid in IOS_JAILBREAK_PACKAGES:
                    name = IOS_JAILBREAK_PACKAGES[appid]
                    msg = (
                        f"Failed rootcheck '{appid}'. "
                        f"Detected: '{appid}'. "
                        f"{name} ({appid}) installed. "
                        f"Command to reproduce: `{cmd_run}`"
                    )
                    reasons.append(msg)
    except Exception as e:
        logging.debug(f"iOS app jailbreak check failed: {e}")

    if reasons:
        return True, reasons

    return None, [
        "No obvious ios jailbreak indicators detected, but cannot be ruled out."
    ]
