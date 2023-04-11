"""
Author: Sophie Stephenson
Date: 2023-03-15

Collect evidence of IPS. Basic version collects this data from the phone:

1. All apps that might be dual-use or spyware and data about them (install 
    time, desc, etc.)
2. Permission usage in the last 7 days (or 28 days, if we can)

"""
import json
import os
from collections import defaultdict
from pprint import pprint

import jinja2
import pdfkit
from flask import session
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FieldList,
    FormField,
    HiddenField,
    MultipleFileField,
    RadioField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import InputRequired

import config
from db import create_mult_appinfo, create_scan
from privacy_scan_android import take_screenshot
from web.view.index import get_device
from web.view.scan import first_element_or_none

DEFAULT = "y"
SCREENSHOT_FOLDER = os.path.join("tmp", "isdi-screenshots/")

second_factors = ["Phone", "Email", "App"]
accounts = ["Google", "iCloud", "Microsoft", "Lyft", "Uber", "Doordash", "Grubhub", "Facebook", "Twitter", "Snapchat", "Instagram"]

yes_no_choices = [( 'yes', 'Yes'), ('no', 'No'), ('unsure', 'Unsure')]
device_type_choices = [('android', 'Android'), ('ios', 'iOS')]
#two_factor_choices = [empty_choice] + [(x.lower(), x) for x in second_factors]
two_factor_choices = [(x.lower(), x) for x in second_factors]
account_choices = [(x, x) for x in accounts]

## HELPER FORMS FOR EVERY PAGE
class NotesForm(FlaskForm):
    client_notes = TextAreaField("Client notes")
    consultant_notes = TextAreaField("Consultant notes")

