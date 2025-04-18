import hashlib
import hmac
import os, sys
import secrets
import shlex
from pathlib import Path
import platform
import logging
import logging.handlers as handlers

def setup_logger():
    """
    Set up a logger with a rotating file handler.

    The logger will write in a file named 'app.log' in the 'logs' directory.
    The log file will rotate when it reaches 100,000 bytes, keeps a maximum of 30 files.

    Returns:
        logging.Logger: The configured logger object.
    """
    handler = handlers.RotatingFileHandler(
        "logs/app.log", maxBytes=100000, backupCount=30
    )

    logging.basicConfig(
        format='%(filename)s:%(lineno)d - %(message)s', 
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


DEV_SUPPRTED = ["android", "ios"]  # 'windows', 'mobileos', later
THIS_DIR = Path(__file__).absolute().parent

# Used by data_process only.
source_files = {
    "playstore": "static_data/android_apps_crawl.csv.gz",
    "appstore": "static_data/ios_apps_crawl.csv.gz",
    "offstore": "static_data/offstore_apks.csv",
}
spyware_list_file = "static_data/spyware.csv"  # hand picked


# ---------------------------------------------------------
DEBUG = bool(int(os.getenv("DEBUG", "0")))
TEST = bool(int(os.getenv("TEST", "0")))

DEVICE_PRIMARY_USER = {
    "me": "Me",
    "child": "A child of mine",
    "partner": "My current partner/spouse",
    "family_other": "Another family member",
    "other": "Someone else",
}

ANDROID_PERMISSIONS_CSV = "static_data/android_permissions.csv"
IOS_DUMPFILES = {
    "Jailbroken-FS": "ios_jailbroken.log",
    "Jailbroken-SSH": "ios_jailbreak_ssh.retcode",
    "Apps": "ios_apps.json",
    "Info": "ios_info.json",
}

TEST_APP_LIST = "static_data/android.test.apps_list"
# TITLE = "Anti-IPS: Stop Intimate Partner Surveillance"

TITLE = {"title": "IPV Spyware Discovery (ISDi){}".format(" (test)" if TEST else "")}


APP_FLAGS_FILE = "static_data/app-flags.csv"
APP_INFO_SQLITE_FILE = "sqlite:///static_data/app-info.db"

# IOC stalkware indicators
IOC_PATH = "stalkerware-indicators"
IOC_FILE = os.path.join(IOC_PATH, "ioc.yaml")

# we will resolve the database path using an absolute path to __FILE__ because
# there are a couple of sources of truth that may disagree with their "path
# relavitity". Needless to say, FIXME
SQL_DB_PATH = f"sqlite:///{str(THIS_DIR / 'data/fieldstudy.db')}"
# SQL_DB_CONSULT_PATH = 'sqlite:///data/consultnotes.db' + ("~test" if TEST else "")


def set_test_mode(test):
    """
    Sets the test mode to the given value and returns the new values of APP_FLAGS_FILE and SQL_DB_PATH.
    """
    app_flags_file, sql_db_path = APP_FLAGS_FILE, SQL_DB_PATH
    if test:
        if not app_flags_file.endswith("~test"):
            app_flags_file = APP_FLAGS_FILE + "~test"
        if not sql_db_path.endswith("~test"):
            sql_db_path = sql_db_path + "~test"
    else:
        if app_flags_file.endswith("~test"):
            app_flags_file = app_flags_file.replace("~test", "")
        if sql_db_path.endswith("~test"):
            sql_db_path = sql_db_path.replace("~test", "")
    return app_flags_file, sql_db_path


APP_FLAGS_FILE, SQL_DB_PATH = set_test_mode(TEST)


STATIC_DATA = THIS_DIR / "static_data"

# TODO: We should get rid of this, ADB_PATH is very confusing
ANDROID_HOME = os.getenv("ANDROID_HOME", "")
PLATFORM = platform.system().lower()
if 'microsoft' in platform.release().lower(): ## Check for wsl
    PLATFORM = "wsl" 

LIBIMOBILEDEVICE_PATH = "pymobiledevice3.exe" if PLATFORM == "wsl" \
    else "pymobiledevice3"
ADB_PATH = shlex.quote(os.path.join(ANDROID_HOME, "adb")) \
    + (".exe" if PLATFORM in ("wsl", "win32") else "")


DUMP_DIR = THIS_DIR / "phone_dumps"
SCRIPT_DIR = THIS_DIR / "scripts"

DATE_STR = "%Y-%m-%d %I:%M %p"
ERROR_LOG = []

APPROVED_INSTALLERS = {"com.android.vending", "com.sec.android.preloadinstaller"}

REPORT_PATH = THIS_DIR / "reports"
PII_KEY_PATH = STATIC_DATA / "pii.key"


def open_or_create_random_key(fpath, keylen=32):
    """
    Opens the file at the given path or creates a new file with a random key of the specified length.

    Args:
        fpath (str): The path to the file.
        keylen (int, optional): The length of the random key. Defaults to 32.

    Returns:
        bytes: The contents of the file as bytes.
    """

    def create():
        with fpath.open("wb") as f:
            f.write(secrets.token_bytes(keylen))

    if not fpath.exists():
        create()
    k = fpath.open("rb").read(keylen)
    if len(k) != keylen:
        create()
    return fpath.open("rb").read()


PII_KEY = open_or_create_random_key(PII_KEY_PATH, keylen=32)

FLASK_SECRET_PATH = STATIC_DATA / "flask.secret"
FLASK_SECRET = open_or_create_random_key(FLASK_SECRET_PATH)

if not REPORT_PATH.exists():
    os.mkdir(REPORT_PATH)


def hmac_serial(ser: str) -> str:
    """Returns a string starting with HSN_<hmac(ser)>. If ser already have 'HSN_',
    it returns the same value."""
    if ser.startswith("HSN_"):
        return ser
    hser = hmac.new(PII_KEY, ser.encode("utf8"), digestmod=hashlib.sha256).hexdigest()[:8]
    return f"HSN_{hser}"


def add_to_error(*args):
    global ERROR_LOG
    m = "\n".join(str(e) for e in args)
    print(m)
    ERROR_LOG.append(m)


def error():
    global ERROR_LOG
    e = ""
    if len(ERROR_LOG) > 0:
        e, ERROR_LOG = ERROR_LOG[0], ERROR_LOG[1:]

        print(f"ERROR: {e}")
    return e.replace("\n", "<br/>")
