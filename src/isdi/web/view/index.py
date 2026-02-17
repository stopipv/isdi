from isdi.config import get_config
from isdi.web import app
from flask import render_template, request, session
from isdi.scanner import AndroidScanner, IosScanner, TestScanner
from isdi.scanner.db import get_client_devices_from_db, new_client_id
import os

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
        is_termux=bool(os.environ.get('PREFIX')),
        device_primary_user=config.DEVICE_PRIMARY_USER,
        task="home",
        devices={
            "Android": android.devices(),
            "iOS": ios.devices(),
            "Test": test.devices(),
        },
        apps={},
        clientid=session["clientid"],
        currently_scanned=get_client_devices_from_db(session["clientid"]),
    )
