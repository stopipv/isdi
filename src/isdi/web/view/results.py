from isdi.web import app
from isdi.web.view.index import get_device
from flask import request, render_template, redirect, url_for
from isdi.config import get_config
from isdi.scanner.db import (
    get_scan_res_from_db,
    get_app_info_from_db,
    first_element_or_none,
)

config = get_config()


@app.route("/view_results", methods=["POST", "GET"])
def view_results():
    print("WORK IN PROGRESS")
    # clientid = request.form.get('clientid', request.args.get('clientid'))
    # hmac'ed serial of results we want to view
    scan_res_pk = request.form.get("scan_res", request.args.get("scan_res"))
    scan_res = first_element_or_none(get_scan_res_from_db(scan_res_pk))
    if not scan_res:
        return f"No scan found with id={scan_res_pk}"
    serial = scan_res["serial"]
    device = scan_res["device"]
    model = scan_res["device_model"]

    sc = get_device(device)

    """
    template_d = dict(
        task="home",
        title=config.TITLE,
        device=device,
        device_primary_user=config.DEVICE_PRIMARY_USER,   # TODO: Why is this sent
        device_primary_user_sel=device_primary_user,
        apps={},
        currently_scanned=currently_scanned,
        clientid=session['clientid']
    )
    
    apps = sc.find_spyapps(serialno=ser).fillna('').to_dict(orient='index')

    
    template_d.update(dict(
          isrooted=(
              "<strong class='text-danger'>Yes.</strong> Reason(s): {}"
              .format(rooted_reason) if rooted
              else "Don't know" if rooted is None
              else "No"
          ),
          device_name=device_name_print,
          apps=apps,
          scanid=scanid,
          sysapps=set(),  # sc.get_system_apps(serialno=ser)),
          serial=ser,
          # TODO: make this a map of model:link to display scan results for that
          # scan.
          error=config.error()
  ))
  """

    if scan_res_pk == last_serial:
        print("Should return same template as before.")
        print("scan_res:  {}".format(scan_res_pk))
        print("last_serial: {}".format(last_serial))
    else:
        print("Should return results of scan_res.")
        print("scan_res: {}".format(scan_res_pk))
        print("last_serial: {}".format(last_serial))
    return redirect(url_for("index"))
