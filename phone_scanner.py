#!/usr/bin/env python3

import subprocess
import pandas as pd
from config import DEV_SUPPRTED, APPS_LIST, TEST_APP_LIST


class AppScan(object):
    device_type = ''

    def __init__(self, dev_type):
        assert dev_type in DEV_SUPPRTED, \
            "dev={!r} is not supported yet. Allowed={}".format(dev_type, DEV_SUPPRTED)
        self.device_type = dev_type

    def setup(self):
        """If the device needs some setup to work."""
        pass

    def get_apps(self):
        pass

    def find_spyapps(self):
        installed_apps = self.get_apps()
        fname = APPS_LIST.get(self.device_type)
        app_list = pd.read_csv(fname, index_col='appId')
        return app_list.loc[set(installed_apps) & set(app_list.index), 'title']\
            .apply(lambda x: x.encode('ascii', errors='ignore'))

    def uninstall(self):
        pass


class AndroidScan(AppScan):
    """
    NEED Android Debug Bridge (adb) tool installed. Ensure your Android device is connected
    through Developer Mode with USB Debugging enabled, and `adb devices` showing the device as
    connected before running this scan function.
    """

    def __init__(self):
        super(AndroidScan, self).__init__('android')

    def setup(self):
        subprocess.call(
            'adb kill-server; adb start-server', shell=True
        )

    def get_apps(self):
        installed_apps = subprocess.run(
            'adb shell pm list packages -f | sed -e "s/.*=//" | sed "s/\r//g" | sort',
            stdout=subprocess.PIPE, shell=True
        )

        if installed_apps.returncode != 0:
            print("Error running Android device scan. Is the Android Debug Bridge (adb)"
                  "tool installed on this machine?")
            try:
                print("Attempting to start Debug Server...")
                self.setup()
                print("Android Debug Server is online! Re-run the scan tool!")
            except Exception as e:
                print(e)
                return
        installed_apps = installed_apps.stdout.decode()
        installed_apps = installed_apps.split('\n')

        return installed_apps


'''
NEED https://github.com/imkira/mobiledevice installed
(`brew install mobiledevice` or build from source).
'''


class IosScan(AppScan):
    def __init__(self):
        super(IosScan, self).__init__('ios')

    def get_apps(self):
        installed_apps = subprocess.run(['mobiledevice', 'list_apps'], stdout=subprocess.PIPE)
        if installed_apps.returncode != 0:
            print("Error running iOS device scan. Is the 'https://github.com/imkira/mobiledevice"
                  "code installed on this Mac?")
            exit(1)
        installed_apps = installed_apps.stdout
        installed_apps = installed_apps.split('\n').tolist()
        return installed_apps


class TestScan(AppScan):
    def __init__(self):
        super(TestScan, self).__init__('android')

    def get_apps(self):
        installed_apps = open(TEST_APP_LIST, 'r').read().splitlines()
        return installed_apps


if __name__ == "__main__":
    pass
