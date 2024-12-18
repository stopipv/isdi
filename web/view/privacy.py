from flask import render_template, request

import config
import web.view.evidence

#from phone_scanner import iosScreenshot
from phone_scanner.privacy_scan_android import do_privacy_check, take_screenshot
from web import app
from web.view import get_device

from phone_scanner.privacy_scan_android import do_privacy_check
import config


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
        res = take_screenshot(sc.serialno, context, nocache=True)
    else:
        res = do_privacy_check(sc.serialno, cmd, context)
    print("Screenshot Taken")
    return res
