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
from enum import Enum
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

FAKE_APP_DATA = {"spyware": [{"app_name": "MSpy",
                                 "appId": "mspy.app.id",
                                 "store": "offstore",
                                 "url": "https://www.mspy.com/",
                                 "genres": "spyware",
                                 "install_time": "January 1, 1970 00:00:00",
                                 "description": "mSpy is a computer security for parental control. Helps parents to give attention to their children online activities. It checks WhatsApp, Facebook, massage and snapchat messages. mSpy is a computer security for parental control.",
                                 "permissions": [
                                    {"permission_name": "Precise location"},
                                    {"permission_name": "Camera"},
                                    {"permission_name": "Messages"},
                                    {"permission_name": "Calls"},
                                ]
                                 }],
                    "dualuse": [{"app_name": "Snapchat",
                                 "appId": "snapchat.app.id",
                                 "store": "App Store",
                                 "url": "https://www.snapchat.com",
                                 "genres": "Photo \& Video",
                                 "install_time": "January 1, 1970 00:00:00",
                                 "description": "Snapchat is a fast and fun way to share the moment with your friends and family.",
                                "permissions": [
                                    {"permission_name": "Location"},
                                    {"permission_name": "Camera"},
                                ]},
                                {"app_name": "FindMy",
                                 "appId": "findmy.app.id",
                                 "store": "System App",
                                 "url": "https://apps.apple.com/us/app/find-my/id1514844621",
                                 "genres": "System apps",
                                 "install_time": "January 1, 1970 00:00:00",
                                 "description": "View the current location of your Apple devices, locate items you’ve attached AirTag to, keep track of Find My network accessories, and share your location with friends and family in a single, easy-to-use app.",
                                "permissions": [
                                    {"permission_name": "Precise location"},
                                ]}]
                    }

SCREENSHOT_FOLDER = os.path.join("tmp", "isdi-screenshots/")
CONTEXT_PKL_FNAME = "context.pkl"

DEFAULT = "y"
SECOND_FACTORS = ["Phone", "Email", "App"]
ACCOUNTS = ["Google", "iCloud", "Microsoft", "Lyft", "Uber", "Doordash", "Grubhub", "Facebook", "Twitter", "Snapchat", "Instagram"]

YES_NO_CHOICES = [( 'yes', 'Yes'), ('no', 'No'), ('unsure', 'Unsure')]
DEVICE_TYPE_CHOICES = [('android', 'Android'), ('ios', 'iOS')]
#two_factor_choices = [empty_choice] + [(x.lower(), x) for x in second_factors]
TWO_FACTOR_CHOICES = [(x.lower(), x) for x in SECOND_FACTORS] + [('none', 'None')]
ACCOUNT_CHOICES = [(x, x) for x in ACCOUNTS]

class Pages(Enum):
    START = 1
    SCAN = 2
    SPYWARE = 3
    DUALUSE = 4
    ACCOUNTS_USED = 5
    ACCOUNT_COMP = 6

## HELPER FORMS FOR EVERY PAGE
class NotesForm(FlaskForm):
    client_notes = TextAreaField("Client notes")
    consultant_notes = TextAreaField("Consultant notes")

