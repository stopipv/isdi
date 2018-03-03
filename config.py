from pathlib import Path
import os

DEV_SUPPRTED = ['android', 'ios']    # 'windows', 'mobileos', later
APPS_LIST = {
    'android': 'android_apps_crawl.csv',
    'ios': 'ios_apps_crawl.csv',
}
TEST_APP_LIST = 'android.test.apps_list' 
TITLE = "Anti-IPS: Stop intiimate partner surveillance"

ANDROID_HOME = os.getenv('ANDROID_HOME', './platform-tools')
ADB_PATH = os.path.join(ANDROID_HOME, 'adb')
MOBILEDEVICE_PATH = 'mobiledevice'

DUMP_DIR = './phone_dumps'


DEBUG = True