## HELPER FORMS FOR APPS
class PermissionForm(FlaskForm):
    permission_name = HiddenField("Permission")
    access = RadioField('Can your [ex-]partner access this information?', choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    describe = TextAreaField("Please describe how you know this.")
    screenshot = MultipleFileField('Add screenshot(s)')

class InstallForm(FlaskForm):
    knew_installed = RadioField('Did you know this app was installed?', choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    installed = RadioField('Did you install this app?', choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    coerced = RadioField('Were you coerced into installing this app?', choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    screenshot = MultipleFileField('Add screenshot(s)')

class SpywareAppForm(FlaskForm):
    app_name = HiddenField("App Name")
    install_form = FormField(InstallForm)
    notes = FormField(NotesForm)

class DualUseAppForm(FlaskForm):
    app_name = HiddenField("App Name")
    install_form = FormField(InstallForm)
    permissions = FieldList(FormField(PermissionForm))
    notes = FormField(NotesForm)

## HELPER FORMS FOR ACCOUNTS
class SuspiciousLoginsForm(FlaskForm):
    recognize = RadioField("Do you recognize all logged-in devices?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    describe_logins = TextAreaField("Which devices do you not recognize?")
    login_screenshot = MultipleFileField('Add screenshot(s)')
    activity_log = RadioField("Are there any suspicious logins in the activity log?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    describe_activity = TextAreaField("Which logins are suspicious, and why?")
    activity_screenshot = MultipleFileField('Add screenshot(s)')

class PasswordForm(FlaskForm):
    know = RadioField("Does your [ex-]partner know the password for this account?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    guess = RadioField("Do you believe they could guess the password?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)

class RecoveryForm(FlaskForm):
    phone_present = RadioField("Is there a recovery phone number?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    phone_access = RadioField("Could your partner have access to the recovery phone number?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    phone_screenshot = MultipleFileField('Add screenshot(s)')
    email_present = RadioField("Is there a recovery email address?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    email_access = RadioField("Could your partner have access to the recovery email address?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    email_screenshot = MultipleFileField('Add screenshot(s)')

class TwoFactorForm(FlaskForm):
    enabled = RadioField("Is two-factor authentication enabled?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    second_factor_type = RadioField("What type of two-factor authentication is it?", choices=two_factor_choices, validators=[InputRequired()], default=DEFAULT)
    second_factor_access = RadioField("Could your partner have access to the second factor?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    screenshot = MultipleFileField('Add screenshot(s)')

class SecurityQForm(FlaskForm):
    present = RadioField("Does the account use security questions?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    questions = TextAreaField("Which questions are set?")
    know = RadioField("Would your [ex-]partner know the answer to any of these questions?", choices=yes_no_choices, validators=[InputRequired()], default=DEFAULT)
    screenshot = MultipleFileField('Add screenshot(s)')

class AccountInfoForm(FlaskForm):
    account_name = HiddenField("Account Name")
    suspicious_logins = FormField(SuspiciousLoginsForm)
    password_check = FormField(PasswordForm)
    recovery_settings = FormField(RecoveryForm)
    two_factor_settings = FormField(TwoFactorForm)
    security_questions = FormField(SecurityQForm)
    notes = FormField(NotesForm)

## INDIVIDUAL PAGES
class StartForm(FlaskForm):
    title = "Welcome to <Name of tool>"
    name = StringField('Name', validators=[InputRequired()])
    consultant_name = StringField('Consultant name', validators=[InputRequired()])
    device_type = RadioField('Device type', choices=device_type_choices, validators=[InputRequired()], default=DEFAULT)
    submit = SubmitField("Continue")

class ScanForm(FlaskForm):
    title = "Scan Instructions"
    submit = SubmitField("Scan")

class SpywareForm(FlaskForm):
    title = "Step 1: Spyware Check"
    spyware_apps = FieldList(FormField(SpywareAppForm))
    submit = SubmitField("Continue")

class DualUseForm(FlaskForm):
    title = "Step 2: Dual Use App Check"
    dual_use_apps = FieldList(FormField(DualUseAppForm))
    submit = SubmitField("Continue")

class AccountsUsedForm(FlaskForm):
    title = "Step 3a: Accounts Used"
    Google = BooleanField("Google")
    iCloud = BooleanField("iCloud")
    Microsoft = BooleanField("Microsoft")
    Lyft = BooleanField("Lyft")
    Uber = BooleanField("Uber")
    Doordash = BooleanField("Doordash")
    Grubhub = BooleanField("Grubhub")
    Facebook = BooleanField("Facebook")
    Twitter = BooleanField("Twitter")
    Snapchat = BooleanField("Snapchat")
    Instagram = BooleanField("Instagram")
    submit = SubmitField("Continue")

class AccountCompromiseForm(FlaskForm):
    title = "Step 3b: Account Compromise Check"
    accounts = FieldList(FormField(AccountInfoForm))
    submit = SubmitField("Continue")

def unpack_evidence_context(session, task="evidence"):
    """Takes session data and turns it into less confusing context to feed to template"""

    context = dict(
        task = task,
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
        device_owner = "",
        device = "",
        consultant = "",
        spyware = [],
        dualuse = [],
        accounts = [],
    )
    
    if "step1" in session.keys():
        context['device_owner'] = session['step1']['name']
        context['consultant'] = session['step1']['consultant_name']
        context['device'] = session['step1']['device_type']

    if "step3" in session.keys():
        context['spyware'] = session['step3']['spyware_apps']

    if "step4" in session.keys():
        context['dualuse'] = session['step4']['dual_use_apps']

    if "step6" in session.keys():
        context['accounts'] = session['step6']['accounts']

    if "apps" in session.keys():
        spyware = defaultdict(dict)
        for item in session['step3']['spyware_apps'] + session['apps']['spyware']:
            spyware[item['app_name']].update(item)
        dualuse = defaultdict(dict)
        for item in session['step4']['dual_use_apps'] + session['apps']['dualuse']:
            dualuse[item['app_name']].update(item)

        context['dualuse'] = dualuse.values()
        context['spyware'] = spyware.values()

    return context

def create_printout(context):
    
    filename = os.path.join('reports', 'test_report.pdf')
    template = os.path.join('templates', 'printout.html')
    css_path = os.path.join('webstatic', 'style.css')
    
    template_loader = jinja2.FileSystemLoader("./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(template)
    output_text = template.render(context)

    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
    pdfkit.from_string(output_text, filename, configuration=config, css=css_path)

    print("Printout created. Filename is", filename)

    return filename

def screenshot(device, fname):
    """Take a screenshot and return the file where the screenshot is"""
    fname = os.path.join(SCREENSHOT_FOLDER, fname)

    sc = get_device(device)
    ser = sc.devices()

    if device.lower() == "android":
        take_screenshot(ser, fname=fname)

    else:
        # don't know how to do this yet
        return None
    
    return fname

def remove_unwanted_data(data):
    """Clean data from forms (e.g., remove CSRF tokens so they don't live in the session)"""
    unwanted_keys = ["csrf_token"]

    if type(data) == list:
        return [remove_unwanted_data(d) for d in data]
        
    elif type(data) == dict:
        new_data = {}
        for k in data.keys():
            if k not in unwanted_keys:
                new_v = remove_unwanted_data(data[k])
                new_data[k] = new_v

        return new_data
    
    else:
        return data  
    
def reformat_verbose_apps(verbose_apps):
    """Minimize data we're storing in the session about these apps"""
    pprint(verbose_apps)
    spyware = []
    dualuse = []
    
    for verbose_app in verbose_apps:
        minimal_app = dict()

        minimal_app['description'] = verbose_app['description']
        minimal_app['appId'] = verbose_app['appId']
        minimal_app['icon'] = verbose_app['application_icon']
        minimal_app['url'] = verbose_app['developerwebsite']

        # the way ISDi does permissions is messed up rn, have to fix on the backend
        minimal_app['permissions'] = [{"permission_name": x.capitalize()} for x in verbose_app['permissions']]

        # add app to correct list
        minimal_app['app_name'] = verbose_app['title']
        if "spyware" in verbose_app["flags"]:
            spyware.append(minimal_app)
        if "dual-use" in verbose_app["flags"]:
            dualuse.append(minimal_app)

    return spyware, dualuse
    
def account_is_concerning(account):
    login_concern = account['suspicous_logins']['recognize'] != 'y' or account['suspicous_logins']['activity_log'] != 'n'
    pwd_concern = account['password_check']['guess'] != 'n' or account['password_check']['know'] != 'n'
    recovery_concern = account['recovery_settings']['phone_owned'] != 'y' or account['recovery_settings']['email_owned'] != 'y'
    twofactor_concern = account['two_factor_settings']['second_factor_owned'] != 'n'
    security_concern = account['security_questions']['know'] != 'n'

    return login_concern or pwd_concern or recovery_concern or twofactor_concern or security_concern


def get_multiple_app_details(device, ser, apps):
    filled_in_apps = []
    for app in apps:
        d = get_app_details(device, ser, app["id"])
        d["flags"] = app["flags"]
        filled_in_apps.append(d)
    return filled_in_apps


def get_app_details(device, ser, appid):
    sc = get_device(device)
    d, info = sc.app_details(ser, appid)
    d = d.fillna('')
    d = d.to_dict(orient='index').get(0, {})
    d['appId'] = appid

    return d

def get_suspicious_apps(device, device_owner):

    # The following code is adapted from web/view/scan.py

    template_d = dict(
        task="home",
        title=config.TITLE,
        device=device,
        device_primary_user=config.DEVICE_PRIMARY_USER,   # TODO: Why is this sent
        apps={},
    )

    sc = get_device(device)
    if not sc:
        raise Exception("Please choose one device to scan.")
    if not device_owner:
        raise Exception("Please give the device a nickname.")
    ser = sc.devices()

    print("Devices: {}".format(ser))
    if not ser:
        # FIXME: add pkexec scripts/ios_mount_linux.sh workflow for iOS if
        # needed.
        error = "<b>A device wasn't detected. Please follow the "\
            "<a href='/instruction' target='_blank' rel='noopener'>"\
            "setup instructions here.</a></b>"
        template_d["error"] = error
        raise Exception(error)

    ser = first_element_or_none(ser)
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
        if not isconnected:
            raise Exception(error)

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
        raise Exception(error)

    clientid = "1"
    if session['clientid']:
        clientid = session['clientid']

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

    template_d.update(dict(
        isrooted=(
            "<strong class='text-info'>Maybe (this is possibly just a bug with our scanning tool).</strong> Reason(s): {}"
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


    # new stuff from Sophie
    pprint(apps)

    suspicious_apps = []

    for k in apps.keys():
        app = apps[k]
        if 'dual-use' in app["flags"] or 'spyware' in app["flags"]:
            app["id"] = k
            suspicious_apps.append(app)

    detailed_apps = get_multiple_app_details(device, ser, suspicious_apps)
        
    return detailed_apps
