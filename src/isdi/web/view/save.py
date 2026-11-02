from flask import request, session
from isdi.config import get_config
from isdi.web import app
from isdi.scanner.db import (
    get_serial_from_db,
    save_note,
    update_appinfo,
    update_mul_appinfo,
    create_report,
    get_device_from_db,
    get_app_info_from_db,
)
from isdi.scanner import valid_appid
from isdi.web.view.index import get_device

config = get_config()


@app.route("/saveapps/<scanid>", methods=["POST"])
def record_applist(scanid):
    device = get_device_from_db(scanid)
    sc = get_device(device)
    d = request.form
    update_mul_appinfo([(remark, scanid, appid) for appid, remark in d.items()])
    return "Success", 200


@app.route("/savescan/<scanid>", methods=["POST"])
def record_scanres(scanid):
    device = get_device_from_db(scanid)
    sc = get_device(device)
    note = request.form.get("notes")
    r = save_note(scanid, note)
    create_report(session["clientid"])
    # create_report(request.form.get('clientid'))
    return is_success(
        r, "Success!", "Could not save the form. See logs in the terminal."
    )


@app.route("/delete/app/<scanid>", methods=["POST"])
def delete_app(scanid):
    device = get_device_from_db(scanid)
    sc = get_device(device)
    if sc is None:
        return "Unknown scan", 400
    appid = request.form.get("appid", "")
    remark = request.form.get("remark")
    action = "delete"

    # Only uninstall apps that this scan found, on the device it scanned.
    # The database stores the HMAC of the serial, so find the connected
    # device with that HMAC.
    scanned_apps = {row["appid"] for row in get_app_info_from_db(scanid) or []}
    if not valid_appid(appid) or appid not in scanned_apps:
        return "Unknown app for this scan", 400
    serial = sc.connected_serial_for_hmac(get_serial_from_db(scanid) or "")
    if not serial:
        return "The scanned device is not connected", 409

    # TODO: Record the uninstall and note
    r = sc.uninstall(serial=serial, appid=appid)
    if r:
        r = update_appinfo(scanid=scanid, appid=appid, remark=remark, action=action)
        print("Update appinfo failed! r={}".format(r))
    else:
        print("Uninstall failed. r={}".format(r))
    return is_success(r, "Success!", config.error())


def is_success(b, msg_succ="", msg_err=""):
    if b:
        return msg_succ if msg_succ else "Success!", 200
    else:
        return msg_err if msg_err else "Failed", 401
