from flask import (
    Flask, render_template, request, redirect, g, jsonify,
    url_for
)
import logging
from logging.handlers import RotatingFileHandler
from phone_scanner import AndroidScan, IosScan, TestScan
import json
import blacklist
import config
from time import strftime
import traceback
from privacy_scan_android import do_privacy_check
from db import (
    get_db, create_scan, save_note, create_appinfo, update_appinfo,
    create_report, new_client_id, init_db, create_mult_appinfo,
    get_device_from_db, update_mul_appinfo, get_serial_from_db
)


app = Flask(__name__, static_folder='webstatic')
# app.config['STATIC_FOLDER'] = 'webstatic'
android = AndroidScan()
ios = IosScan()
test = TestScan()


def get_device(k):
    return {
        'android': android,
        'ios': ios,
        'test': test
    }.get(k)



@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route("/", methods=['GET'])
def index():
    return render_template(
        'main.html',
        task = 'home',
        devices={
            'Android': android.devices(),
            'iOS': ios.devices(),
            'Test': test.devices()
        },
        apps={},
        clientid=new_client_id()
    )


@app.route('/details/app/<device>', methods=['GET'])
def app_details(device):
    sc = get_device(device)
    appid = request.args.get('appId')
    ser = request.args.get('serial')
    d, info = sc.app_details(ser, appid)
    d = d.to_dict(orient='index').get(0, {})
    d['appId'] = appid

    ## detect apple and put the key into d.permissions
    #if "Ios" in str(type(sc)):
    #    print("apple iphone")
    #else:
    #    print(type(sc))
    
    print(d.keys())
    return render_template(
        'main.html', task="app",
        app=d,
        info=info,
        device=device
    )


@app.route('/instruction', methods=['GET'])
def instruction():
    return render_template('main.html', task="instruction")


@app.route('/kill', methods=['POST', 'GET'])
def killme():
    print("I am here")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return ("The app has been closed!")


def is_success(b, msg_succ="", msg_err=""):
    if b:
        return msg_succ if msg_succ else "Success!", 200
    else:
        return msg_err if msg_err else "Failed", 401

def first_element_or_none(l):
    if l and len(l)>0:
        return l[0]

@app.route("/privacy", methods=['GET'])
def privacy():
    """
    TODO: Privacy scan. Think how should it flow. 
    Privacy is a seperate page. 
    """
    return render_template('main.html', task="privacy")

@app.route("/privacy/<device>/<cmd>", methods=['GET'])
def privacy_scan(device, cmd):
    sc = get_device(device)
    res = do_privacy_check(sc.serialno, cmd)
    return res


@app.route("/scan", methods=['POST', 'GET'])
def scan():
    """
    Needs three attribute for a device
    :param device: "android" or "ios" or test
    :return: a flask view template
    """
    clientid = request.form.get('clientid', request.args.get('clientid'))
    device = request.form.get('device', request.args.get('device'))
    action = request.form.get('action', request.args.get('action'))
    print("--> Action = ", action)
    # if action == "Privacy Check":
    #     return redirect(url_for(privacy, device=device), code=302)
    sc = get_device(device)
    if not sc:
        return render_template("main.html",
                               task="home",
                               apps={},
                               error="Please pick one device.",
                               clientid=clientid
        )
    ser = first_element_or_none(sc.devices())
    # clientid = new_client_id()
    print(">>>scanning_device", device, ser, "<<<<<")
    error = "If an iPhone is connected, open iTunes, click through the connection dialog and wait for the \"Trust this computer\" prompt "\
    "to pop up in the iPhone, and then scan again." if device == 'ios' else\
    "If an Android device is connected, disconnect and reconnect the device, make sure "\
    "developer options is activated and USB debugging is turned on on the device, and then scan again."

    if not ser:
        return render_template(
            "main.html", task="home", apps={},
            error="<b>No device is connected!!</b> {}".format(error)
    )
    scanid = create_scan(clientid, ser, device)
    # @apps have appid, title, flags, TODO: add icon
    apps = sc.find_spyapps(serialno=ser).fillna('').to_dict(orient='index')
    print("Creating appinfo...")
    create_mult_appinfo([(scanid, appid, json.dumps(info['flags']), '', '<new>')
                          for appid, info in apps.items()])
    rooted = sc.isrooted(ser)
    return render_template(
        'main.html', task="home",
        isrooted = "Yes" if rooted else "Don't know" if rooted is None else "No",
        apps=apps,
        scanid=scanid,
        clientid=clientid,
        sysapps=set(), #sc.get_system_apps(serialno=ser)),
        serial=ser,
        device=device,
        error=config.error(),
    )


