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
from filelock import FileLock
from flask import session
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FieldList,
    FormField,
    HiddenField,
    MultipleFileField,
    RadioField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import InputRequired

import config
from phone_scanner.db import create_mult_appinfo, create_scan
from phone_scanner.privacy_scan_android import take_screenshot
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
                                 "genres": "Photo and Video",
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

TMP_CONSULT_DATA_DIR = "tmp-consult-data"

SCREENSHOT_FOLDER = os.path.join("tmp", "isdi-screenshots/")
CONTEXT_PKL_FNAME = "context.pkl"

YES_NO_DEFAULT = "yes"
SECOND_FACTORS = ["Phone", "Email", "App"]
ACCOUNTS = ["Google", "iCloud", "Microsoft", "Lyft", "Uber", "Doordash", "Grubhub", "Facebook", "Twitter", "Snapchat", "Instagram"]

YES_NO_CHOICES = [( 'yes', 'Yes'), ('no', 'No'), ('unsure', 'Unsure')]
PERSON_CHOICES = [( 'me', 'Me'), ('poc', 'Person of concern'), ('other', 'Someone else'), ('unsure', 'Unsure')]

LEGAL_CHOICES = [('ro', 'Restraining order'), ('div', 'Divorce or other family court'), ('cl', 'Criminal case'), ('other', 'Other')]
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
    access = RadioField('Can your [ex-]partner access this information using this app?', choices=YES_NO_CHOICES,  default=YES_NO_DEFAULT)
    describe = TextAreaField("How do you know?")
    screenshot = MultipleFileField('Add screenshot(s)')

# HELPER FORM FOR SCREENSHOTS

