from flask import Flask, render_template
from phone_scanner import AndroidScan, IosScan, TestScan
import json
app = Flask(__name__)

android = AndroidScan()
ios = IosScan()
test = TestScan()

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


@app.route("/scan/<device>?serial=<ser>", methods=['GET'])
def scan(device, ser):
    sc = {
        'android': android,
        'ios': ios,
        'test': test,
    }.get(device)
    return json.dumps(sc.find_spyapps())



@app.route('/list/<type>', methods=['GET'])
def list():
    phones = android.devices()
    return json.dumps(phones)


if __name__ == "__main__":
    app.run(debug=1)
