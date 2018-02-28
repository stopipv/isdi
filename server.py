from flask import Flask, render_template
from phone_scanner import AndroidScan, IosScan

app = Flask(__name__)

android = AndroidScan()
ios = IosScan()


@app.route("/", methods=['GET'])
def index():
    return render_template(
        'layout.html',
        android=[x for x in android.devices() if x],
        ios=ios.devices()
    )


@app.route('/?id=<id>', methods=['GET'])
def app_details(appid):
    pass

@app.route('/list/<type>', methods=['GET'])
def list():
    phones = android.devices()
    return json.dumps(phones)


if __name__ == "__main__":
    app.run(debug=1)
