from flask import request, render_template
from isdi.web import app
from isdi.web.view.index import get_device
from isdi.scanner import valid_appid
from isdi.scanner.db import get_device_info, is_hmac_serial
from isdi.config import get_config
import os

config = get_config()


@app.route("/details/app/<device>", methods=["GET"])
def app_details(device):
    sc = get_device(device)
    if sc is None:
        return "Unknown device type", 400
    appid = request.args.get("appId", "")
    ser = request.args.get("serial", "")
    if not valid_appid(appid):
        return "Invalid app ID", 400

    # The serial is either a connected device (live scan results) or the
    # stored HMAC of a scanned device (results loaded from the database).
    # Device info is only read from that device's own dump.
    if sc.is_connected(ser):
        hashed = False
    elif is_hmac_serial(ser) and get_device_info(ser).get("device") == device:
        hashed = True
    else:
        return "Unknown or disconnected device", 400

    d, info = sc.app_details(ser, appid, hashed=hashed)
    d["appId"] = appid

    # detect apple and put the key into d.permissions
    # if "Ios" in str(type(sc)):
    #    print("apple iphone")
    # else:
    #    print(type(sc))

    print(d.keys())
    return render_template(
        "main.html",
        task="app",
        title=config.TITLE,
        device_primary_user=config.DEVICE_PRIMARY_USER,
        app=d,
        info=info,
        device=device,
        is_termux=bool(os.environ.get("PREFIX")),
        is_debug=config.DEBUG,
    )
