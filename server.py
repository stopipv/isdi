from flask import (
    Flask, render_template, request, redirect, g, jsonify,
    url_for
)
import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from phone_scanner import AndroidScan, IosScan, TestScan
import json
import config
from time import strftime
# import traceback
from privacy_scan_android import do_privacy_check
from db import (
    create_scan, save_note, update_appinfo,
    create_report, new_client_id, init_db, create_mult_appinfo,
    get_client_devices_from_db, get_device_from_db, update_mul_appinfo,
    get_serial_from_db
)

#from flask_wtf import Form
#from sqlalchemy.orm import validates
from flask_migrate import Migrate
from flask_sqlalchemy import Model, SQLAlchemy
from wtforms_alchemy import ModelForm
from sqlalchemy import *
from wtforms.validators import Email, InputRequired
from wtforms.fields import SelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

app = Flask(__name__, static_folder='webstatic')
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQL_DB_PATH
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.secret_key = 'secret key' # doesn't seem to be necessary
app.config['SESSION_TYPE'] = 'filesystem'
sa=SQLAlchemy(app)
Migrate(app, sa)
# sa.create_all() # run in init_db()

# If changes are made to this model, please run 
# `flask db migrate` and then delete the drops to other tables from the upgrade() method in 
# migrations/versions/<version>.py
# before running `flask db upgrade` and re-launching the server.
# if the migrations folder isn't present, run `flask db init` first.
# _order in ClientForm should be modified .
class Client(sa.Model):
    __tablename__ = 'clients_notes'
    _d = {'default':'', 'server_default':''} # makes migrations smooth
    _lr = lambda label,req: {'label':label,'validators':InputRequired() if req=='r' else ''}
    id = sa.Column(sa.Integer, primary_key=True)
    created_at = sa.Column(
        sa.DateTime,
        default=datetime.now()
        #server_default=str(datetime.now()),
    )

    # TODO: link to session ClientID for scans, with foreignkey? across different db?
    # try using fieldstudy.db, creating table not dropping existing things. use ~test.

    consultant_initials = sa.Column(sa.String(100), nullable=False,
            info=_lr('Consultant Initials','r'), **_d)

    fjc = sa.Column(sa.Enum('Brooklyn', 'Queens', 'The Bronx', 'Manhattan', 'Staten Island'),
            nullable=False, info=_lr('FJC', 'r'), **_d)

    referring_professional = sa.Column(sa.String(100), nullable=False,
            info=_lr('Name of Referring Professional', 'r'), **_d)

    referring_professional_email = sa.Column(sa.String(255), nullable=True,
            info={'label': 'Email of Referring Professional (Optional)', 'validators':Email()})

    caseworker_present = sa.Column(sa.Enum('Yes', 'No'),
            nullable=False, info=_lr('Caseworker present for entire consult', 'r'), **_d)

    caseworker_present_safety_planning = sa.Column(sa.Enum('Yes', 'No'),
            nullable=False, info=_lr('Caseworker present for safety planning', 'r'), **_d)

    recorded = sa.Column(sa.Enum('Yes', 'No'),
            nullable=False, info=_lr('Permission to audio-record clinic', 'r'), **_d)

    chief_concerns = sa.Column(sa.String(400), nullable=False,
            info=_lr('Chief concerns', 'r'), **_d)

    chief_concerns_other = sa.Column(sa.String(400), nullable=False,
            info=_lr('Chief concerns if not listed above (Optional)', ''), **_d)

    def __repr__(self):
        return 'client seen on {}'.format(self.created_at)

class ClientForm(ModelForm): 
    class Meta:
        model = Client

    chief_concerns = SelectMultipleField('Chief concerns', choices=[('spyware','Spyware'),
        ('sms','SMS texts'),('hacked','Abuser hacked accounts or knows secrets'),
        ('other','Other chief concern (write in next question)')],
        coerce = str, option_widget = CheckboxInput(), widget = ListWidget(prefix_label=False))

    __order = ('fjc','consultant_initials','referring_professional','referring_professional_email',
            'caseworker_present','caseworker_present_safety_planning',
            'recorded','chief_concerns','chief_concerns_other')

    def __iter__(self): # https://stackoverflow.com/a/25323199
        fields = list(super(ClientForm, self).__iter__())
        get_field = lambda field_id: next((fld for fld in fields if fld.id == field_id))
        return (get_field(field_id) for field_id in self.__order)

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
    clientid = request.form.get('clientid', request.args.get('clientid'))
    if not clientid: # if not coming from notes
        clientid=new_client_id()

    return render_template(
        'main.html',
        title=config.TITLE,
        device_primary_user=config.DEVICE_PRIMARY_USER,
        task='home',
        devices={
            'Android': android.devices(),
            'iOS': ios.devices(),
            'Test': test.devices()
        },
        apps={},
        clientid=clientid
    )