class InstallForm(FlaskForm):
    knew_installed = RadioField('Did you know this app was installed?', choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    installed = RadioField('Did you install this app?', choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    coerced = RadioField('Did your [ex-]partner coerce you into installing this app?', choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    #who = TextAreaField("If you were coerced, who coerced you?")
    screenshot = MultipleFileField('Add screenshot(s)')

class SpywareAppForm(FlaskForm):
    title = HiddenField("App Name")
    install_form = FormField(InstallForm)
    app_name = HiddenField("App Name")
    appId = HiddenField("App ID")
    flags = HiddenField("Flags")
    application_icon = HiddenField("App Icon")
    app_website = HiddenField("App Website")
    description = HiddenField("Description")
    #descriptionHTML = HiddenField("HTML Description")
    developerwebsite = HiddenField("Developer Website")
    permissions = HiddenField("Permissions")
    subclass = HiddenField("Subclass")
    summary = HiddenField("Summary")
    notes = FormField(NotesForm)

class DualUseAppForm(FlaskForm):
    title = HiddenField("App Name")
    install_info = FormField(InstallForm)
    permissions = FieldList(FormField(PermissionForm))
    app_name = HiddenField("App Name")
    appId = HiddenField("App ID")
    flags = HiddenField("Flags")
    application_icon = HiddenField("App Icon")
    app_website = HiddenField("App Website")
    description = HiddenField("Description")
    #descriptionHTML = HiddenField("HTML Description")
    developerwebsite = HiddenField("Developer Website")
    subclass = HiddenField("Subclass")
    summary = HiddenField("Summary")
    notes = FormField(NotesForm)

## HELPER FORMS FOR ACCOUNTS
class SuspiciousLoginsForm(FlaskForm):
    recognize = RadioField("Do you recognize all devices logged into this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    describe_logins = TextAreaField("Which devices do you not recognize?")
    login_screenshot = MultipleFileField('Add screenshot(s)')
    activity_log = RadioField("In the login history, do you see any suspicious logins?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    describe_activity = TextAreaField("Which logins are suspicious, and why?")
    activity_screenshot = MultipleFileField('Add screenshot(s)')

class PasswordForm(FlaskForm):
    know = RadioField("Does your [ex-]partner know the password for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    guess = RadioField("Do you believe your [ex-]partner could guess the password?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)

class RecoveryForm(FlaskForm):
    phone_present = RadioField("Is there a recovery phone number set for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    phone = TextAreaField("What is the recovery phone number?")
    phone_access = RadioField("Do you believe your [ex-]partner has access to the recovery phone number?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    phone_screenshot = MultipleFileField('Add screenshot(s)')
    email_present = RadioField("Is there a recovery email address set for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    email = TextAreaField("What is the recovery email address?")
    email_access = RadioField("Do you believe your [ex-]partner has access to this recovery email address?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    email_screenshot = MultipleFileField('Add screenshot(s)')

class TwoFactorForm(FlaskForm):
    enabled = RadioField("Is two-factor authentication enabled for this account?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    second_factor_type = RadioField("What type of two-factor authentication is it?", choices=TWO_FACTOR_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    describe = TextAreaField("Which phone/email/app is set as the second factor?")
    second_factor_access = RadioField("Do you believe your [ex-]partner has access to this second factor?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    screenshot = MultipleFileField('Add screenshot(s)')

class SecurityQForm(FlaskForm):
    present = RadioField("Does the account use security questions?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    questions = TextAreaField("Which questions are set?")
    know = RadioField("Do you believe your [ex-]partner knows the answer to any of these questions?", choices=YES_NO_CHOICES, validators=[InputRequired()], default=YES_NO_DEFAULT)
    screenshot = MultipleFileField('Add screenshot(s)')

class AccountInfoForm(FlaskForm):
    account_nickname = TextAreaField("Account Nickname")
    account_platform = TextAreaField("Platform")
    suspicious_logins = FormField(SuspiciousLoginsForm)
    password_check = FormField(PasswordForm)
    recovery_settings = FormField(RecoveryForm)
    two_factor_settings = FormField(TwoFactorForm)
    security_questions = FormField(SecurityQForm)
    notes = FormField(NotesForm)

class AppSelectForm(FlaskForm):
    title = HiddenField("App Name")
    appId = HiddenField("App ID")
    flags = HiddenField("Flags")
    app_name = HiddenField("App Name")
    application_icon = HiddenField("App Icon")
    app_website = HiddenField("App Website")
    description = HiddenField("Description")
    #descriptionHTML = HiddenField("HTML Description")
    developerwebsite = HiddenField("Developer Website")
    permissions = HiddenField("Permissions")
    subclass = HiddenField("Subclass")
    summary = HiddenField("Summary")
    investigate = BooleanField("Check this app?")

## INDIVIDUAL PAGES
class StartForm(FlaskForm):
    title = "Device To Be Scanned"
    device_nickname = StringField('Device nickname', validators=[InputRequired()])
    device_type = RadioField('Device type', choices=DEVICE_TYPE_CHOICES, validators=[InputRequired()])
    submit = SubmitField("Scan Device")
    manualadd = SubmitField("Select apps manually")


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

class SingleAppCheckForm(FlaskForm):
    title = HiddenField("App Name")
    install_info = FormField(InstallForm)
    permissions = FieldList(FormField(PermissionForm))
    appId = HiddenField("App ID")
    flags = HiddenField("Flags")
    application_icon = HiddenField("App Icon")
    app_website = HiddenField("App Website")
    description = HiddenField("Description")
    descriptionHTML = HiddenField("HTML Description")
    developerwebsite = HiddenField("Developer Website")
    subclass = HiddenField("Subclass")
    summary = HiddenField("Summary")
    investigate = HiddenField("Investigate?")
    notes = FormField(NotesForm)

class AppInvestigationForm(FlaskForm):
    title = "App Investigations"
    selected_apps = FieldList(FormField(SingleAppCheckForm))
    submit = SubmitField("Save Investigation")

class AccountCompromiseForm(FlaskForm):
    title = "Account Compromise Check"
    platform = StringField('Platform', validators=[InputRequired()])
    account_nickname = StringField('Account Nickname')
    suspicious_logins = FormField(SuspiciousLoginsForm)
    password_check = FormField(PasswordForm)
    recovery_settings = FormField(RecoveryForm)
    two_factor_settings = FormField(TwoFactorForm)
    security_questions = FormField(SecurityQForm)
    notes = FormField(NotesForm)
    submit = SubmitField("Save")

class SetupForm(FlaskForm):
    title = "Consultation Information"
    client = StringField('Client Name', validators=[InputRequired()])
    date = StringField('Consultation Date and Time', validators=[InputRequired()], render_kw={'readonly': True})
    submit = SubmitField("Start Consultation")

class AppSelectPageForm(FlaskForm):
    title = "Select Apps to Investigate"
    apps = FieldList(FormField(AppSelectForm))
    submit = SubmitField("Select")

class ManualAppSelectForm(FlaskForm):
    app_name = StringField("App Name")
    spyware = BooleanField("Appears to be a spyware app?")

class ManualAddPageForm(FlaskForm):
    title = "Manual App Investigation: Select Apps"
    device_nickname = StringField("Device Nickname", validators=[InputRequired()])
    apps = FieldList(FormField(ManualAppSelectForm))
    addline = SubmitField("Add a new app")
    submit = SubmitField("Submit")

    def update_self(self):
        # read the data in the form
        read_form_data = self.data

        # modify the data as you see fit:
        updated_list = read_form_data['apps']
        if read_form_data['addline']:
            updated_list.append({})
        read_form_data['apps'] = updated_list

        # reload the form from the modified data
        self.__init__(formdata=None, **read_form_data)
        self.validate()  # the errors on validation are cancelled in the line above

### TAQ Forms
class TAQDeviceCompForm(FlaskForm):
    title = "Device Compromise Indicators"
    live_together = RadioField("Do you live with the person of concern?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    physical_access = RadioField("Has the person of concern had physical access to your devices at any point in time?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)

class TAQAccountsForm(FlaskForm):
    title = "Account and Password Management"
    pwd_mgmt = StringField("How do you manage passwords?")
    pwd_comp = RadioField("Do you believe the person of concern knows, or could guess, any of your passwords?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    pwd_comp_which = StringField("Which ones?")

class TAQSharingForm(FlaskForm):
    title = "Account Sharing"
    share_phone_plan = RadioField("Do you share a phone plan with the person of concern?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    phone_plan_admin = SelectMultipleField("If you share a phone plan, who is the family 'head' or plan administrator?", choices=PERSON_CHOICES)
    share_accounts = RadioField("Do you share any accounts with the person of concern?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)

class TAQSmartHomeForm(FlaskForm):
    title = "Smart Home Devices"
    smart_home = RadioField("Do you have any smart home devices?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    smart_home_setup = SelectMultipleField("Who installed and set up your smart home devices?", choices=PERSON_CHOICES)
    smart_home_access = RadioField("Did the person of concern ever have physical access to the devices?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    smart_home_account = RadioField("Do you share any smart home accounts with the person of concern?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)

class TAQKidsForm(FlaskForm):
    title = "Children's Devices"
    custody = RadioField("Do you share custody of children with the person of concern?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    child_phys_access = RadioField("Has the person of concern had physical access to any of the child(ren)'s devices?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)
    child_phone_plan = RadioField("Does the person of concern pay for the child(ren)'s phone plan?", choices=YES_NO_CHOICES, default=YES_NO_DEFAULT)

class TAQLegalForm(FlaskForm):
    title = "Legal Proceedings"
    legal = SelectMultipleField("Do you have any ongoing legal cases?", choices=LEGAL_CHOICES)

class TAQForm(FlaskForm):
    title = "Technology Assessment Questionnaire (TAQ)"
    devices = FormField(TAQDeviceCompForm)
    accounts = FormField(TAQAccountsForm)
    sharing = FormField(TAQSharingForm)
    smarthome = FormField(TAQSmartHomeForm)
    kids = FormField(TAQKidsForm)
    legal = FormField(TAQLegalForm)
    submit = SubmitField("Save TAQ")


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

    pprint(context)

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
            
    return concerns

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
    #d = d.fillna('')
    #d = d.to_dict(orient='index').get(0, {})
    #d['appId'] = appid

    return d

def get_scan_data(device, device_owner):

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
        error = "A device wasn't detected."
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
    other_apps = []

    for k in apps.keys():
        app = apps[k]
        app["id"] =k
        app["app_name"] = app["title"]
        if 'dual-use' in app["flags"] or 'spyware' in app["flags"]:
            suspicious_apps.append(app)
        else:
            other_apps.append(app)

    detailed_suspicious_apps = get_multiple_app_details(device, ser, suspicious_apps)
    detailed_other_apps = get_multiple_app_details(device, ser, other_apps)

    pprint(detailed_suspicious_apps)

    return scan_d, detailed_suspicious_apps, detailed_other_apps

class ConsultDataTypes(Enum):
    TAQ = 1
    SCANS = 2
    ACCOUNTS = 3
    SETUP = 4

def get_data_filename(datatype: ConsultDataTypes):

    if datatype == ConsultDataTypes.SETUP.value:
        return "setup.json"
    elif datatype == ConsultDataTypes.TAQ.value:
        return "taq.json"
    elif datatype == ConsultDataTypes.SCANS.value:
        return "scans.json"
    else:
        return "accounts.json"


# Save data to the right tmp file as JSON
# Overwrites it always, assume any previous data has been incorporated
def save_data_as_json(data, datatype: ConsultDataTypes):

    json_object = json.dumps(data, cls=EvidenceDataEncoder)

    fname = os.path.join(TMP_CONSULT_DATA_DIR, get_data_filename(datatype))
    
    lock = FileLock(fname + ".lock")
    with lock:
        with open(fname, 'w') as outfile:
            outfile.write(json_object)

    
    print("DATA SAVED:", type(data))

    return

def load_json_data(datatype: ConsultDataTypes):

    fname = os.path.join(TMP_CONSULT_DATA_DIR, get_data_filename(datatype))

    lock = FileLock(fname + ".lock")
    with lock:
        if not os.path.exists(fname):
            if datatype in [ConsultDataTypes.TAQ.value, ConsultDataTypes.SETUP.value] :
                return dict()
            else: 
                return []

        with open(fname, 'r') as openfile:
            json_object = json.load(openfile)

    return json_object



### ----------------------------------
### ----------------------------------
### DATA TYPING
### ----------------------------------
### ----------------------------------

### HELPER CLASSES

# Helps create JSON encoding from nested classes
class EvidenceDataEncoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__
        
class Dictable:
    def to_dict(self):
        return json.loads(json.dumps(self, cls=EvidenceDataEncoder))
        
# Base class for nested classes where we'll input data as dict (for ease)
class DictInitClass (Dictable):
    attrs = []
    
    def __init__(self, datadict=dict()):
        for k in self.attrs:
            if k in list(datadict.keys()):
                setattr(self, k, datadict[k])
            else:
                setattr(self, k, "")

class SuspiciousLogins(DictInitClass):
    attrs = ['recognize',
             'describe_logins',
             'login_screenshot',
             'activity_log',
             'describe_activity',
             'activity_screenshot']

class PasswordCheck(DictInitClass):
    attrs = ['know', 'guess']

class RecoverySettings(DictInitClass):
    attrs = ['phone_present',
             'phone',
             'phone_access',
             'phone_screenshot',
             'email_present', 
             'email', 
             'email_access', 
             'email_screenshot']

class TwoFactorSettings(DictInitClass):
    attrs = ['enabled',
             'second_factor_type',
             'describe',
             'second_factor_access',
             'screenshot']


class SecurityQuestions(DictInitClass):
    attrs = ['present', 
             'questions', 
             'know',
             'screenshot']
    
class PermissionInfo(DictInitClass):
    attrs = ['permission_name',
             'reason',
             'access',
             'describe',
             'screenshot']
    
class InstallInfo(DictInitClass):
    attrs = ['knew_installed',
             'installed',
             'coerced',
             'screenshot']
    
    
class AppInfo(Dictable):
    def __init__(self,
                 title="",
                 app_name="",
                 appId="",
                 flags=[],
                 application_icon="",
                 app_website="",
                 description="",
                 developerwebsite="",
                 investigate=False,
                 permissions=[],
                 install_info=dict(),
                 notes=dict(),
                 **kwargs):
        
        self.title = title
        self.app_name = app_name
        if self.app_name.strip() == "":
            self.app_name = title
        if self.app_name.strip() == "":
            self.app_name = appId
        self.appId = appId
        self.flags = flags
        self.application_icon = application_icon
        self.app_website = app_website
        self.description = description
        self.developerwebsite = developerwebsite
        self.investigate = investigate

        # TODO: fix actual permissions

        placeholder_permissions = [{
            "permission_name": "Camera",
            "reason": "Needed to capture photos",
        }]
        
        self.permissions = [PermissionInfo(p) for p in placeholder_permissions]

        self.install_info = InstallInfo(install_info)
        self.notes = Notes(notes)

        self.report, self.is_concerning = self.generate_app_report()

    def generate_app_report(self, second_person=True, harmdoer="the person of concern"):
        agent = "you"
        pronoun = "you"
        if second_person:
            agent = "the client"
            pronoun = "they"
        
        spyware = 'spyware' in self.flags

        sentences = []
        concern = False

        if spyware:
            concern = True
            sentences.append("{} is an app designed for surveillance.".format(self.title))

        # for all apps, look at install information
        if self.install_info.knew_installed != 'yes':
            concern = True
            sentences.append("{} did not know that this app was installed on the device.".format(agent.capitalize()))
            if "system-app" in self.flags:
                sentences.append("However, this is a system app which was likely installed on the phone when it was purchased.".format(agent.capitalize()))
            elif spyware:
                sentences.append("This indicates that another person installed the app with the intention of surveilling {}. Installing the app would require physical access to the device.".format(agent))

        elif self.install_info.installed != 'yes':
            if "system-app" in self.flags:
                sentences.append("{} did not install this app. However, this is a system app which was likely installed on the phone when it was purchased.".format(agent.capitalize()))
            else:
                concern = True
                if self.install_info.installed == 'no':
                    sentences.append("{} knew this app was installed on the phone, but did not install it.".format(agent.capitalize()))
                if self.install_info.installed == 'unsure':
                    sentences.append("{} knew this app was installed on the phone, but {} are unsure whether {} installed it.".format(agent.capitalize(), pronoun, pronoun))
                sentences.append("This indicates that another person installed this app, which would require physical access to the device.")


        elif self.install_info.coerced != 'no':
            concern = True
            sentences.append("{} coerced {} to install this app, indicating that person is using the app to surveil {}.".format(harmdoer.capitalize(), agent, agent))
        else:
            sentences.append("{} installed this app voluntarily.".format(agent.capitalize()))

        # for spyware apps, look at permission stuff
        if not spyware:
            any_issues = False
            for perm in self.permissions:
                if perm.access == 'yes':
                    any_issues = True
                    concern = True
                    sentences.append("{} can use this app to access the phone's {}.".format(harmdoer.capitalize(), perm.permission_name.lower()))

            if not any_issues:
                sentences.append("There is no evidence that this app is being used maliciously against {}.".format(agent))

        return " ".join(sentences), concern


class CheckApps(Dictable):
    def __init__(self, 
                 spyware=list(), 
                 dualuse=list(), 
                 other=list(), 
                 **kwargs):
        pprint(spyware)
        pprint(dualuse)
        pprint(other)
        self.spyware = [AppInfo(app) for app in spyware]
        self.dualuse = [AppInfo(app) for app in dualuse]
        self.other = [AppInfo(app) for app in other]

class TAQDevices(DictInitClass):
    attrs = ['live_together', 
             'physical_access']

class TAQAccounts(DictInitClass):
    attrs = ['pwd_mgmt', 
             'pwd_comp', 
             'pwd_comp_which']

class TAQSharing(DictInitClass):
    attrs = ['share_phone_plan', 
             'phone_plan_admin',
             'share_accounts']

class TAQSmarthome(DictInitClass):
    attrs = ['smart_home',
             'smart_home_setup',
             'smart_home_access',
             'smart_home_account']

class TAQKids(DictInitClass):
    attrs = ['custody',
             'child_phys_access',
             'child_phone_plan']

class TAQLegal(DictInitClass):
    attrs = ['legal']

class Notes(DictInitClass):
    attrs = ['client_notes', 'consultant_notes']

class RiskFactor():
    
    def __init__(self, risk, description):
        self.risk = risk
        self.description = description


### REAL CLASSES

class ConsultationData(Dictable):

    def generate_overall_summary(self):
         return "TODO: WRITE CODE TO GENERATE AN OVERALL SUMMARY"
        
    def __init__(self,
                 setup,
                 taq,
                 accounts,
                 scans,
                 screenshot_dir,
                 **kwargs):
        self.setup = ConsultSetupData(**setup)
        self.taq = TAQData(**taq)
        self.accounts = [AccountInvestigation(**account) for account in accounts]
        self.concerning_accounts = [acct for acct in self.accounts if acct.is_concerning]
        self.scans = [ScanData(**scan) for scan in scans]
        self.screenshot_dir = screenshot_dir

        self.overall_summary = self.generate_overall_summary()


class AccountInvestigation(Dictable):
    def __init__(self, 
                 account_id=0,
                 platform="", 
                 account_nickname="", 
                 suspicious_logins=dict(),
                 password_check=dict(), 
                 recovery_settings=dict(),  
                 two_factor_settings=dict(),
                 security_questions=dict(),
                 notes=dict(), 
                 **kwargs):
        self.account_id = account_id
        self.platform = platform
        self.account_nickname = account_nickname
        if self.account_nickname.strip() == "":
            self.account_nickname = platform
        self.suspicious_logins = SuspiciousLogins(suspicious_logins)
        self.password_check = PasswordCheck(password_check)
        self.recovery_settings = RecoverySettings(recovery_settings)
        self.two_factor_settings = TwoFactorSettings(two_factor_settings)
        self.security_questions = SecurityQuestions(security_questions)
        self.notes = Notes(notes)

        self.access_report, self.ability_report, self.access_concern, self.ability_concern = self.generate_reports()

        self.is_concerning = self.access_concern or self.ability_concern


    def generate_reports(self, second_person=True, harmdoer="the person of concern"):
        agent = "you"
        pronoun = "you"
        possessive = "your"
        if second_person:
            agent = "the client"
            pronoun = "they"
            possessive = "their"

        # generally, more high level because there is a lot going on.
        access_sentences = []
        access_concern = False

        # Suspicious logins
        suspicious_logins = False
        if self.suspicious_logins.recognize != "yes":
            access_concern = True
            suspicious_logins = True
            if self.suspicious_logins.describe_logins != "":
                access_sentences.append("There is evidence that someone other than {} is currently logged into this account using {}.".format(agent, self.suspicious_logins.describe_logins))
            else:
                access_sentences.append("There is evidence that someone other than {} is currently logged into this account.".format(agent))
        elif self.suspicious_logins.activity_log != "no":
            access_concern = True
            suspicious_logins = True
            access_sentences.append("There is evidence that someone other than {} has recently logged into this account.".format(agent))
        else:
            access_sentences.append("There is no evidence that someone other than {} has logged into this account recently.".format(agent))

        # Passwords
        pwd = False
        if self.password_check.know != 'no' or self.password_check.guess != 'no':
            pwd = True

        # Recovery details
        recovery = False
        if (self.recovery_settings.email_present == 'yes' and self.recovery_settings.email_access != 'no'
            ) or (
            self.recovery_settings.phone_present == 'yes' and self.recovery_settings.phone_access != 'no'
            ):
            recovery = True

        # Two-factor
        twofactor = False
        if self.two_factor_settings.enabled == 'yes' and self.two_factor_settings.second_factor_access != 'no':
            twofactor = True

        # Security questions
        questions = False
        if self.security_questions.present and self.security_questions.know != 'no':
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
                ability_sentences.append("There is {}evidence that {} can access this account via these methods: {}.".format(also, harmdoer, ", ".join(methods)))
            else:
                ability_sentences.append("There is {}evidence that {} can access this account via {}.".format(also, harmdoer, methods[0]))

            if twofactor:
                ability_sentences.append("{} has access to the second authentication factor; if they know the password, they could access this account without alerting {}.".format(harmdoer.capitalize(), agent))

        return " ".join(access_sentences), " ".join(ability_sentences), access_concern, ability_concern
        


class ScanData(Dictable):
    def __init__(self,
                 manual=False,
                 scan_id=0,
                 device_type="",
                 device_nickname="",
                 serial="",
                 device_model="",
                 device_version="",
                 device_manufacturer="",
                 is_rooted="",
                 rooted_reasons="",
                 all_apps=list(),
                 selected_apps=list(),
                 **kwargs):

        self.manual = manual
        self.scan_id = scan_id
        self.device_type = device_type
        self.device_nickname = device_nickname
        self.serial = serial
        self.device_model = device_model
        self.device_version = device_version
        self.device_manufacturer = device_manufacturer
        self.is_rooted = is_rooted
        self.rooted_reasons = rooted_reasons
        self.all_apps = [AppInfo(**app) for app in all_apps]
        self.selected_apps = [AppInfo(**app) for app in selected_apps]
        self.concerning_apps = [app for app in self.selected_apps if app.is_concerning]

        self.report = self.generate_report()

    def generate_report(self, harmdoer="the person of concern"):
        agent = "the client"

        report_sentences = []
        
        if self.is_rooted:
            report_sentences.append(
                "This device is jailbroken, giving the jailbreaker nearly unbounded "
                "access to the device and {}'s activity on the device.".format(
                    agent
                )
            )
        else: 
            report_sentences.append("This device is not jailbroken.")

        if len(self.selected_apps) == 0:
            report_sentences.append("No suspicious apps were found on this device.")
        else:
            '''
            plural = ""
            if len(self.selected_apps) > 1:
                plural = "s"
            report_sentences.append(
                "{} potentially malicious app{} investigated.".format(
                    len(self.selected_apps), plural
                )
            )
            '''

            if len(self.concerning_apps) > 0:
                plural = ""
                verb_plural = "s"
                if len(self.concerning_apps) > 1:
                    plural = "s"
                    verb_plural = ""

                report_sentences.append(
                    "{} app{} pose{} a concern: {}.".format(
                        len(self.concerning_apps), plural, verb_plural, ", ".join([app.title for app in self.concerning_apps])
                    )
                )
            else: 
                report_sentences.append(
                    "No apps determined to pose a concern."
                )

        if self.manual:
            report_sentences.append("This device was not automatically scanned; instead, apps were manually investigated.")

        return " ".join(report_sentences)


class TAQData(Dictable):
    def __init__(self,
                 devices=dict(),
                 accounts=dict(),
                 sharing=dict(),
                 smarthome=dict(),
                 kids=dict(),
                 legal=dict(), 
                 **kwargs):
        self.devices = TAQDevices(devices)
        self.accounts = TAQAccounts(accounts)
        if self.accounts.pwd_comp_which.strip() == "":
            self.accounts.pwd_comp_which = "[Not provided]"
        self.sharing = TAQSharing(sharing)
        if self.sharing.phone_plan_admin == []:
            self.sharing.phone_plan_admin = ""
        self.smarthome = TAQSmarthome(smarthome)
        self.kids = TAQKids(kids)
        self.legal = TAQKids(legal)

        self.risk_factors = self.get_risk_factors()

    def get_risk_factors(self, second_person=True, harmdoer="the person of concern"):
        agent = "you"
        pronoun = "you"
        if second_person:
            agent = "the client"
            pronoun = "they"

        risk_factors = []

        # accounts
        if self.accounts.pwd_comp != 'no':
            risk_factors.append(RiskFactor(
                risk="Risk from password compromise",
                description="{} believes that {} knows some passwords. Compromised passwords: {}. "
                            "This could allow {} access to {}'s accounts.".format(
                                agent.capitalize(), harmdoer, self.accounts.pwd_comp_which, harmdoer, agent
                            )           
                )
            )
        # TODO: Should we ask if the abuser has accesss to pwd management methods?

        # devices
        if self.devices.live_together == 'yes':
            risk_factors.append(RiskFactor(
                risk="Risk from device access",
                description="{} lives with {}, giving {} physical access to {}'s devices. "
                            "With physical access to devices, it is possible that {} could "
                            "install spyware or access online accounts, and see private information.".format(
                                agent.capitalize(),harmdoer,harmdoer,agent,harmdoer
                            ))
            )
        elif self.devices.physical_access == 'yes':
            risk_factors.append(RiskFactor(
                risk="Risk from device access",
                description="{} has had physical access to {}'s devices. "
                "With physical access to devices, it is possible that {} could "
                "install spyware, access online accounts, and see private information.".format(
                    harmdoer.capitalize(), agent, harmdoer
                )))

        # sharing
        if self.sharing.share_phone_plan == 'yes':
            admin = ""
            if self.sharing.phone_plan_admin.strip() != "":
                admin = ", {},".format(self.sharing.phone_plan_admin)
            risk_factors.append(RiskFactor(
                risk="Risk from shared phone plan",
                description="{} shares a phone plan with {}. This may leak information including call and text history or location. The administrator{} likely has even more privileged access to such information.".format(
                    agent.capitalize(), harmdoer, admin
                )
            ))
        if self.sharing.share_accounts == 'yes':
            risk_factors.append(RiskFactor(
                risk="Risk from shared accounts",
                description="Some accounts are shared with {}, meaning {} can see any information and activity on those accounts.".format(
                    harmdoer, harmdoer
                )
            ))

        # kids
        if self.kids.custody == 'yes':
            if self.kids.child_phone_plan == 'yes':
                risk_factors.append(RiskFactor(
                    risk="Risk from child's phone plan",
                    description="{}'s child shares a phone plan with {}. This may leak information including the child's call and text history or location.".format(
                        agent.capitalize(), harmdoer
                    )
                ))
            if self.kids.child_phys_access != 'no':
                risk_factors.append(RiskFactor(
                    risk="Risk from child's devices",
                    description="{} has had physical access to devices owned by {}'s child. "
                    "With physical access to these devices, it is possible that {} could "
                    "install spyware, access online accounts, and see private information, "
                    "including information about {}.".format(
                        harmdoer.capitalize(), agent, harmdoer, agent
                    )
                ))

        if self.smarthome.smart_home == 'yes':
            # TODO: we should ask what devices they have to give more details about the risks

            smarthome_risk = False
            risk_reasons = []

            # physical access
            if self.smarthome.smart_home_setup == 'poc':
                smarthome_risk = True
                risk_reasons.append("{} set up some of the smart home devices in {}'s home.".format(harmdoer.capitalize(), agent))
            elif self.smarthome.smart_home_access == 'yes':
                smarthome_risk = True
                risk_reasons.append("{} had physical access to some of the smart home devices in {}'s home.".format(harmdoer.capitalize(), agent))
            
            # account
            if self.smarthome.smart_home_account == 'yes':
                smarthome_risk = True
                also = ""
                if len(risk_reasons) > 0:
                    also = "also "
                risk_reasons.append("{} can {}access accounts connected to smart home devices in {}'s home.".format(harmdoer.capitalize(), also, agent))
            
            # combine risks
            if smarthome_risk:
                risk_factors.append(RiskFactor(
                    risk="Risk from smart home devices",
                    description="{} As a result, {} may be able to see data collected by those smart home devices.".format(
                        " ".join(risk_reasons), harmdoer
                    )
                ))

        return risk_factors

class ConsultSetupData(Dictable):
    def __init__(self, 
                 client="",
                 date="", 
                 **kwargs):
        self.client = client
        self.date = date
    

def get_scan_by_ser(ser, all_scan_data: list[ScanData]):

    for scan in all_scan_data:
        if scan.serial == ser:
            return scan
    
    return ScanData()



def update_scan_by_ser(new_scan: ScanData, all_scan_data: list[ScanData]):

    for i in range(len(all_scan_data)):
        scan = all_scan_data[i]

        # if serial numbers match, replace with the new one
        if scan.serial == new_scan.serial:
            all_scan_data[i] = new_scan
            return all_scan_data
    
    all_scan_data.append(new_scan)
    return all_scan_data

class ConsultDataTypes(Enum):
    TAQ = 1
    SCANS = 2
    ACCOUNTS = 3
    SETUP = 4

def get_data_filename(datatype: ConsultDataTypes):

    if datatype == ConsultDataTypes.SETUP.value:
        return "setup.json"
    elif datatype == ConsultDataTypes.TAQ.value:
        return "taq.json"
    elif datatype == ConsultDataTypes.SCANS.value:
        return "scans.json"
    else:
        return "accounts.json"


# Save data to the right tmp file as JSON
# Overwrites it always, assume any previous data has been incorporated
def save_data_as_json(data, datatype: ConsultDataTypes):

    json_object = json.dumps(data, cls=EvidenceDataEncoder)

    fname = os.path.join(TMP_CONSULT_DATA_DIR, get_data_filename(datatype))

    with open(fname, 'w') as outfile:
        outfile.write(json_object)

    return

def load_json_data(datatype: ConsultDataTypes):

    fname = os.path.join(TMP_CONSULT_DATA_DIR, get_data_filename(datatype))
    if not os.path.exists(fname):
        if datatype in [ConsultDataTypes.TAQ, ConsultDataTypes.SETUP] :
            return dict()
        else: 
            return []

    with open(fname, 'r') as openfile:
        json_object = json.load(openfile)

    return json_object
