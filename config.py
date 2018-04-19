from pathlib import Path
import os

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
TEST = True 


TEST_APP_LIST = 'static_data/android.test.apps_list'
TITLE = "Anti-IPS: Stop intiimate partner surveillance"
APP_FLAGS_FILE = 'static_data/app-flags.csv'+ ("~test" if TEST else "")
APP_INFO_FILE = 'static_data/app-info.csv'
APP_INFO_SQLITE_FILE = 'sqlite:///static_data/app-info.db'+ ("~test" if TEST else "")
SQL_DB_PATH = 'sqlite:///data/fieldstudy.db' + ("~test" if TEST else "")

THISDIR = os.path.dirname(os.path.abspath(__file__))
ANDROID_HOME = os.getenv('ANDROID_HOME', './.platform-tools')
ADB_PATH = os.path.join(ANDROID_HOME, 'adb')
# MOBILEDEVICE_PATH = 'mobiledevice'
# MOBILEDEVICE_PATH = os.path.join(THISDIR, "mdf")  #'python2 -m MobileDevice'
MOBILEDEVICE_PATH = os.path.join(THISDIR, "ios-deploy/build/Release/ios-deploy")  #'python2 -m MobileDevice'

DUMP_DIR = os.path.join(THISDIR, 'phone_dumps')

ERROR_LOG = []



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
    return e

