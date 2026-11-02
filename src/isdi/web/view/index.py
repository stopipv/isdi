from isdi.config import get_config
from isdi.web import app
from flask import jsonify, render_template, request, session
from isdi.scanner import AndroidScanner, IosScanner, TestScanner
from isdi.scanner.db import get_client_devices_from_db, get_last_scan_time, new_client_id
import os
import threading
import time

config = get_config()

# FIXME: why are we scanning devices before people clicked on scan now?
android = AndroidScanner()
ios = IosScanner()
test = TestScanner()


# all in all, this particular section has a terrible code smell...
def get_device(k):
    return {"android": android, "ios": ios, "test": test}.get(k)


@app.route("/", methods=["GET"])
def index():
    # clientid = request.form.get('clientid', request.args.get('clientid'))
    # if not clientid: # if not coming from notes

    newid = request.args.get("newid")
    # if it's a new day (see app.permenant_session_lifetime),
    # or the client devices are all scanned (newid),
    # ask the DB for a new client ID (additional checks in DB).
    if "clientid" not in session or (newid is not None):
        session["clientid"] = new_client_id()

    return render_template(
        "main.html",
        title=config.TITLE,
        platform=config.PLATFORM,
        is_termux=bool(os.environ.get("PREFIX")),
        is_debug=config.DEBUG,
        device_primary_user=config.DEVICE_PRIMARY_USER,
        task="home",
        apps={},
        clientid=session["clientid"],
        currently_scanned=get_client_devices_from_db(session["clientid"]),
    )


_attached = {"at": 0.0, "devices": []}
_attached_lock = threading.Lock()


def attached_devices(max_age=2.0):
    """List attached phones, running the device tools at most every max_age seconds.

    The home page polls this; the lock makes concurrent polls share one
    listing instead of each starting adb and pymobiledevice3.
    """
    with _attached_lock:
        if time.time() - _attached["at"] > max_age:
            scanners = [("android", android), ("ios", ios)]
            if config.DEBUG:
                scanners.append(("test", test))
            found = []
            for kind, sc in scanners:
                for d in sc.connected_devices():
                    found.append(
                        {"device": kind, "devid": d["serial"], "label": d["label"], "state": d["state"]}
                    )
            _attached.update(at=time.time(), devices=found)
        return _attached["devices"]


@app.route("/devices", methods=["GET"])
def devices():
    # Looked up on every request (not cached) so a scan that just finished shows.
    found = [
        dict(d, last_scanned=get_last_scan_time(config.hmac_serial(d["devid"])))
        for d in attached_devices()
    ]
    return jsonify({"devices": found})
