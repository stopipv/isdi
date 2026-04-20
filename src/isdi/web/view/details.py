from flask import request, render_template
from isdi.web import app
from isdi.web.view.index import get_device
from isdi.config import get_config
import os

config = get_config()


@app.route("/details/app/<device>", methods=["GET"])
def app_details(device):
    sc = get_device(device)
    appid = request.args.get("appId")
    ser = request.args.get("serial")
    d, info = sc.app_details(ser, appid)
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
