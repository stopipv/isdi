from flask import request, render_template
from isdi.web import app
from isdi.web.view.index import get_device
from isdi.scanner.privacy_scan_android import do_privacy_check
from isdi.config import get_config

config = get_config()


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


@app.route("/privacy/<device>/<cmd>", methods=["GET"])
def privacy_scan(device, cmd):
    sc = get_device(device)
    res = do_privacy_check(sc.serialno, cmd)
    return res