##############  RECORD DATA PART  ###############################


@app.route("/delete/app/<scanid>", methods=["POST", "GET"])
def delete_app(scanid):
    device = get_device_from_db(scanid)
    serial = get_serial_from_db(scanid)
    sc = get_device(device)
    appid = request.form.get('appid')
    remark = request.form.get('remark')
    action = "delete"
    # TODO: Record the uninstall and note
    r = sc.uninstall(serial=serial, appid=appid)
    if r:
        r = update_appinfo(
            scanid=scanid, appid=appid, remark=remark, action=action
        )
        print("Update appinfo failed! r={}".format(r))
    else:
        print("Uinstall failed. r={}".format(r))
    return is_success(r, "Success!", config.error())


# @app.route('/save/appnote/<device>', methods=["POST"])
# def save_app_note(device):
#     sc = get_device(device)
#     serial = request.form.get('serial')
#     appId = request.form.get('appId')
#     note = request.form.get('note')
#     return is_success(sc.save('appinfo', serial=serial, appId=appId, note=note))

@app.route('/saveapps/<scanid>', methods=["POST"])
def record_applist(scanid):
    device = get_device_from_db(scanid)
    sc = get_device(device)
    d = request.form
    update_mul_appinfo([(remark, scanid, appid)
                        for appid, remark in d.items()])
    return "Success", 200


@app.route('/savescan/<scanid>', methods=["POST"])
def record_scanres(scanid):
    device = get_device_from_db(scanid)
    sc = get_device(device)
    note = request.form.get('notes')
    r = save_note(scanid, note)
    create_report(request.form.get('clientid'))
    return is_success(r, "Success!", "Could not save the form. See logs in the terminal.")




################# For logging ##############################################
@app.route("/error")
def get_nothing():
    """ Route for intentional error. """
    return "foobar" # intentional non-existent variable


@app.after_request
def after_request(response):
    """ Logging after every request. """
    # This avoids the duplication of registry in the log,
    # since that 500 is already logged via @app.errorhandler.
    if response.status_code != 500:
        ts = strftime('[%Y-%b-%d %H:%M]')
        logger.error('%s %s %s %s %s %s',
                      ts,
                      request.remote_addr,
                      request.method,
                      request.scheme,
                      request.full_path,
                      response.status)
    return response


# @app.errorhandler(Exception)
# def exceptions(e):
#     """ Logging after every Exception. """
#     ts = strftime('[%Y-%b-%d %H:%M]')
#     tb = traceback.format_exc()
#     logger.error('%s %s %s %s %s 5xx INTERNAL SERVER ERROR\n%s',
#                   ts,
#                   request.remote_addr,
#                   request.method,
#                   request.scheme,
#                   request.full_path,
#                   tb)
#     print(e, file=sys.stderr)
#     return "Internal server error", 500





if __name__ == "__main__":
    from imp import reload
    import sys
    if 'TEST' in sys.argv[1:] or 'test' in sys.argv[1:]:
        print("Running in test mode.")
        config.set_test_mode(True)
        print("Checking mode = {}\nApp flags: {}\nSQL_DB: {}"
              .format(config.TEST, config.APP_FLAGS_FILE,
                      config.SQL_DB_PATH))


    init_db(app, force=(not config.TEST))
    handler = RotatingFileHandler('logs/app.log', maxBytes=100000,
                                  backupCount=30)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)

    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)

