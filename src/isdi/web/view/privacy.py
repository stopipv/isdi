from flask import request, render_template
from isdi.web import app
from isdi.web.view.index import get_device
from isdi.scanner.privacy_scan_android import do_privacy_check
from isdi.config import get_config
import os

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
        is_termux=bool(os.environ.get("PREFIX")),
        is_debug=config.DEBUG,
    )


@app.route("/privacy/<device>/<cmd>", methods=["GET"])
def privacy_scan(device, cmd):
    sc = get_device(device)
    if sc is None:
        return "No device loaded", 400
    # Get serial from request parameters
    serial = request.args.get("serial") or request.form.get("serial")
    if not serial:
        # Try to get the first available device
        devices = sc.devices()
        serial = devices[0] if devices else None
    if not serial:
        return "No device serial provided", 400
    res = do_privacy_check(serial, cmd)
    return res
