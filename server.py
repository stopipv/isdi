from flask import Flask, render_template, request, redirect
from phone_scanner import AndroidScan, IosScan, TestScan
import json
import re
import config

app = Flask(__name__)
android = AndroidScan()
ios = IosScan()
test = TestScan()


def get_device(k):
    return {
        'android': android,
        'ios': ios,
        'test': test
    }.get(k)

@app.route("/", methods=['GET'])
def index():
    return render_template(
        'layout.html',
        devices={
            'Android': android.devices(),
            'iOS': ios.devices(),
            'Test': test.devices()
        })


@app.route('/?id=<id>', methods=['GET'])
def app_details(appid):
    pass


@app.route("/scan", methods=['GET'])
def scan():
    device = request.args.get('device')
    ser = request.args.get('serial')
    print(device, ser)
    sc = get_device(device)
    return sc.find_spyapps().to_json()


@app.route('/submit', methods=["POST", "GET"])
def record_response():
    if request.method == "POST":
        t = re.match('device=(\w+)&serial=(\w+)', request.form.get('url'))
        if not t:
            return "The form could not be submitted!", 400
        device, serial = t.groups()
        app_feedback = {
            k.split('-', 1)[1]: v
            for k,v in request.form.items()
            if k != 'url'
        }
        sc = get_device(device)
        sc.save(feedback=json.dumps(app_feedback), serial=serial)
        return "Success", 200
    else:
        return "hello", 200


@app.route('/list/<type>', methods=['GET'])
def list():
    phones = android.devices()
    return json.dumps(phones)


if __name__ == "__main__":
    app.run(debug=config.DEBUG)