@app.route('/form/', methods=['GET', 'POST'])
def client_forms():
    clientid = request.form.get('clientid', request.args.get('clientid'))
    print("FORM CLIENT ID IS:{}".format(clientid))

    # retrieve form defaults from db schema
    client = Client()
    form = ClientForm(request.form)
    if request.method == 'POST':
        try:
            if form.validate():
                print('VALIDATED')
                # convert checkbox lists to json-friendly strings
                for field in form:
                    if field.type == 'SelectMultipleField':
                        field.data = json.dumps(field.data)
                form.populate_obj(client)
                sa.session.add(client)
                sa.session.commit()
                return redirect('/')
        except Exception as e:
            print('NOT VALIDATED')
            print(e)
            sa.session.rollback()

    #clients_list = Client.query.all()
    return render_template('main.html', task="form", form=form, title=config.TITLE, clientid=clientid)

@app.route('/details/app/<device>', methods=['GET'])
def app_details(device):
    sc = get_device(device)
    appid = request.args.get('appId')
    ser = request.args.get('serial')
    d, info = sc.app_details(ser, appid)
    d = d.fillna('')
    d = d.to_dict(orient='index').get(0, {})
    d['appId'] = appid

    # detect apple and put the key into d.permissions
    # if "Ios" in str(type(sc)):
    #    print("apple iphone")
    # else:
    #    print(type(sc))

    print(d.keys())
    return render_template(
        'main.html', task="app",
        title=config.TITLE,
        device_primary_user=config.DEVICE_PRIMARY_USER,
        app=d,
        info=info,
        device=device
    )


@app.route('/instruction', methods=['GET'])
def instruction():
    return render_template('main.html', task="instruction",
                           device_primary_user=config.DEVICE_PRIMARY_USER,
                           title=config.TITLE)


@app.route('/kill', methods=['POST', 'GET'])
def killme():
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
    if l and len(l) > 0:
        return l[0]


@app.route("/privacy", methods=['GET'])
def privacy():
    """
    TODO: Privacy scan. Think how should it flow.
    Privacy is a seperate page.
    """
    return render_template(
        'main.html', task="privacy",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE
    )


@app.route("/privacy/<device>/<cmd>", methods=['GET'])
def privacy_scan(device, cmd):
    sc = get_device(device)
    res = do_privacy_check(sc.serialno, cmd)
    return res


@app.route("/view_results", methods=['POST', 'GET'])
def view_results():
    clientid = request.form.get('clientid', request.args.get('clientid'))
    scan_res = request.form.get('scan_res', request.args.get('scan_res'))

    # TODO: maybe unneccessary, but likely nice for returning without
    # re-drawing screen.
    last_serial = request.form.get(
        'last_serial', request.args.get('last_serial'))

    if scan_res == last_serial:
        print('Should return same template as before.')
        print("scan_res:  {}".format(scan_res))
        print("last_serial: {}".format(last_serial))
    else:
        print('Should return results of scan_res.')
        print("scan_res: {}".format(scan_res))
        print("last_serial: {}".format(last_serial))


