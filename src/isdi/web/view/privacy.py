from flask import abort, request, render_template, send_from_directory
from isdi.web import app
from isdi.web.view.index import get_device
from isdi.scanner.privacy_scan_android import SCREENSHOT_RE, do_privacy_check
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


@app.route("/privacy/<device>/<cmd>", methods=["POST"])
def privacy_scan(device, cmd):
    sc = get_device(device)
    if sc is None:
        return "No device loaded", 400
    devices = sc.devices()
    serial = request.form.get("serial")
    if not serial:
        # Use the first available device
        serial = devices[0] if devices else None
    if not serial:
        return "No device serial provided", 400
    if serial not in devices:
        return "That device is not connected", 400
    res = do_privacy_check(serial, cmd)
    return res


@app.route("/privacy/screenshot/<name>", methods=["GET"])
def privacy_screenshot(name):
    """Serve a privacy-checkup screenshot from the private screenshots dir."""
    if not SCREENSHOT_RE.match(name):
        abort(404)
    resp = send_from_directory(config.screenshots_dir, name, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store"
    return resp
