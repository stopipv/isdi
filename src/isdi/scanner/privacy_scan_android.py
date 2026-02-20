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

from subprocess import Popen, PIPE
import re
import time
from flask import url_for
import random
from isdi.config import get_config

config = get_config()
adb = config.ADB_PATH
print(f">>>>>>>>>>>>>>> {adb} <<<<<<<<<<<<<<<<<<<<")


def run_command(cmd, **kwargs):
    _cmd = cmd.format(**kwargs)
    print(_cmd)
    p = Popen(_cmd, stdout=PIPE, stderr=PIPE, shell=True)
    p.wait()
    stdout = p.stdout.read().decode("utf-8") if p.stdout else ""
    stderr = p.stderr.read().decode("utf-8") if p.stderr else ""
    return stdout, stderr


def thiscli(ser):
    if ser:
        return "{adb} -s {ser}".format(adb=adb, ser=ser)
    else:
        return "{adb}".format(adb=adb)


def get_screen_res(ser):
    cmd = "{cli} shell dumpsys window | grep 'mUnrestrictedScreen'"
    out, err = run_command(cmd, cli=thiscli(ser))
    m = re.match(r"mUnrestrictedScreen=\(0,0\) (?P<w>\d+)x(?P<h>\d+)", out.strip())
    if m:
        return int(m.group("w")), int(m.group("h"))
    else:
        return -1, -1


def open_activity(ser, activity_name):
    """
    Opens an activity
    """
    cmd = "{cli} shell am start '{act}'"
    out, err = run_command(cmd, cli=thiscli(ser), act=activity_name)
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
    cmd = "{cli} shell input tap {x} {y}"
    out, err = run_command(cmd, cli=thiscli(ser), x=x, y=y)
    if err:
        print("ERROR (tap): {!r}".format(err))


def keycode(ser, evt):
    cmds = {"home": "3", "back": "4", "menu": "82", "power": "26"}
    if evt not in cmds:
        print("ERROR (keycode): No support for {}".format(evt))

    key = cmds.get(evt)
    run_command("{cli} shell input keyevent {key}", cli=thiscli(ser), key=key)


def is_screen_on(ser):
    cmd = "{cli} shell dumpsys input_method | grep 'mInteractive' | sed 's/.*mInteractive=//g'"
    out, err = run_command(cmd, cli=thiscli(ser))
    if err:
        print("ERROR (is_screen_on): {!r}".format(err))
    out = out.strip()
    if out == "true":
        return True
    else:
        return False


def take_screenshot(ser, fname=None):
    """
    Take a screenshot and output the iamge
    """
    # if not is_screen_on(ser):
    #     keycode(ser, 'power'); keycode(ser, 'menu') # Wakes the screen up
    if not fname:
        fname = "tmp_screencap.png"
    cmd = "{cli} shell screencap -p | perl -pe 's/\\x0D\\x0A/\\x0A/g' > '{fname}'"
    # cmd = "{cli} shell screencap -p > '{fname}'"
    run_command(cmd, cli=thiscli(ser), fname=fname)


def wait(t):
    time.sleep(t)


def do_privacy_check(ser, command):
    def add_image(img, nocache=False):
        rand = random.randint(0, 10000)
        query_string = f"?nocache={rand}" if nocache else ""
        return (
            "<img height='400px' src='"
            + url_for("static", filename="images/" + img)
            + query_string
            + "'/>"
        )

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
        open_activity(ser, "com.android.settings/.Settings\\$PrivacySettingsActivity")
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
            "google_maps_sharing.png"
        )
    elif command == "sync":
        if not open_activity(
            ser, "com.android.settings/.Settings\\$AccountsGroupSettingsActivity"
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
        take_screenshot(ser, fname="webstatic/images/tmp.png")
        return add_image("tmp.png", nocache=True)
    else:
        return "Command not supported; should be one of ['account', 'backup', 'gmap', 'gphotos'] (case in-sensitive)"


if __name__ == "__main__":
    # ser = "ZY224F8TKG"
    # print(get_screen_res(ser))
    # print(is_screen_on(ser))
    # do_privacy_check(ser, 'account')
    take_screenshot(ser="")
