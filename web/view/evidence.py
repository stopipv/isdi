import json
import os
from pprint import pprint

from flask import redirect, render_template, request, session, url_for

import config
from db import (
    create_mult_appinfo,
    create_scan,
    get_client_devices_from_db,
    new_client_id,
)
from evidence_collection import get_suspicious_apps
from web import app
from web.view.index import get_device
from web.view.scan import first_element_or_none


@app.route("/evidence", methods=['GET', 'POST'])
def evidence():
    """
    TODO: Evidence stuff!
    """
    context = dict(
        task = "evidence",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
        device_owner = "",
        device = "",
        scanned=False
    )

    if request.method=="POST":

        # get form data
        device_owner = request.form["name"]
        device = request.form["device"]

        # get list of suspicious apps
        apps = get_suspicious_apps(device, device_owner)
        dual_use = []
        spyware = []
        for app in apps:
            if "dual-use" in app["flags"]:
                dual_use.append(app)
            if "spyware" in app["flags"]:
                spyware.append(app)

        context.update(dict(
            dual_use=dual_use,
            spyware=spyware,
            device_owner=device_owner,
            device=device,
            scanned=True
        ))

    return render_template('main.html', **context)

    

@app.route("/evidence/apps", methods=['GET', 'POST'])
def evidence_apps():
    """
    TODO: Get list of apps which ISDi flags as dual-use or spyware
    """
    
    # TODO get input from the user
    device = 'ios'
    device_owner = 'test'

    app_list = get_suspicious_apps(device, device_owner)

    return "Hi"