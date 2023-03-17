from pathlib import Path
import os
import shlex
from sys import platform
from runcmd import run_command, catch_err
import hashlib
import hmac

DEV_SUPPRTED = ['android', 'ios']    # 'windows', 'mobileos', later
THIS_DIR = Path(__file__).absolute().parent

# Used by data_process only.
source_files = {
    'playstore': 'static_data/android_apps_crawl.csv.gz',
    'appstore': 'static_data/ios_apps_crawl.csv.gz',
    'offstore': 'static_data/offstore_apks.csv',
}
spyware_list_file = 'static_data/spyware.csv'   # hand picked

# ---------------------------------------------------------
DEBUG = bool(int(os.getenv("DEBUG", "0")))
TEST = bool(int(os.getenv("TEST", "0")))

DEVICE_PRIMARY_USER = {
    'me': 'Me',
    'child': 'A child of mine',
    'partner': 'My current partner/spouse',
    'family_other': 'Another family member',
    'other': 'Someone else'
}

ANDROID_PERMISSIONS_CSV = 'static_data/android_permissions.csv'
IOS_DUMPFILES = {'Jailbroken-FS': 'ios_jailbroken.log', 
                 'Jailbroken-SSH': 'ios_jailbreak_ssh.retcode',
                 'Apps': 'ios_apps.plist', 'Info': 'ios_info.xml'}

TEST_APP_LIST = 'static_data/android.test.apps_list'
#TITLE = "Anti-IPS: Stop Intimate Partner Surveillance"

TITLE = {'title': "IPV Spyware Discovery (ISDi){}".format(" (test)" if TEST else '')}

APP_FLAGS_FILE = 'static_data/app-flags.csv'
APP_INFO_SQLITE_FILE = 'sqlite:///static_data/app-info.db' + \
    ("~test" if TEST else "")

# IOC stalkware indicators
IOC_PATH = "data/stalkerware-indicators/"
IOC_FILE = IOC_PATH + "ioc.yaml"


# we will resolve the database path using an absolute path to __FILE__ because
# there are a couple of sources of truth that may disagree with their "path
# relavitity". Needless to say, FIXME
SQL_DB_PATH = "sqlite:///{}".format(str(THIS_DIR / "data/fieldstudy.db"))
#SQL_DB_CONSULT_PATH = 'sqlite:///data/consultnotes.db' + ("~test" if TEST else "")


def set_test_mode(test):
    global TEST, APP_FLAGS_FILE, SQL_DB_PATH
    TEST = test
    if TEST:
        if not APP_FLAGS_FILE.endswith('~test'):
            APP_FLAGS_FILE = APP_FLAGS_FILE + "~test"
        if not SQL_DB_PATH.endswith('~test'):
            SQL_DB_PATH = SQL_DB_PATH + "~test"
    else:
        if APP_FLAGS_FILE.endswith('~test'):
            APP_FLAGS_FILE = APP_FLAGS_FILE.replace("~test", '')
        if SQL_DB_PATH.endswith('~test'):
            SQL_DB_PATH = SQL_DB_PATH.replace("~test", '')


set_test_mode(TEST)


STATIC_DATA = THIS_DIR / 'static_data'

# TODO: We should get rid of this, ADB_PATH is very confusing
ANDROID_HOME = os.getenv('ANDROID_HOME', STATIC_DATA)
PLATFORM = ('darwin' if platform == 'darwin'
            else 'linux' if platform.startswith('linux')
            else 'win32' if platform == 'win32' else None)
ADB_PATH = os.path.join(ANDROID_HOME, 'adb-', PLATFORM)

#LIBIMOBILEDEVICE_PATH = shlex.quote(str(STATIC_DATA / ("libimobiledevice-" + PLATFORM)))
LIBIMOBILEDEVICE_PATH = ''
# MOBILEDEVICE_PATH = 'mobiledevice'
# MOBILEDEVICE_PATH = os.path.join(THISDIR, "mdf")  #'python2 -m MobileDevice'
MOBILEDEVICE_PATH = shlex.quote(str(STATIC_DATA / ("ios-deploy-" + PLATFORM)))

DUMP_DIR = THIS_DIR / 'phone_dumps'
SCRIPT_DIR = THIS_DIR / 'scripts'

DATE_STR = '%Y-%m-%d %I:%M %p'
ERROR_LOG = []

APPROVED_INSTALLERS = {
    'com.android.vending',
    'com.sec.android.preloadinstaller'}

REPORT_PATH = THIS_DIR / 'reports'
PII_KEY_PATH = STATIC_DATA / "pii.key"
def open_or_create_random_key(fpath, keylen=32):
    def create():
        import secrets
        with fpath.open('wb') as f:
            f.write(secrets.token_bytes(keylen))

    if not fpath.exists():
        create()
    k = fpath.open('rb').read(keylen)
    if len(k) != keylen:
        creatte()
    return fpath.open('rb').read()

PII_KEY = open_or_create_random_key(PII_KEY_PATH, keylen=32)

FLASK_SECRET_PATH = STATIC_DATA / "flask.secret"
FLASK_SECRET = open_or_create_random_key(FLASK_SECRET_PATH)

if not REPORT_PATH.exists():
    os.mkdir(REPORT_PATH)


def hmac_serial(ser):
    return hmac.new(PII_KEY, ser.encode('utf8'),
                    digestmod=hashlib.sha256).hexdigest()


def add_to_error(*args):
    global ERROR_LOG
    m = '\n'.join(str(e) for e in args)
    print(m)
    ERROR_LOG.append(m)


def error():
    global ERROR_LOG
    e = ''
    if len(ERROR_LOG) > 0:
        e, ERROR_LOG = ERROR_LOG[0], ERROR_LOG[1:]

        print("ERROR: {}".format(e))
    return e.replace("\n", "<br/>")
