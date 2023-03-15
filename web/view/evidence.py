import json
import os

from flask import redirect, render_template, request, session, url_for

import config
from db import (
    create_mult_appinfo,
    create_scan,
    get_client_devices_from_db,
    new_client_id,
)
from evidence_collection import app_list_to_str, get_suspicious_apps
from web import app
from web.view.index import get_device
from web.view.scan import first_element_or_none


@app.route("/evidence", methods=['GET'])
def evidence():
    """
    TODO: Evidence stuff!
    """
    return render_template(
        'main.html', task="evidence",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
        apps={}
    )

@app.route("/evidence/apps", methods=['GET'])
def evidence_apps():
    """
    TODO: Get list of apps which ISDi flags as dual-use or spyware
    """
    
    # TODO get input from the user
    device = 'ios'
    device_owner = 'test'

    app_list = get_suspicious_apps(device, device_owner)

    return app_list_to_str(app_list)