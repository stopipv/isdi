import json
import os
from isdi.config import get_config
from isdi.web import app
from isdi.web.view.index import get_device
from flask import render_template, request, session, redirect, url_for
from isdi.scanner import db, blocklist
from isdi.scanner.db import (
    get_client_devices_from_db,
    new_client_id,
    create_scan,
    create_mult_appinfo,
    first_element_or_none,
)

config = get_config()


def get_param(key):
    return request.form.get(key, request.args.get(key))


@app.route("/scan", methods=["POST", "GET"])
def scan():
    """
    Needs three attribute for a device
    :param device: "android" or "ios" or test
    :param devid: id of the android device
    :param cientid: id of the cient
    :return: a flask view template
    """
    # clientid = request.form.get('clientid', request.args.get('clientid'))
    if "clientid" not in session:
        return redirect(url_for("index"))

    clientid = session["clientid"]
    device_primary_user = get_param("device_primary_user")
    device = get_param("device")
    action = get_param("action")
    device_owner = get_param("device_owner")
    ser = get_param("devid")

    currently_scanned = get_client_devices_from_db(session["clientid"])
    template_d = dict(
        task="home",
        title=config.TITLE,
        platform=config.PLATFORM,
        is_termux=bool(os.environ.get("PREFIX")),
        is_debug=config.DEBUG,
        device=device,
        device_primary_user=config.DEVICE_PRIMARY_USER,  # TODO: Why is this sent
        device_primary_user_sel=device_primary_user,
        apps={},
        currently_scanned=currently_scanned,
        clientid=session["clientid"],
    )
    # lookup devices scanned so far here. need to add this by model rather
    # than by serial.
    print("CURRENTLY SCANNED: {}".format(currently_scanned))
    print("DEVICE OWNER IS: {}".format(device_owner))
    print("PRIMARY USER IS: {}".format(device_primary_user))
    print("SERIAL NO: {}".format(ser))
    print("-" * 80)
    print("CLIENT ID IS: {}".format(session["clientid"]))
    print("-" * 80)
    print("--> Action = ", action)

    sc = get_device(device)
    if not sc:
        template_d["error"] = "Please choose one device to scan."
        return render_template("main.html", **template_d), 201
    if not device_owner:
        template_d["error"] = "Please give the device a nickname."
        return render_template("main.html", **template_d), 201

    if not ser:
        ser = first_element_or_none(sc.devices())

    print("Devices: {}".format(ser))
    if not ser:
        # FIXME: add pkexec scripts/ios_mount_linux.sh workflow for iOS if
        # needed.
        error = (
            "<b>A device wasn't detected. Please follow the "
            "<a href='/instruction' target='_blank' rel='noopener'>"
            "setup instructions here.</a></b>"
        )
        template_d["error"] = error
        return render_template("main.html", **template_d), 201

    # clientid = new_client_id()
    print(">>>scanning_device", device, ser, "<<<<<")

    # Only explicit from_dump requests should load old results.
    # Some real device serials are long hex strings and were mis-detected as hashed.
    from_dump = get_param("from_dump") == "1"

    if from_dump:
        # Load scan data from database — do NOT run ADB/iOS commands with hashed serial
        scanid = db.get_most_recent_scan_id(ser)
        if not scanid:
            template_d["error"] = (
                "No scan found for this device. Please connect the device and scan again."
            )
            return render_template("main.html", **template_d), 201

        scan_res = db.get_scan_res_from_db(scanid)
        if not scan_res:
            template_d["error"] = "Scan record not found in database."
            return render_template("main.html", **template_d), 201

        manufacturer = scan_res.get("device_manufacturer") or ""
        model = scan_res.get("device_model") or ""
        device_name_print = f"{manufacturer} {model}".strip() or "<Unknown device>"

        app_rows = db.get_app_info_from_db(scanid)
        apps = {}
        # Pre-fetch titles from the app-info cache database for this device type
        _title_cache = {}
        if sc and scan_res.get("device") == "android" and sc.app_info_conn:
            try:
                appids_in_scan = [r["appid"] for r in app_rows if r.get("appid")]
                if appids_in_scan:
                    cur = sc.app_info_conn.cursor()
                    placeholders = ",".join("?" * len(appids_in_scan))
                    cur.execute(
                        f"SELECT appid, title FROM apps WHERE appid IN ({placeholders})",
                        appids_in_scan,
                    )
                    for r in cur.fetchall():
                        if isinstance(r, dict):
                            _title_cache[r["appid"]] = r.get("title") or ""
                        else:
                            _title_cache[r[0]] = r[1] or ""
            except Exception:
                pass
        for row in app_rows:
            appid = row["appid"]
            try:
                flags = json.loads(row["flags"]) if row["flags"] else []
            except (json.JSONDecodeError, TypeError):
                flags = []
            title = _title_cache.get(appid, "")
            title = title.encode("ascii", errors="ignore").decode("ascii")
            apps[appid] = {
                "title": title,
                "flags": flags,
                "score": blocklist.score(flags),
                "class_": blocklist.assign_class(flags),
                "html_flags": blocklist.flag_str(flags),
            }

        rooted = scan_res.get("is_rooted")
        try:
            rooted_reason = json.loads(scan_res.get("rooted_reasons") or "[]")
        except (json.JSONDecodeError, TypeError):
            rooted_reason = []

    else:
        # Live scan — device must be connected

        if device == "ios":
            error = (
                "If an iPhone is connected, open iTunes, click through the "
                'connection dialog and wait for the "Trust this computer" '
                "prompt to pop up in the iPhone, and then scan again."
            )
        else:
            error = (
                "If an Android device is connected, disconnect and reconnect "
                "the device, make sure developer options is activated and USB "
                "debugging is turned on on the device, and then scan again."
            )
        error += (
            "{} <b>Please follow the <a href='/instruction' target='_blank'"
            " rel='noopener'>setup instructions here,</a> if needed.</b>"
        )

        device_name_print, device_name_map = sc.device_info(serial=ser)
        apps = sc.find_spyapps(serialno=ser)

        if len(apps) <= 0:
            print("The scanning failed for some reason.")
            error = (
                "The scanning failed. This could be due to many reasons. Try"
                " rerunning the scan from the beginning. If the problem persists,"
                " please report it in the file. <code>report_failed.md</code> in the<code>"
                "phone_scanner/</code> directory. Checn the phone manually. Sorry for"
                " the inconvenience."
            )
            template_d["error"] = error
            return render_template("main.html", **template_d), 201

        scan_d = {
            "clientid": session["clientid"],
            "serial": config.hmac_serial(ser),
            "device": device,
            "device_model": device_name_map.get("model", "<Unknown>").strip(),
            "device_version": device_name_map.get("version", "<Unknown>").strip(),
            "device_primary_user": device_owner,
        }

        if device == "ios":
            scan_d["device_manufacturer"] = "Apple"
            scan_d["last_full_charge"] = "unknown"
        else:
            scan_d["device_manufacturer"] = device_name_map.get("brand", "<Unknown>").strip()
            scan_d["last_full_charge"] = device_name_map.get("last_full_charge", "<Unknown>")

        rooted, rooted_reason = sc.isrooted(ser)
        scan_d["is_rooted"] = rooted
        scan_d["rooted_reasons"] = json.dumps(rooted_reason)

        scanid = create_scan(scan_d)

        print("Creating appinfo...")
        create_mult_appinfo(
            [
                (scanid, appid, json.dumps(info["flags"]), "", "<new>")
                for appid, info in apps.items()
            ]
        )

    apps_sorted = sorted(
        apps.items(),
        key=lambda item: (-item[1].get("score", 0.0), item[0]),
    )
    currently_scanned = get_client_devices_from_db(session["clientid"])
    template_d.update(
        dict(
            isrooted=(
                "<strong class='text-info'>Maybe (this is possibly just a bug with our scanning tool).</strong> Reason(s): {}".format(
                    rooted_reason
                )
                if rooted
                else "Don't know" if rooted is None else "No"
            ),
            device_name=device_name_print,
            apps=apps,
            apps_sorted=apps_sorted,
            scanid=scanid,
            sysapps=set(),
            serial=ser,
            currently_scanned=currently_scanned,
            error=config.error(),
        )
    )
    return render_template("main.html", **template_d), 200
