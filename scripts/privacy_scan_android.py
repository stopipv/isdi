"""
Author: Rahul Chatterjee
Date: 2018-06-11
Doc: https://docs.google.com/document/d/1HAzmB1IiViMrY7eyEt2K7-IwqFOKcczsgtRRaySCInA/edit

Privacy configuration for Android. An attempt to automate most of this. 

"""
from subprocess import Popen, PIPE
import re
import time

def run_command(cmd, **kwargs):
    _cmd = cmd.format(
        **kwargs
    )
    p = Popen(_cmd, stdout=PIPE, stderr=PIPE, shell=True)
    p.wait(2)
    return p.stdout.read().decode('utf-8'), p.stderr.read().decode('utf-8')

def thiscli(ser):
    if ser:
        return "adb -s {ser}".format(ser=ser)
    else:
        return "adb"

def get_screen_res(ser):
    cmd = "{cli} shell dumpsys window | grep 'mUnrestrictedScreen'"
    out, err = run_command(cmd, cli=thiscli(ser))
    m = re.match(r'mUnrestrictedScreen=\(0,0\) (?P<w>\d+)x(?P<h>\d+)', out.strip())
    if m:
        return int(m.group('w')), int(m.group('h'))
    else:
        return -1, -1


def open_activity(ser, activity_name):
    """
    Opens an activity
    """
    cmd = "{cli} shell am start {act}"
    out, err = run_command(cmd, cli=thiscli(ser), act=activity_name)
    if err:
        print("ERROR (open_activity): {!r}".format(err))

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
    cmds = {
        "home": "3",
        "back": "4",
        "menu": "82",
        "power": "26"
    }
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
    if out == 'true':
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
    cmd = "{cli} shell screencap -p | perl -pe 's/\\x0D\\x0A/\\x0A/g' > {fname}"
    run_command(cmd, cli=thiscli(ser), fname=fname)
    

def wait(t):
    time.sleep(t)

def do_privacy_check(ser):
    # 1. Account ownership
    open_activity(ser, "com.google.android.gms/com.google.android.gms.app.settings.GoogleSettingsLink")
    wait(2)
    keycode(ser, 'home')
    take_screenshot(ser, 'account.png')
    # 2. Backup & reset
    # 3. Sync (if present)
    # 4. Google Maps sharing
    # 5. Google Photos sharing

if __name__ == "__main__":
    ser = "ZY224F8TKG"
    # print(get_screen_res(ser)
    # print(is_screen_on(ser))
    do_privacy_check(ser)
