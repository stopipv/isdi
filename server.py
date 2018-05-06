from flask import Flask, render_template, request, redirect
from phone_scanner import AndroidScan, IosScan, TestScan
import json
import blacklist
import config
import parse_dump


FLASK_APP = Flask(__name__)
android = AndroidScan()
ios = IosScan()
test = TestScan()


def get_device(k):
    return {
        'android': android,
        'ios': ios,
        'test': test
    }.get(k)


@FLASK_APP.route("/", methods=['GET'])
def index():
    return render_template(
        'main.html',
        devices={
            'Android': android.devices(),
            'iOS': ios.devices(),
            'Test': test.devices()
        }, apps={}
    )


@FLASK_APP.route('/details/app/<device>', methods=['GET'])
def app_details(device):
    sc = get_device(device)
    appid = request.args.get('appId')
    ser = request.args.get('serial')
    d, info = sc.app_details(ser, appid)
    d = d.to_dict(orient='index').get(0, {})
    d['appId'] = appid
    return render_template(
        'app.html',
        app=d,
        info=info
    )


def first_element_or_none(a):
    if a: return a[0]


def is_success(b, msg_succ="", msg_err=""):
    if b:
        return msg_succ if msg_succ else "Success!", 200
    else:
        return msg_err if msg_err else "Failed", 401

@FLASK_APP.route("/scan/<device>", methods=['GET'])
def scan(device):
    # ser = request.args.get('serial')
    sc = get_device(device)
    ser = first_element_or_none(sc.devices())
    print(">>>scan_device", device, "<<<<<")

    # return json.dumps({
    #     'apps': sc.find_spyapps(serialno=ser).to_json(orient="index"),
    #     'serial': ser,
    #     'error': config.error()
    # })
    apps = sc.find_spyapps(serialno=ser).fillna('')
    # apps['flags'] = apps.flags.apply(blacklist.flag_str)
    return render_template(
        'main.html',
        apps=apps.to_dict(orient='index'),
        sysapps=set(sc.get_system_apps(serialno=ser)),
        serial=ser,
        device=device,
        error=config.error(),
    )

##############  RECORD DATA PART  ###############################


@FLASK_APP.route("/delete/app/<device>", methods=["POST"])
def delete_app(device):
    sc = get_device(device)
    serial = request.form.get('serial')
    appid = request.form.get('appid')
    # TODO: Record the uninstall and note
    r = sc.uninstall(serialno=serial, appid=appid)
    r &= sc.save('app_uninstall', serial=serial, appid=appid, notes=request.form.get('note', ''))
    return is_success(r, "Success!", config.error())

@FLASK_APP.route('/save/appnote/<device>', methods=["POST"])
def save_app_note(device):
    sc = get_device(device)
    serial = request.form.get('serial')
    appId = request.form.get('appId')
    note = request.form.get('note')
    return is_success(sc.save('notes', serialno=serial, appId=appId, note=note))


@FLASK_APP.route('/save/metainfo/<device>', methods=["POST"])
def record_response(device):
    sc = get_device(device)
    r = bool(sc.save(
        'response',
        response=json.dumps(request.form),
        serial=request.form.get('serial'),
    ))
    return is_success(r, "Success!", "Could not save for some reason. See logs in the terminal.")


if __name__ == "__main__":
    from imp import reload
    import sys
    if 'TEST' in sys.argv[1:] or 'test' in sys.argv[1:]:
        print("Running in test mode.")
        config.set_test_mode(True)
        print("Checking mode = {}\nApp flags: {}\nSQL_DB: {}"
              .format(config.TEST, config.APP_FLAGS_FILE,
                      config.SQL_DB_PATH))
    FLASK_APP.run(debug=config.DEBUG)
