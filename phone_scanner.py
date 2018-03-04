#!/usr/bin/env python3

import subprocess
import pandas as pd
import config
from config import DEV_SUPPRTED, APPS_LIST, TEST_APP_LIST, DEBUG
import gzip
import os
import dataset
from datetime import datetime

if DEBUG:
    TEST = '~test'
else:
    TEST = ''

db = dataset.connect('sqlite:///fieldstudy.db' + TEST)


class AppScan(object):
    device_type = ''

    def __init__(self, dev_type, cli):
        assert dev_type in DEV_SUPPRTED, \
            "dev={!r} is not supported yet. Allowed={}"\
                .format(dev_type, DEV_SUPPRTED)
        self.device_type = dev_type
        self.cli = cli   # The cli of the device, e.g., adb or mobiledevice
        fname = APPS_LIST.get(self.device_type)
        self.stored_apps = pd.read_csv(fname, index_col='appId')

    def setup(self):
        """If the device needs some setup to work."""
        pass

    def devices(self):
        raise Exception("Not implemented")

    def get_apps(self, serialno):
        pass

    def app_details(self, appid):
        try:
            return self.stored_apps.loc[appid]
        except KeyError as ex:
            print(ex)
            return {}

    def find_spyapps(self, serialno):
        installed_apps = self.get_apps(serialno)
        app_list = self.stored_apps.query('relevant == "y"')
        return (app_list.loc[
            list(set(installed_apps) & set(app_list.index)), 'title'
        ].apply(lambda x: x.encode('ascii', errors='ignore')))

    def uninstall(self, serialno, appid):
        pass

    def run_command(self, cmd, **kwargs):
        _cmd = cmd.format(
            cli=self.cli, **kwargs
        )
        print(_cmd)
        p = subprocess.Popen(
            _cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        return p

    def save(self, **kwargs):
        try:
            tab = db.get_table('feedback')
            kwargs['time'] = datetime.now()
            tab.insert(kwargs)
            db.commit()
            return True
        except Exception as ex:
            print(ex)
            return False


class AndroidScan(AppScan):
    """NEED Android Debug Bridge (adb) tool installed. Ensure your Android device
    is connected through Developer Mode with USB Debugging enabled, and `adb
    devices` showing the device as connected before running this scan function.

    """

    def __init__(self):
        super(AndroidScan, self).__init__('android', config.ADB_PATH)

    def setup(self):
        p = self.run_command(
            '{cli} kill-server; {cli} start-server'
        )
        if p != 0:
            print("Setup failed with returncode={}.\nex={!r}"
                  .format(p, p.stderr.read()))
        self.devid = None

    def get_apps(self, serialno):
        cmd = '{cli} -s {serial} shell pm list packages -f -u | sed -e "s/.*=//" |'\
              ' sed "s/\r//g" | sort'
        p = self.run_command(cmd, serial=serialno); p.wait()

        if p.returncode != 0:
            print("Error running Android device scan. Error={}".format(
                p.stderr.read())
            )
            print("Retry in few second")
            self.setup()
            return []
        else:
            installed_apps = p.stdout.read().decode()
            installed_apps = installed_apps.split('\n')

            return installed_apps

    def devices(self):
        cmd = '{cli} devices | tail -n +2 | cut -f1'
        return [l.strip() for l in self.run_command(cmd)
                .stdout.read().decode('utf-8').split('\n') if l.strip()]

    def devices_info(self):
        cmd = '{cli} devices -l'
        return self.run_command(cmd).stdout.read().decode('utf-8')

    def dump_phone(self, serialno=None):
        if not serialno:
            serialno = self.devices()[0]
        cmd = '{cli} -s {serial} shell dumpsys'
        p = self.run_command(cmd, serial=serialno)
        outfname = os.path.join(config.DUMP_DIR, '{}.txt.gz'.format(serialno))
        # if p.returncode != 0:
        #     print("Dump command failed")
        #     return
        with gzip.open(outfname, 'w') as f:
            f.write(p.stdout.read())
        print("Dump success! Written to={}".format(outfname))

    def uninstall(self, appid, serialno):
        cmd = '{cli} -s {serial} uninstall {appid!r}'
        p = self.run_command(cmd, serial=serialno, appid=appid)
        p.wait()
        if p.returncode != 0:
            print("Error ({}) = {}".format(p.returncode, p.stderr.read()))
        return p.returncode == 0


class IosScan(AppScan):
    """
    NEED https://github.com/imkira/mobiledevice installed
    (`brew install mobiledevice` or build from source).
    """

    def __init__(self):
        super(IosScan, self).__init__('ios', config.MOBILEDEVICE_PATH)

    def get_apps(self):
        installed_apps = subprocess.run(
            ['mobiledevice', 'list_apps'], stdout=subprocess.PIPE
        )
        if installed_apps.returncode != 0:
            print("Error running iOS device scan. Is the "
                  "'https://github.com/imkira/mobiledevice"
                  "code installed on this Mac?")
            exit(1)
        installed_apps = installed_apps.stdout
        installed_apps = installed_apps.split('\n').tolist()
        return installed_apps

    def devices(self):
        cmd = '{cli} list_devices'
        return [l.strip() for l in self.run_command(cmd)\
                .stdout.read().decode('utf-8').split('\n') if l.strip()]


class TestScan(AppScan):
    def __init__(self):
        super(TestScan, self).__init__('android', cli='cli')

    def get_apps(self, serialno):
        assert serialno == 'testdevice1'
        installed_apps = open(TEST_APP_LIST, 'r').read().splitlines()
        return installed_apps

    def devices(self):
        return ["testdevice1", "testdevice2"]

    def uninstall(self, appid, serialno):
        return True


if __name__ == "__main__":
    sc = AndroidScan()
    print(sc.find_spyapps())
    print(sc.devices())
    sc.dump_phone()
