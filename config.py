from pathlib import Path
import os
import shlex
from sys import platform

DEV_SUPPRTED = ['android', 'ios']    # 'windows', 'mobileos', later

# Used by data_process only.
source_files = {
    'playstore': 'static_data/android_apps_crawl.csv.gz',
    'appstore': 'static_data/ios_apps_crawl.csv.gz',
    'offstore': 'static_data/offstore_apks.csv',
}
spyware_list_file = 'static_data/spyware.csv'   # hand picked

# ---------------------------------------------------------
DEBUG = True
TEST = False


TEST_APP_LIST = 'static_data/android.test.apps_list'
TITLE = "Anti-IPS: Stop Intimate Partner Surveillance"
APP_FLAGS_FILE = 'static_data/app-flags.csv'
APP_INFO_FILE = 'static_data/app-info.csv'
APP_INFO_SQLITE_FILE = 'sqlite:///static_data/app-info.db' + ("~test" if TEST else "")
SQL_DB_PATH = 'sqlite:///data/fieldstudy.db' + ("~test" if TEST else "")


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


THISDIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DATA = os.path.join(THISDIR, 'static_data')
ANDROID_HOME = os.getenv('ANDROID_HOME', STATIC_DATA)
PLATFORM = 'darwin' if platform == 'darwin' else 'linux' if platform.startswith('linux') \
           else 'win32' if platform == 'win32' else None
ADB_PATH = shlex.quote(os.path.join(ANDROID_HOME, 'adb-' + PLATFORM))
# MOBILEDEVICE_PATH = 'mobiledevice'
# MOBILEDEVICE_PATH = os.path.join(THISDIR, "mdf")  #'python2 -m MobileDevice'
MOBILEDEVICE_PATH = shlex.quote(os.path.join(STATIC_DATA, "ios-deploy-" + PLATFORM))

DUMP_DIR = os.path.join(THISDIR, 'phone_dumps')
SCRIPT_DIR = os.path.join(THISDIR, 'scripts')

ERROR_LOG = []

APPROVED_INSTALLERS = {'com.android.vending', }

REPORT_PATH = os.path.join(THISDIR, 'reports')
if not os.path.exists(REPORT_PATH):
    os.mkdir(REPORT_PATH)

def add_to_error(*args):
    global ERROR_LOG
    m = '\n'.join(str(e) for e in args)
    print(m)
    ERROR_LOG.append(m)


def error():
    global ERROR_LOG
    e = ''
    if len(ERROR_LOG)>0:
        e, ERROR_LOG = ERROR_LOG[0], ERROR_LOG[1:]

        print("ERROR: {}".format(e))
    return e.replace("\n", "<br/>")

