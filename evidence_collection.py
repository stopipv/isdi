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
from pprint import pprint

from flask import render_template, session
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FieldList,
    FormField,
    HiddenField,
    MultipleFileField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import InputRequired

import config
from db import create_mult_appinfo, create_scan
from web.view.index import get_device
from web.view.scan import first_element_or_none

ios_instructions = """
		        <img src="/webstatic/images/apple.resized.png"> There is not much preparation required for iOS. Just connect the USB cable, then on
                the device, you should see a prompt asking if you trust this device. Please select "Trust",
                and enter your passcode to unlock the device. Leave the device unlocked during the scan.
                <b>Troubleshooting:</b> Sometimes the system might fail to recognize the
                iOS device. Try opening iTunes on macOS, and see if the device is
                listed. Disconnect the device from the USB cable, reconnect, and try scanning again."""

android_instructions = """
	                    <img src="/webstatic/images/android.resiz.png">
                    For an Android device, the <code>developer options</code> on the device need to be
		            activated. Developer options provide functionality for this system to communicate with 
		            your device. The exact steps might vary from device manufacturer and version of
                    Android, but roughly the following steps will help you activate developer
                    options and USB debugging. 
                     <ol>
                    <li>Go to Settings. Either find the Settings app in the device drawer, or
                        pull down from the top notification bar, on the top right you will see a gear
                        type icon (<b>&#9881;</b>) for settings.</li>
                    <li>Scroll down to find About Phone, search for <code>Build number</code>,
                        tap on the build number 6-8 times to activate the developer mode. For some
                        devices, Build number might be hidden under Software info. (<b>Warning:</b> For
                        most device we can turn it off (see step 4), but there are some devices this
                        cannot be undone. This will not interfere with any of the device’s common
                        functionality, but does not leave the device at the state as it was before the
                        scanning.)</li>
                    <li>Turn on <code>USB debugging</code>. Go to
                        <code>Settings</code>&rarr;<code>Developer options</code>&rarr;<code>USB debugging</code>.
                        Tap on the toggle switch to turn it on.
                    </ol>
                        """

empty_choice = ("", "---")
second_factors = ["Phone", "Email", "App"]
accounts = ["Google", "iCloud", "Microsoft", "Lyft", "Uber"]

yes_no_choices = [empty_choice,( 'y', 'Yes'), ('n', 'No'), ('u', 'Unsure')]
device_type_choices = [empty_choice, ('android', 'Android'), ('ios', 'iOS')]
#two_factor_choices = [empty_choice] + [(x.lower(), x) for x in second_factors]
two_factor_choices = [(x.lower(), x) for x in second_factors] + [empty_choice]
account_choices = [(x, x) for x in accounts]

## HELPER FORMS FOR EVERY PAGE
class NotesForm(FlaskForm):
    client_notes = TextAreaField("Client notes")
    consultant_notes = TextAreaField("Consultant notes")

## HELPER FORMS FOR APPS
class PermissionForm(FlaskForm):
    permission_name = HiddenField("Permission")
    access = SelectField('Can your [ex-]partner access this information?', choices=yes_no_choices, validators=[InputRequired()], default="")
    describe = TextAreaField("Please describe how you know this.", validators=[InputRequired()])
    screenshot = MultipleFileField('Add screenshot(s)')

class InstallForm(FlaskForm):
    knew_installed = SelectField('Did you know this app was installed?', choices=yes_no_choices, validators=[InputRequired()], default="")
    installed = SelectField('Did you install this app?', choices=yes_no_choices, validators=[InputRequired()], default="")
    coerced = SelectField('Were you coerced into installing this app?', choices=yes_no_choices, validators=[InputRequired()], default="")
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
    recognize = SelectField("Do you recognize all logged-in devices?", choices=yes_no_choices, validators=[InputRequired()], default="")
    describe = TextAreaField("Which devices do you not recognize?", validators=[InputRequired()])
    activity_log = SelectField("Are there any suspicious logins in the activity log?", choices=yes_no_choices, validators=[InputRequired()], default="")
    screenshot = MultipleFileField('Add screenshot(s)')

class PasswordForm(FlaskForm):
    know = SelectField("Does your [ex-]partner know the password for this account?", choices=yes_no_choices, validators=[InputRequired()], default="")
    guess = SelectField("Do you believe they could guess the password?", choices=yes_no_choices, validators=[InputRequired()], default="")

class RecoveryForm(FlaskForm):
    phone = TextAreaField("What is the recovery phone number?", validators=[InputRequired()])
    phone_owned = SelectField("Is this your phone number?", choices=yes_no_choices, validators=[InputRequired()], default="")
    email = TextAreaField("What is the recovery email?", validators=[InputRequired()])
    email_owned = SelectField("Is this your email address?", choices=yes_no_choices, validators=[InputRequired()], default="")
    screenshot = MultipleFileField('Add screenshot(s)')

class TwoFactorForm(FlaskForm):
    enabled = SelectField("Is two-factor authentication enabled?", choices=yes_no_choices, validators=[InputRequired()], default="")
    type = SelectField("What type of two-factor authentication is it?", choices=two_factor_choices, validators=[InputRequired()], default="")
    second_factor = TextAreaField("What is the second factor?", validators=[InputRequired()])
    second_factor_owned = SelectField("Do you control the second factor?", choices=yes_no_choices, validators=[InputRequired()], default="")
    screenshot = MultipleFileField('Add screenshot(s)')

class SecurityQForm(FlaskForm):
    present = SelectField("Does the account use security questions?", choices=yes_no_choices, validators=[InputRequired()], default="")
    questions = TextAreaField("Which questions are set?", validators=[InputRequired()])
    know = SelectField("Would your [ex-]partner know the answer to any of these questions?", choices=yes_no_choices, validators=[InputRequired()], default="")
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
    device_type = SelectField('Device type', choices=device_type_choices, validators=[InputRequired()], default="")
    submit = SubmitField("Continue")

class SpywareForm(FlaskForm):
    title = "Spyware Check"
    spyware_apps = FieldList(FormField(SpywareAppForm))
    submit = SubmitField("Continue")

class DualUseForm(FlaskForm):
    title = "Dual Use App Check"
    dual_use_apps = FieldList(FormField(DualUseAppForm))
    submit = SubmitField("Continue")

class AccountsUsedForm(FlaskForm):
    title = "Accounts Used"
    Google = BooleanField("Google")
    iCloud = BooleanField("iCloud")
    Microsoft = BooleanField("Microsoft")
    Lyft = BooleanField("Lyft")
    Uber = BooleanField("Uber")
    Other = BooleanField("Other")
    submit = SubmitField("Continue")

class AccountCompromiseForm(FlaskForm):
    title = "Account Compromise Check"
    accounts = FieldList(FormField(AccountInfoForm))
    submit = SubmitField("Continue")

def remove_unwanted_data(data):
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
        'clientid': session['clientid'],
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
