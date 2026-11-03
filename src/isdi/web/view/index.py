from isdi.config import get_config
from isdi.web import app
from flask import jsonify, render_template, request, session
from isdi.scanner import AndroidScanner, IosScanner, TestScanner, device_watch, parse_adb_devices
from isdi.scanner.ios_device import IosLibrary
from isdi.scanner.db import get_client_devices_from_db, get_last_scan_time, new_client_id
import logging
import os
import threading
import time
from datetime import datetime

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


def _watcher(kind):
    """The background device watcher for kind, or None where ISDi polls instead.

    Termux and WSL keep polling (their adb/usbmuxd access is indirect), as do tests.
    """
    if config.TEST or os.environ.get("PREFIX") or config.PLATFORM == "wsl":
        return None
    if kind == "android":
        return device_watch.get(
            "android", lambda: device_watch.AdbWatcher(android.cli, parse_adb_devices))
    if kind == "ios" and isinstance(ios.tool, IosLibrary):
        return device_watch.get("ios", lambda: device_watch.UsbmuxWatcher(IosLibrary.describe))
    return None


def _list_kind(kind, sc):
    w = _watcher(kind)
    records = w.snapshot() if w is not None else None
    if records is None:
        return sc.connected_devices()   # no live subscription: ask the tool directly
    return records if kind == "android" else sc.describe(records)


def attached_devices(max_age=2.0):
    """List attached phones.

    Normally answered from memory by the device watchers (isdi.scanner.device_watch).
    Otherwise the device tools run at most every max_age seconds, and the lock makes
    concurrent polls share one listing instead of each starting adb and pymobiledevice3.
    """
    with _attached_lock:
        if time.time() - _attached["at"] > max_age:
            scanners = [("android", android), ("ios", ios)]
            if config.DEBUG:
                scanners.append(("test", test))
            found = []
            for kind, sc in scanners:
                for d in _list_kind(kind, sc):
                    found.append(
                        {"device": kind, "devid": d["serial"], "label": d["label"], "state": d["state"]}
                    )
            _attached.update(at=time.time(), devices=found)
        return _attached["devices"]


def display_time(value, tz_name=None):
    """A DB timestamp (server local time, no zone) as e.g. "2026-11-02 20:12 CST".

    Shown in config.DISPLAY_TZ (ISDI_DISPLAY_TZ, default US Central); if that
    zone is unknown (no tzdata), in the server's own zone, still labelled.
    """
    if not value:
        return None
    try:
        local = datetime.fromisoformat(str(value)[:19]).astimezone()   # naive = server local
    except ValueError:
        return str(value)
    try:
        from zoneinfo import ZoneInfo
        local = local.astimezone(ZoneInfo(tz_name or config.DISPLAY_TZ))
    except Exception as exc:
        logging.debug("Display time zone %r unavailable: %s", tz_name or config.DISPLAY_TZ, exc)
    return local.strftime("%Y-%m-%d %H:%M %Z")


@app.route("/devices", methods=["GET"])
def devices():
    # Looked up on every request (not cached) so a scan that just finished shows.
    found = [
        dict(d, last_scanned=display_time(get_last_scan_time(config.hmac_serial(d["devid"]))))
        for d in attached_devices()
    ]
    return jsonify({"devices": found})
