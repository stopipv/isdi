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

ANDROID_HOME = os.getenv('ANDROID_HOME', './.platform-tools')
ADB_PATH = os.path.join(ANDROID_HOME, 'adb')
MOBILEDEVICE_PATH = 'mobiledevice'

DUMP_DIR = './phone_dumps'


DEBUG = True
