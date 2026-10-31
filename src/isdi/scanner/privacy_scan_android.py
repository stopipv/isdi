r"""
Author: Rahul Chatterjee
Date: 2018-06-11
Doc: https://docs.google.com/document/d/1HAzmB1IiViMrY7eyEt2K7-IwqFOKcczsgtRRaySCInA/edit

Privacy configuration for Android. An attempt to automate most of this.


Automatic settings check

To find what activity is running on the current window (*Super useful command*)

    adb shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'

Finally screen capture.

    adb shell screencap -p | perl -pe 's/\x0D\x0A/\x0A/g' > screen.png


1. Check the Accounts & Sync
    adb shell am start 'com.android.settings/.Settings\$AccountsGroupSettingsActivity'
2. Check the Google Account settings
    adb shell am start 'com.google.android.gms/com.google.android.gms.app.settings.GoogleSettingsLink'
3. Backup and reset
    adb shell am start 'com.android.settings/.Settings\$PrivacySettingsActivity'
4. Check location sharing settings
    adb shell am start 'com.google.android.apps.maps/com.google.android.maps.MapsActivity' && sleep 5 && adb shell input tap 20 80
5. Check photo sharing settings
    adb shell am start 'com.google.android.apps.photos/com.google.android.apps.photos.home.HomeActivity' && sleep 10 && adb shell input tap 20 80
"""

import os
import re
import secrets
import time
from pathlib import Path
from flask import url_for
from isdi.config import get_config
from isdi.scanner import runcmd

config = get_config()
adb = config.ADB_PATH

# Screenshots are named <16 hex chars>.png inside config.screenshots_dir.
SCREENSHOT_RE = re.compile(r"^[0-9a-f]{16}\.png$")


def thiscli(ser):
    """argv prefix for adb, targeting ser if given."""
    return [adb, "-s", ser] if ser else [adb]


def run_command(argv, timeout=10):
    """Run argv (no shell) and return (stdout, stderr)."""
    p = runcmd.run(argv, timeout=timeout)
    return p.stdout, p.stderr if p.returncode != 0 else ""


def get_screen_res(ser):
    out, err = run_command(thiscli(ser) + ["shell", "dumpsys", "window"])
    m = re.search(r"mUnrestrictedScreen=\(0,0\) (?P<w>\d+)x(?P<h>\d+)", out)
    if m:
        return int(m.group("w")), int(m.group("h"))
    else:
        return -1, -1


def open_activity(ser, activity_name):
    """
    Opens an activity
    """
    # adb shell joins its arguments into a command line for the device's
    # shell, so quote the activity name ($ appears in some of them).
    out, err = run_command(thiscli(ser) + ["shell", "am", "start", f"'{activity_name}'"])
    if err:
        print("ERROR (open_activity): {!r}".format(err))
        return False
    if "error" in out.lower():
        print("ERROR (open_activity) stdout=: {!r}".format(out))
        return False
    return True


def tap(ser, xpercent, ypercent):
    """
    Tap at xpercent and ypercent from top left
    """
    w, h = get_screen_res(ser)
    x = int(xpercent * w / 100)
    y = int(ypercent * h / 100)
    out, err = run_command(thiscli(ser) + ["shell", "input", "tap", str(x), str(y)])
    if err:
        print("ERROR (tap): {!r}".format(err))


def keycode(ser, evt):
    cmds = {"home": "3", "back": "4", "menu": "82", "power": "26"}
    if evt not in cmds:
        print("ERROR (keycode): No support for {}".format(evt))
        return

    run_command(thiscli(ser) + ["shell", "input", "keyevent", cmds[evt]])


def is_screen_on(ser):
    out, err = run_command(thiscli(ser) + ["shell", "dumpsys", "input_method"])
    if err:
        print("ERROR (is_screen_on): {!r}".format(err))
    return "mInteractive=true" in out


def take_screenshot(ser, fname=None):
    """
    Take a screenshot, save it in the private screenshots directory, and
    return an <img> tag that loads it through the token-checked route.
    """
    if not fname:
        fname = Path(config.screenshots_dir) / f"{secrets.token_hex(8)}.png"
    fname = Path(fname)

    p = runcmd.run(thiscli(ser) + ["exec-out", "screencap", "-p"], timeout=30, text=False)
    if p.returncode != 0 or not p.stdout:
        print(f"Screenshot failed with exit code {p.returncode}: {p.stderr!r}")
        return "<div class='screenshotfail'>Screenshot failed with exit code {}</div>".format(
            p.returncode
        )

    fname.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(os.open(fname, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
        f.write(p.stdout)
    return (
        "<img height='400px' src='"
        + url_for("privacy_screenshot", name=fname.name)
        + "'/>"
    )


def wait(t):
    time.sleep(t)


def add_image(img):
    """<img> tag for a bundled image in web/static/images."""
    return "<img height='400px' src='" + url_for("static", filename=f"images/{img}") + "'/>"


def do_privacy_check(ser, command):
    command = command.lower()
    if command == "account":  # 1. Account ownership  & 3. Sync (if present)
        open_activity(
            ser,
            "com.google.android.gms/com.google.android.gms.app.settings.GoogleSettingsLink",
        )
        # wait(2)
        # keycode(ser, 'home')
        # take_screenshot(ser, 'account.png')
        return (
            "Click on the <code>Google Account</code> on the phone, and check the "
            "<em>account email address</em> at the top."
        )
    elif command == "backup":  # 2. Backup & reset
        open_activity(ser, "com.android.settings/.Settings$PrivacySettingsActivity")
        # wait(2)
        # keycode(ser, 'home')
        # take_screenshot(ser, 'account.png')
        return (
            "If backup is <b>on</b>, then check the email address where <code>Backup "
            "account</code> is registered to."
        )
    elif command == "gmap":  # 4. Google Maps sharing
        open_activity(
            ser, "com.google.android.apps.maps/com.google.android.maps.MapsActivity"
        )
        wait(2)
        keycode(ser, "menu")
        return "Check the <code>location sharing</code> option; " + add_image(
            "google_maps_sharing.png"
        )
    elif command == "gphotos":  # 5. Google Photos sharing
        open_activity(
            ser,
            "com.google.android.apps.photos/com.google.android.apps.photos.home.HomeActivity",
        )
        wait(2)
        keycode(ser, "menu")
        return "Check the <code>Shared library</code>. " + add_image(
            "google_photos_sharing.png"
        )
    elif command == "sync":
        if not open_activity(
            ser, "com.android.settings/.Settings$AccountsGroupSettingsActivity"
        ):
            return (
                "I could not find syncing functionality in your Android. This most likely mean this is not available, "
                "and no need to check."
            )
        else:
            return (
                "Click on the <code>Google</code> (or other account) where the phone is syncing its data "
                "and what data is being synced."
            )

    elif command == "screenshot":
        return take_screenshot(ser)
    else:
        return "Command not supported; should be one of ['account', 'backup', 'gmap', 'gphotos'] (case in-sensitive)"


if __name__ == "__main__":
    # ser = "ZY224F8TKG"
    # print(get_screen_res(ser))
    # print(is_screen_on(ser))
    # do_privacy_check(ser, 'account')
    take_screenshot(ser="")