@app.route("/scan", methods=['POST', 'GET'])
def scan():
    """
    Needs three attribute for a device
    :param device: "android" or "ios" or test
    :return: a flask view template
    """
    # FIXME: prevent clientID modification (remove it from GET params?)
    clientid = request.form.get('clientid', request.args.get('clientid'))
    device_primary_user = request.form.get(
        'device_primary_user',
        request.args.get('device_primary_user'))
    device = request.form.get('device', request.args.get('device'))
    action = request.form.get('action', request.args.get('action'))
    device_owner = request.form.get(
        'device_owner', request.args.get('device_owner'))

    currently_scanned = get_client_devices_from_db(clientid)
    template_d = dict(
        task="home",
        title=config.TITLE,
        device=device,
        device_primary_user=config.DEVICE_PRIMARY_USER,   # TODO: Why is this sent
        device_primary_user_sel=device_primary_user,
        apps={},
        currently_scanned=currently_scanned,
        clientid=clientid
    )
    # lookup devices scanned so far here. need to add this by model rather
    # than by serial.
    print('CURRENTLY SCANNED: {}'.format(currently_scanned))
    print('DEVICE OWNER IS: {}'.format(device_owner))
    print('PRIMARY USER IS: {}'.format(device_primary_user))
    print('-' * 80)
    print('CLIENT ID IS: {}'.format(clientid))
    print('-' * 80)
    print("--> Action = ", action)

    sc = get_device(device)
    if not sc:
        template_d["error"] = "Please choose one device to scan."
        return render_template("main.html", **template_d), 201
    if not device_owner:
        template_d["error"] = "Please give the device a nickname."
        return render_template("main.html", **template_d), 201

    ser = sc.devices()

    print("Devices: {}".format(ser))
    if not ser:
        # FIXME: add pkexec scripts/ios_mount_linux.sh workflow for iOS if
        # needed.
        error = "<b>A device wasn't detected. Please follow the "\
            "<a href='/instruction' target='_blank' rel='noopener'>"\
            "setup instructions here.</a></b>"
        template_d["error"] = error
        return render_template("main.html", **template_d), 201

    ser = first_element_or_none(ser)
    # clientid = new_client_id()
    print(">>>scanning_device", device, ser, "<<<<<")

    if device == "ios":
        error = "If an iPhone is connected, open iTunes, click through the "\
                "connection dialog and wait for the \"Trust this computer\" "\
                "prompt to pop up in the iPhone, and then scan again."
    else:
        error = "If an Android device is connected, disconnect and reconnect "\
                "the device, make sure developer options is activated and USB "\
                "debugging is turned on on the device, and then scan again."
    error += "{} <b>Please follow the <a href='/instruction' target='_blank'"\
             " rel='noopener'>setup instructions here,</a> if needed.</b>"
    if device == 'ios':
        # go through pairing process and do not scan until it is successful.
        isconnected, reason = sc.setup()
        template_d["error"] = error.format(reason)
        template_d["currently_scanned"] = currently_scanned
        if not isconnected:
            return render_template("main.html", **template_d), 201

    # TODO: model for 'devices scanned so far:' device_name_map['model']
    # and save it to scan_res along with device_primary_user.
    device_name_print, device_name_map = sc.device_info(serial=ser)

    # Finds all the apps in the device
    # @apps have appid, title, flags, TODO: add icon
    apps = sc.find_spyapps(serialno=ser).fillna('').to_dict(orient='index')
    if len(apps) <= 0:
        print("The scanning failed for some reason.")
        error = "The scanning failed. This could be due to many reasons. Try"\
            " rerunning the scan from the beginning. If the problem persists,"\
            " please report it in the file. <code>report_failed.md</code> in the<code>"\
            "phone_scanner/</code> directory. Checn the phone manually. Sorry for"\
            " the inconvenience."
        template_d["error"] = error
        return render_template("main.html", **template_d), 201

    scan_d = {
        'clientid': clientid,
        'serial': config.hmac_serial(ser),
        'device': device,
        'device_model': device_name_map.get('model', '<Unknown>').strip(),
        'device_version': device_name_map.get('version', '<Unknown>').strip(),
        'device_primary_user': device_owner,
    }

    if device == 'ios':
        scan_d['device_manufacturer'] = 'Apple'
        scan_d['last_full_charge'] = 'unknown'
    else:
        scan_d['device_manufacturer'] = device_name_map.get(
            'brand', "<Unknown>").strip()
        scan_d['last_full_charge'] = device_name_map.get(
            'last_full_charge', "<Unknown>")

    rooted, rooted_reason = sc.isrooted(ser)
    scan_d['is_rooted'] = rooted
    scan_d['rooted_reasons'] = json.dumps(rooted_reason)

    # TODO: here, adjust client session.
    scanid = create_scan(scan_d)

    if device == 'ios':
        pii_fpath = sc.dump_path(ser, 'Device_Info')
        print('Revelant info saved to db. Deleting {} now.'.format(pii_fpath))
        cmd = os.unlink(pii_fpath)
        # s = catch_err(run_command(cmd), msg="Delete pii failed", cmd=cmd)
        print('iOS PII deleted.')

    print("Creating appinfo...")
    create_mult_appinfo([(scanid, appid, json.dumps(
        info['flags']), '', '<new>') for appid, info in apps.items()])

    currently_scanned = get_client_devices_from_db(clientid)
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
    return render_template("main.html", **template_d), 200
    
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
        print("Uninstall failed. r={}".format(r))
    return is_success(r, "Success!", config.error())


# @app.route('/save/appnote/<device>', methods=["POST"])
# def save_app_note(device):
#     sc = get_device(device)
#     serial = request.form.get('serial')
#     appId = request.form.get('appId')
#     note = request.form.get('note')
# return is_success(sc.save('appinfo', serial=serial, appId=appId,
# note=note))

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
    return is_success(
        r,
        "Success!",
        "Could not save the form. See logs in the terminal.")


################# For logging ##############################################
@app.route("/error")
def get_nothing():
    """ Route for intentional error. """
    return "foobar"  # intentional non-existent variable


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
    import sys
    if 'TEST' in sys.argv[1:] or 'test' in sys.argv[1:]:
        print("Running in test mode.")
        config.set_test_mode(True)
        print("Checking mode = {}\nApp flags: {}\nSQL_DB: {}"
              .format(config.TEST, config.APP_FLAGS_FILE,
                      config.SQL_DB_PATH))
    print("TEST={}".format(config.TEST))
    init_db(app, sa, force=config.TEST)
    handler = RotatingFileHandler('logs/app.log', maxBytes=100000,
                                  backupCount=30)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    port = 5000 if not config.TEST else 5002
    app.run(host="0.0.0.0", port=port, debug=config.DEBUG)
