from flask import Flask, render_template, request, redirect
from phone_scanner import AndroidScan, IosScan, TestScan
import json
import re
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
        })


@FLASK_APP.route('/details/app/<device>', methods=['GET'])
def app_details(device):
    sc = get_device(device)
    appid = request.args.get('id')
    ser = request.args.get('ser')
    d = sc.app_details(ser, appid).to_dict()
    d['appId'] = appid
    return render_template(
        'app.html',
        app=d,
        info=d['info']
    )


@FLASK_APP.route("/scan/<device>", methods=['GET'])
def scan(device):
    ser = request.args.get('serial')
    print(">>>scan_device", device, ser, "<<<<<")
    sc = get_device(device)
    # return json.dumps({
    #     'apps': sc.find_spyapps(serialno=ser).to_json(orient="index"),
    #     'serial': ser,
    #     'error': config.error()
    # })
    return render_template(
        'main.html',
        apps=sc.find_spyapps(serialno=ser).fillna('').to_dict(orient='index'),
        serial=ser,
        error=config.error()
    )


@FLASK_APP.route("/delete/<device>", methods=["GET"])
def delete_app(device):
    sc = get_device(device)
    serial = request.args.get('serial')
    appid = request.args.get('appid')
    # TODO: Record the uninstall and note
    sc.save('app_uninstall', serial=serial, appid=appid, notes=request.args.get('notes', ''))
    return sc.uninstall(serialno=serial, appid=appid)


@FLASK_APP.route('/submit/<device>', methods=["POST"])
def record_response(device):
    if request.method == "POST":
        # t = re.match('(\w+)\?serial=(\w+)', request.form.get('url', ''))
        # if not t:
        #     print(request.form)
        #     return "The form could not be submitted!", 400
        # device, serial = t.groups()
        # TODO: Dump the whole form
        sc = get_device(device)
        r = bool(sc.save(
            'response',
            response=json.dumps(request.form),
            serial=request.form.get('device-id'),
        ))
        if not r:
            return "The action failed for some reason. See the logs "\
                "in the terminal.", 401
        else:
            return "Success!!", 200
    else:
        return "hello", 200


if __name__ == "__main__":
    FLASK_APP.run(debug=config.DEBUG)