## HELPER FORMS FOR APPS
class PermissionForm(FlaskForm):
    permission_name = HiddenField("Permission")
    access = RadioField('Can your [ex-]partner access this information using this app?', choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    describe = TextAreaField("How do you know?")
    screenshot = MultipleFileField('Add screenshot(s)')

# HELPER FORM FOR SCREENSHOTS

class InstallForm(FlaskForm):
    knew_installed = RadioField('Did you know this app was installed?', choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    installed = RadioField('Did you install this app?', choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    coerced = RadioField('Did your [ex-]partner coerce you into installing this app?', choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    #who = TextAreaField("If you were coerced, who coerced you?")
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
    recognize = RadioField("Do you recognize all devices logged into this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    describe_logins = TextAreaField("Which devices do you not recognize?")
    login_screenshot = MultipleFileField('Add screenshot(s)')
    activity_log = RadioField("In the login history, do you see any suspicious logins?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    describe_activity = TextAreaField("Which logins are suspicious, and why?")
    activity_screenshot = MultipleFileField('Add screenshot(s)')

class PasswordForm(FlaskForm):
    know = RadioField("Does your [ex-]partner know the password for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    guess = RadioField("Do you believe your [ex-]partner could guess the password?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)

class RecoveryForm(FlaskForm):
    phone_present = RadioField("Is there a recovery phone number set for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    phone = TextAreaField("What is the recovery phone number?")
    phone_access = RadioField("Do you believe your [ex-]partner has access to the recovery phone number?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    phone_screenshot = MultipleFileField('Add screenshot(s)')
    email_present = RadioField("Is there a recovery email address set for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    email = TextAreaField("What is the recovery email address?")
    email_access = RadioField("Do you believe your [ex-]partner has access to this recovery email address?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    email_screenshot = MultipleFileField('Add screenshot(s)')

class TwoFactorForm(FlaskForm):
    enabled = RadioField("Is two-factor authentication enabled for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    second_factor_type = RadioField("What type of two-factor authentication is it?", choices=TWO_FACTOR_CHOICES, validators=[InputRequired()], default=DEFAULT)
    describe = TextAreaField("Which phone/email/app is set as the second factor?")
    second_factor_access = RadioField("Do you believe your [ex-]partner has access to this second factor?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    screenshot = MultipleFileField('Add screenshot(s)')

class SecurityQForm(FlaskForm):
    present = RadioField("Does the account use security questions?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
    questions = TextAreaField("Which questions are set?")
    know = RadioField("Do you believe your [ex-]partner knows the answer to any of these questions?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=DEFAULT)
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
    name = StringField('Client name', validators=[InputRequired()])
    consultant_name = StringField('Consultant name', validators=[InputRequired()])
    device_type = RadioField('Device type', choices=DEVICE_TYPE_CHOICES, validators=[InputRequired()], default=DEFAULT)
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

    if 'step{}'.format(Pages.START.value) in session.keys():
        context['device_owner'] = session['step1']['name']
        context['consultant'] = session['step1']['consultant_name']
        context['device'] = session['step1']['device_type']

    if 'step{}'.format(Pages.SPYWARE.value) in session.keys():
        context['spyware'] = session['step3']['spyware_apps']

    if 'step{}'.format(Pages.DUALUSE.value) in session.keys():
        context['dualuse'] = session['step4']['dual_use_apps']

    if 'step{}'.format(Pages.ACCOUNT_COMP.value) in session.keys():
        context['accounts'] = session['step6']['accounts']

    if "apps" in session.keys():

        # remove permissions from the orig list because it merges weird
        permissionless_apps = []
        for app in session['apps']['dualuse']:
            newapp = dict()
            for k, v in app.items():
                if k != "permissions":
                    newapp[k] = v
            permissionless_apps.append(newapp)

        # combine the information in both dicts
        spyware = defaultdict(dict)
        for item in session['step{}'.format(Pages.SPYWARE.value)]['spyware_apps'] + session['apps']['spyware']:
            spyware[item['app_name']].update(item)
        dualuse = defaultdict(dict)
        for item in session['step{}'.format(Pages.DUALUSE.value)]['dual_use_apps'] + permissionless_apps:
            dualuse[item['app_name']].update(item)

        context['dualuse'] = list(dualuse.values())
        context['spyware'] = list(spyware.values())

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
    options = {'enable-local-file-access': None,
            'footer-right': '[page]'}
    pdfkit.from_string(output_text, filename, configuration=config, options=options, css=css_path)

    print("Printout created. Filename is", filename)

    return filename

def create_overall_summary(context, second_person=False):
    concerns = dict(
        spyware = [],
        dualuse = [],
        accounts = []
    )

    for app in context['spyware']:
        summary, concerning = create_app_summary(app, spyware=True, second_person=second_person)
        if concerning:
            concerns['spyware'].append(dict(
                name = app['app_name'],
                concern_type = "spyware app",
                summary = summary
            ))

    for app in context['dualuse']:
        summary, concerning = create_app_summary(app, spyware=False, second_person=second_person)
        if concerning:
            concerns['dualuse'].append(dict(
                name = app['app_name'],
                concern_type = "dual use app",
                summary = summary
            ))

    for account in context['accounts']:
        access, ability, access_concern, ability_concern = create_account_summary(account, second_person=second_person)
        if access_concern or ability_concern:
            summary = ""
            if access_concern:
                summary += access + " "
            if ability_concern:
                summary += ability
            concerns['accounts'].append(dict(
                name = account['account_name'],
                concern_type = "account",
                summary = summary
            ))

    return concerns

def create_app_summary(app, spyware, second_person=False):

    agent = "you"
    pronoun = "you"
    possessive = "your"
    if not second_person:
        agent = "the client"
        pronoun = "they"
        possessive = "their"

    sentences = []
    concern = False
    if spyware:
        concern = True
        sentences.append("{} is an app designed for surveillance.".format(app['app_name']))

    # for all apps, look at install information
    form = app['install_form']
    if form['knew_installed'] != 'yes':
        concern = True
        sentences.append("{} did not know that this app was installed on the phone.".format(agent.capitalize()))
        if spyware:
            sentences.append("This indicates that another person installed the app with the intention of surveilling {}.".format(agent))

    elif form['installed'] != 'yes':
        #
        # TODO: check if it is a system app
        #
        system_app = True
        if system_app:
            sentences.append("{} did not install this app. However, this is a system app which was likely installed on the phone when it was purchased.".format(agent.capitalize()))
        else:
            concern = True
            if form['installed'] == 'no':
                sentences.append("{} knew this app was installed on the phone, but did not install it.".format(agent.capitalize()))
            if form['installed'] == 'unsure':
                sentences.append("{} knew this app was installed on the phone, but {} are unsure whether {} installed it.".format(agent.capitalize(), pronoun, pronoun))
            sentences.append("This indicates that another person installed this app, which would require physical access to the phone.")


    elif form['coerced'] != 'no':
        concern = True
        sentences.append("{} [ex-]partner coerced {} to install this app, indicating that person is using the app to surveil {}.".format(possessive.capitalize(), agent, agent))
    else:
        sentences.append("{} installed this app voluntarily.".format(agent.capitalize()))

    # for spyware apps, look at permission stuff
    if not spyware:
        any_issues = False
        for perm in app['permissions']:
            if perm['access'] != 'no':
                any_issues = True
                concern = True
                sentences.append("{} [ex-]partner can use this app to access the phone's {}.".format(possessive.capitalize(), perm['permission_name'].lower()))

        if not any_issues:
            sentences.append("There is no evidence that this app is being used maliciously against {}.".format(agent))

    return " ".join(sentences), concern

def create_account_summary(account, second_person=False):

    agent = "you"
    pronoun = "you"
    possessive = "your"
    if not second_person:
        agent = "the client"
        pronoun = "they"
        possessive = "their"

    # generally, more high level because there is a lot going on.
    access_sentences = []
    access_concern = False

    # Suspicious logins
    form = account["suspicious_logins"]
    suspicious_logins = False
    if form['recognize'] != "yes":
        access_concern = True
        suspicious_logins = True
        if form['describe_logins'] != "":
            access_sentences.append("There is evidence that someone other than {} is currently logged into this account using {}.".format(agent, form['describe_logins']))
        else:
            access_sentences.append("There is evidence that someone other than {} is currently logged into this account.".format(agent))
    elif form['activity_log'] != "no":
        access_concern = True
        suspicious_logins = True
        access_sentences.append("There is evidence that someone other than {} has recently logged into this account.".format(agent))
    else:
        access_sentences.append("There is no evidence that someone other than {} has logged into this account recently.".format(agent))

    # Passwords
    pwd = False
    form = account["password_check"]
    if form['know'] != 'no' or form['guess'] != 'no':
        pwd = True

    # Recovery details
    recovery = False
    form = account["recovery_settings"]
    if (form['email_present'] == 'yes' and form['email_access'] != 'no') or (form['phone_present'] == 'yes' and form['phone_access'] != 'no'):
        recovery = True

    # Two-factor
    twofactor = False
    form = account["two_factor_settings"]
    if form['enabled'] == 'yes' and form['second_factor_access'] != 'no':
        twofactor = True

    # Security questions
    questions = False
    form = account["security_questions"]
    if form['present'] and form['know'] != 'no':
        questions= True

    ability_sentences = []
    ability_concern = False

    if not (pwd or recovery or twofactor or questions):

        other = ""
        if suspicious_logins:
            other = "other "
        ability_sentences.append("There is no {}evidence that anyone else could access this account.".format(other))
    else:
        ability_concern = True
        methods = []
        if pwd: methods.append("the password")
        if recovery: methods.append("the recovery contact information")
        if questions: methods.append("the security questions")

        also = ""
        if suspicious_logins:
            also = "also "

        if len(methods) > 1:
            ability_sentences.append("There is {}evidence that {} [ex-]partner can access this account via these methods: {}.".format(also, possessive, ", ".join(methods)))
        else:
            ability_sentences.append("There is {}evidence that {} [ex-]partner can access this account via {}.".format(also, possessive, methods[0]))

        if twofactor:
            ability_sentences.append("{} [ex-]partner has access to the second authentication factor; if they know the password, they could access this account without alerting {}.".format(possessive.capitalize(), agent))

    return " ".join(access_sentences), " ".join(ability_sentences), access_concern, ability_concern

def get_screenshots(context, name, dir):
    screenshots = os.listdir(dir)
    name = name.replace(' ', '')
    return list(filter(lambda x: context in x and name in x, screenshots))


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
        minimal_app['genres'] = []
        if verbose_app['genres'] != "":
            minimal_app['genres'] = verbose_app['genres'].split(", ")
        minimal_app['store'] = verbose_app['store']

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
    if 'clientid' in session.keys():
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
