from pathlib import Path
import os

DEV_SUPPRTED = ['android', 'ios']    # 'windows', 'mobileos', later
APPS_LIST = {
    'android': 'data/android_apps_crawl.csv.gz',
    'ios': 'data/ios_apps_crawl.csv.gz',
    'test': 'data/test_android_apps_crawl.csv.gz'
}
OFFSTORE_APPS = 'data/offstore_apks.csv'
TEST_APP_LIST = 'android.test.apps_list' 
TITLE = "Anti-IPS: Stop intiimate partner surveillance"
APP_FLAGS_FILE = 'data/app-flags.csv'

THISDIR = os.path.dirname(os.path.abspath(__file__))
ANDROID_HOME = os.getenv('ANDROID_HOME', './.platform-tools')
ADB_PATH = os.path.join(ANDROID_HOME, 'adb')
# MOBILEDEVICE_PATH = 'mobiledevice'
# MOBILEDEVICE_PATH = os.path.join(THISDIR, "mdf")  #'python2 -m MobileDevice'
MOBILEDEVICE_PATH = os.path.join(THISDIR, "ios-deploy/build/Release/ios-deploy")  #'python2 -m MobileDevice'

DUMP_DIR = os.path.join(THISDIR, 'phone_dumps')


DEBUG = True
ERROR_LOG = []


def add_to_error(*args):
    m = '\n'.join(str(e) for e in args)
    print(m)
    ERROR_LOG.append(m)


def error():
    e = ''
    if len(ERROR_LOG)>0:
        e = ERROR_LOG.popleft()
        print("ERROR: {}".format(e))
    return e

