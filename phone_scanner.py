#!/usr/bin/env python3

import subprocess
import pandas as pd
import config
from config import DEV_SUPPRTED, APPS_LIST, TEST_APP_LIST, DEBUG
import gzip
import os
import dataset
from datetime import datetime
import parse_dump
from blacklist import flag_apps
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
        if ('relevant' not in self.stored_apps.columns) or \
           (self.stored_apps.relevant.count() < len(self.stored_apps)*0.5):
            print("Relevant column is missing or unpopulated... recreating")
            self.stored_apps['relevant'] = (self.stored_apps['ml_score'] > 0.4)\
                .apply(lambda x: 'y' if x else 'n')

    def setup(self):
        """If the device needs some setup to work."""
        pass

    def catch_err(self, p, cmd='', msg=''):
        p.wait(10)
        if p.returncode != 0:
            m = ("[{}]: Error running {!r}. Error ({}): {}\n{}".format(
                self.device_type, cmd, p.returncode, p.stderr.read(), msg
            ))
            config.add_to_error(m)
            return -1
        else:
            return p.stdout.read().decode()

    def devices(self):
        raise Exception("Not implemented")

    def get_apps(self, serialno):
        pass

    def dump_file_name(self, serial, fsuffix='json'):
        return os.path.join(config.DUMP_DIR, '{}_{}.{}'.format(
            serial, self.device_type, fsuffix))

    def app_details(self, serialno, appid):
        try:
            d = self.stored_apps.loc[appid].copy()
            if not isinstance(d.get('permissions', ''), list):
                d['permissions'] = d.get('permissions', '').split(', ')
            if 'descriptionHTML' not in d:
                d['descriptionHTML'] = d['description']
            dfname = self.dump_file_name(serialno)
            if self.device_type == 'ios':
                ddump = parse_dump.IosDump(dfname)
            else:
                ddump = parse_dump.AndroidDump(dfname)
            d['info'] = ddump.info(appid)
            # p = self.run_command(
            #     'bash scripts/android_scan.sh info {ser} {appid}',
            #     ser=serialno, appid=appid
            # ); p.wait()
            # d['info'] = p.stdout.read().decode().replace('\n', '<br/>')
            return d
        except KeyError as ex:
            print("Exception:::", ex)
            offstore_apps = pd.read_csv(config.OFFSTORE_APPS,
                                        index_col='appId')
            d = offstore_apps.loc[appid]
            d['permissions'] = ['<not recorded>' for x in range(10)]
            return d

    def find_offstore_apps(self, serialno):
        installed_apps = self.get_apps(serialno)
        offstore_apps = pd.read_csv(config.OFFSTORE_APPS, index_col='appId')
        return (offstore_apps.loc[
            list(set(installed_apps) & set(offstore_apps.index)), 'title'
        ].apply(lambda x: x.encode('ascii', errors='ignore')))

    def find_spyapps(self, serialno):
        """Finds the apps in the phone and add flags to them based on @blacklist.py
        Return the sorted dataframe
        """
        installed_apps = self.get_apps(serialno)
        # r = app_list.query('appId in @installed_apps').copy()
        r = pd.DataFrame({'appId': installed_apps}).join(self.stored_apps, on="appId", how="left", rsuffix='_r')
        r['flags'] = flag_apps(r.appId.values).values
        r['title'] = r.title.str.encode('ascii', errors='ignore').str.decode('ascii')
        # print("SpyApps:", r[r.appId.str.contains('spy')])
        a = r[['title', 'appId', 'flags']].set_index('appId')
        return a.loc[a.flags.apply(len).sort_values(ascending=False).index]

    def flag_apps(self, serialno):
        installed_apps = self.get_apps(serialno)
        app_flags = flag_apps(installed_apps)
        return app_flags

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

    def save(self, table, **kwargs):
        try:
            tab = db.get_table(table)
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
        self.serialno = None
        self.installed_apps = None
        # self.setup()

    def setup(self):
        p = self.run_command(
            '{cli} kill-server; {cli} start-server'
        )
        if p != 0:
            print("Setup failed with returncode={}. ~~ ex={!r}"
                  .format(p.returncode, p.stderr.read() + p.stdout.read()))

    def get_apps(self, serialno):
        cmd = '{cli} -s {serial} shell pm list packages -f -u | sed -e "s/.*=//" |'\
              ' sed "s/\r//g" | sort'
        s = self.catch_err(self.run_command(cmd, serial=serialno),
                           msg="App search failed", cmd=cmd)

        if not s:
            self.setup()
            return []
        else:
            installed_apps = s.split('\n')
            q = self.run_command(
                'bash scripts/android_scan.sh scan {ser}',
                ser=serialno); q.wait()
            self.installed_apps = installed_apps
            return installed_apps

    def devices(self):
        cmd = '{cli} devices | tail -n +2 | cut -f1'
        return [l.strip() for l in self.run_command(cmd)
                .stdout.read().decode('utf-8').split('\n') if l.strip()]

    def devices_info(self):
        cmd = '{cli} devices -l'
        return self.run_command(cmd).stdout.read().decode('utf-8')

    # def dump_phone(self, serialno=None):
    #     if not serialno:
    #         serialno = self.devices()[0]
    #     cmd = '{cli} -s {serial} shell dumpsys'
    #     p = self.run_command(cmd, serial=serialno)
    #     outfname = os.path.join(config.DUMP_DIR, '{}.txt.gz'.format(serialno))
    #     # if p.returncode != 0:
    #     #     print("Dump command failed")
    #     #     return
    #     with gzip.open(outfname, 'w') as f:
    #         f.write(p.stdout.read())
    #     print("Dump success! Written to={}".format(outfname))

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
        self.installed_apps = None
        self.serialno = None

    def get_apps(self, serialno):
        self.serialno = serialno
        # cmd = '{cli} -i {serial} install browse | tail -n +2 > {outf}'
        cmd = '{cli} -i {serial} -B | tail -n +3 > {outf}'
        dumpf = self.dump_file_name(serialno, 'json')
        self.catch_err(self.run_command(cmd, serial=serialno, outf=dumpf))
        print("Dumped the data into: {}".format(dumpf))
        s = parse_dump.IosDump(dumpf)
        self.installed_apps = s.installed_apps()
        return self.installed_apps

    def devices(self):
        cmd = '{cli} --detect -t1 | tail -n 1'
        self.serialno = None
        s = self.catch_err(self.run_command(cmd), cmd=cmd, msg="")
        print(s)
        return [l.strip() for l in s.split('\n') if l.strip()]

    def uninstall(self, appid, serialno):
        cmd = '{cli} -i {serial} --uninstall_only --bundle_id {appid!r}'
        s = self.catch_err(self.run_command(cmd, serial=serialno, appid=appid),
                           cmd=cmd, msg="Could not uninstall")
        return s != -1


class TestScan(AppScan):
    def __init__(self):
        super(TestScan, self).__init__('android', cli='cli')

    def get_apps(self, serialno):
        # assert serialno == 'testdevice1'
        installed_apps = open(TEST_APP_LIST, 'r').read().splitlines()
        return installed_apps

    def devices(self):
        return ["testdevice1", "testdevice2"]

    def uninstall(self, appid, serialno):
        return True


