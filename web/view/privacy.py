from flask import render_template, request

import config
import web.view.evidence

#from phone_scanner import iosScreenshot
from phone_scanner.privacy_scan_android import do_privacy_check, take_screenshot
from web import app
from web.view import get_device

from phone_scanner.privacy_scan_android import do_privacy_check

import hashlib
import hmac
import os
import re
import shlex
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
import subprocess
import time
import random
from flask import url_for, session
from privacy_scan_android import add_image


@app.route("/privacy", methods=["GET"])
def privacy():
    """
    TODO: Privacy scan. Think how should it flow.
    Privacy is a seperate page.
    """
    return render_template(
        "main.html",
        task="privacy",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
    )


@app.route("/privacy/<device>/<cmd>/<context>", methods=["GET"])
def privacy_scan(device, cmd, context):
    print(cmd)
    sc = get_device(device)
    if(device == "ios"):
        print("Taking a IOS screenhsot")
        res = iosScreenshot(sc.serialno, context, nocache=True)
    else:
        res = do_privacy_check(sc.serialno, cmd, context)
    print("Screenshot Taken")
    return res



def iosScreenshot(serialNumber, context, nocache = False):
    curr_time = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
    homePro = subprocess.run(["pwd"], stdout=subprocess.PIPE)
    homeDir = str(homePro.stdout.decode('utf-8')).strip()

    # Verify the directory exists and create it if not
    dir_path = os.path.join(homeDir, "webstatic/images/screenshots")
    os.makedirs(dir_path, exist_ok=True)
    fname = 'images/screenshots/' + context + '_' + curr_time + '.png'
    linkPro = subprocess.Popen(["pymobiledevice3", "lockdown", "start-tunnel"], stdout= subprocess.PIPE)
    time.sleep(2)
    output = linkPro.stdout
    rsdAddress = ""
    rsdPort = ""
    i = 0
    for lineByte in output:
        line = lineByte.decode('utf-8')
        print(line)
        if i == 6:
            break
        if "RSD Address" in line:
            rsdAddress = line[13:]
        if "RSD Port" in line:
            lineSplit = line.split(":")
            rsdPort = lineSplit[1][1:]
        i += 1
    tempFname = 'webstatic/' + fname
    command = "pymobiledevice3 developer dvt screenshot " + tempFname + " --rsd " + rsdAddress + " " + rsdPort
    subprocess.run(shlex.split(command))
    return add_image(fname, nocache=True)