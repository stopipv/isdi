#!/usr/bin/env python3

import subprocess
import pandas as pd
import config
import os
import sqlite3
from datetime import datetime
import parse_dump
import blacklist
import re
import shlex


class AppScan(object):
    device_type = ''
    # app_info = pd.read_csv(config.APP_INFO_FILE, index_col='appId')
    # app_info_conn = dataset.connect(config.APP_INFO_SQLITE_FILE)
    app_info_conn = sqlite3.connect(
        config.APP_INFO_SQLITE_FILE.replace('sqlite:///', ''),
        check_same_thread=False
    )
    
    def __init__(self, dev_type, cli):
        assert dev_type in config.DEV_SUPPRTED, \
            "dev={!r} is not supported yet. Allowed={}"\
                .format(dev_type, config.DEV_SUPPRTED)
        self.device_type = dev_type
        self.cli = cli   # The cli of the device, e.g., adb or mobiledevice

    def setup(self):
        """If the device needs some setup to work."""
        pass

    def catch_err(self, p, cmd='', msg=''):
        """TODO: Therer are two different types. homogenize them"""
        try:
            p.wait(10)
            print("Returncode: ", p.returncode)
            if p.returncode != 0:
                m = ("[{}]: Error running {!r}. Error ({}): {}\n{}".format(
                    self.device_type, cmd, p.returncode, p.stderr.read(), msg
                ))
                config.add_to_error(m)
                return -1
            else:
                s = p.stdout.read().decode()
                if len(s) <= 100 and re.search('(?i)(fail|error)', s):
                    config.add_to_error(s)
                    return -1
                else:
                    return s
        except Exception as ex:
            config.add_to_error(ex)
            print("Exception>>>", ex)
            return -1

    def devices(self):
        raise Exception("Not implemented")

    def get_apps(self, serialno):
        pass

    def get_offstore_apps(self, serialno):
        return []

    def dump_file_name(self, serial, fsuffix='json'):
        return os.path.join(config.DUMP_DIR, '{}_{}.{}'.format(
            serial, self.device_type, fsuffix))

    def app_details(self, serialno, appid):
        try:
            d = pd.read_sql('select * from apps where appid=?', 
                            self.app_info_conn,
                            params=(appid,))
            if not isinstance(d.get('permissions', ''), list):
                d['permissions'] = d.get('permissions', pd.Series([]))
                d['permissions'] = d['permissions'].fillna('').str.split(', ')
            if 'descriptionHTML' not in d:
                d['descriptionHTML'] = d['description']
            dfname = self.dump_file_name(serialno)
            if self.device_type == 'ios':
                #ddump = parse_dump.IosDump(dfname)
                dfname = os.path.join(config.DUMP_DIR, serialno+"_ios")
                ddump = parse_dump.IosDump(dfname)
            else:
                ddump = parse_dump.AndroidDump(dfname)
            info = ddump.info(appid)
            if self.device_type == 'ios':
                d['permissions'] = [info['permissions']]
                d['title'] = [info['title']]
                #print(info['permissions'])
                del info['permissions']
            print("AppInfo: ", info, appid, dfname, ddump)
            # p = self.run_command(
            #     'bash scripts/android_scan.sh info {ser} {appid}',
            #     ser=serialno, appid=appid
            # ); p.wait()
            # d['info'] = p.stdout.read().decode().replace('\n', '<br/>')
            return d.fillna(''), info
        except KeyError as ex:
            print("Exception:::", ex)
            return pd.DataFrame([]), dict()

    def find_spyapps(self, serialno):
        """Finds the apps in the phone and add flags to them based on @blacklist.py
        Return the sorted dataframe
        """
        installed_apps = self.get_apps(serialno)
        # r = pd.read_sql('select appid, title from apps where appid in (?{})'.format(
        #     ', ?'*(len(installed_apps)-1)
        #     ), self.app_info_conn, params=(installed_apps,))
        # r.rename({'appid': 'appId'}, axis='columns', copy=False, inplace=True)
        r = blacklist.app_title_and_flag(
            pd.DataFrame({'appId': installed_apps}),
            offstore_apps=self.get_offstore_apps(serialno),
            system_apps=self.get_system_apps(serialno)
        )
        r['class_'] = r.flags.apply(blacklist.assign_class)
        r['score'] = r.flags.apply(blacklist.score)
        r['title'] = r.title.str.encode('ascii', errors='ignore').str.decode('ascii')
        r['html_flags'] = r.flags.apply(blacklist.flag_str)
        r.sort_values(by=['score', 'appId'], ascending=[False, True], inplace=True, na_position='last')
        r.set_index('appId', inplace=True)
        return r[['title', 'flags', 'score', 'class_', 'html_flags']]

    def flag_apps(self, serialno):
        installed_apps = self.get_apps(serialno)
        app_flags = blacklist.flag_apps(installed_apps)
        return app_flags

    def uninstall(self, serial, appid):
        pass

    def run_command(self, cmd, **kwargs):
        _cmd = cmd.format(
            cli=self.cli, **kwargs
        )
        print(_cmd)
        if kwargs.get('nowait', False) or kwargs.get('NOWAIT', False):
            pid = subprocess.Popen(
                _cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            ).pid
            return pid
        else:
            p = subprocess.Popen(
                _cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            return p

    def save(self, table, **kwargs):
        try:
            tab = db.get_table(table)
            kwargs['device'] = kwargs.get('device', self.device_type)
            tab.insert(kwargs)
            db.commit()
            return True
        except Exception as ex:
            print(ex)
            return False

    def isrooted(self, serial):
        pass


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

    def _get_apps_(self, serialno, flag):
        cmd = "{cli} -s {serial} shell pm list packages {flag} | sed 's/^package://g' | sort"
        s = self.catch_err(self.run_command(cmd, serial=serialno, flag=flag),
                           msg="App search failed", cmd=cmd)
        if not s:
            self.setup()
            return []
        else:
            installed_apps = [x for x in s.splitlines() if x]
            return installed_apps

    def get_apps(self, serialno):
        installed_apps = self._get_apps_(serialno, '-u')
        if installed_apps:
            q = self.run_command(
                'bash scripts/android_scan.sh scan {ser}',
                ser=serialno, nowait=True);
            self.installed_apps = installed_apps
        return installed_apps

    def get_system_apps(self, serialno):
        apps = self._get_apps_(serialno, '-s')
        return apps

    def get_offstore_apps(self, serialno):
        offstore = []
        for l in self._get_apps_(serialno, '-i -u -3'):
            l = l.split()
            if len(l) == 2:
                apps, t = l
                installer = t.replace('installer=', '')
                if installer not in config.APPROVED_INSTALLERS:
                    offstore.append(apps)
            else:
                print(">>>>>> ERROR: {}".format(l))
        return offstore

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

    def uninstall(self, serial, appid):
        cmd = '{cli} -s {serial} uninstall {appid!r}'
        s = self.catch_err(self.run_command(cmd, serial=shlex.quote(serial),
                                                appid=shlex.quote(appid)),
                           cmd=cmd, msg="Could not uninstall")
        return s != -1

    def isrooted(self, serial):
        cmd = '{cli} -s {serial} shell su'
        s = self.catch_err(self.run_command(cmd, serial=shlex.quote(serial)))
        if s == -1 or 'su: not found' in s:
            print(config.error())
            reason = "couldn't find 'su' tool on the phone."
            return (False, reason)
        else:
            reason = "found 'su' tool on the phone."
            return (True, reason)


    
class IosScan(AppScan):
    """
    Run `bash scripts/setup.sh to get libimobiledevice dependencies`
    """
    def __init__(self):
        super(IosScan, self).__init__('ios', config.MOBILEDEVICE_PATH)
        self.installed_apps = None
        self.serialno = None

    def setup(self):
        ''' FIXME: iOS setup. '''
        if config.PLATFORM == 'linux':
            cmd = config.SCRIPT_DIR + '/ios_mount_linux.sh mount'
            #mountmsg = self.run_command(cmd).stderr.read().decode('utf-8')
            if self.catch_err(self.run_command(cmd)) == -1:
                return (False, "Couldn't detect device. See ios_mount_linux.sh.")
        cmd = 'idevicepair pair'
        pairmsg = self.run_command(cmd).stdout.read().decode('utf-8')
        if "No device found, is it plugged in?" in pairmsg:
            return (False, pairmsg)
        return (True, "Follow trust dialog on iOS deivce to continue.")

    def get_apps(self, serialno):
        self.serialno = serialno
        # cmd = '{cli} -i {serial} install browse | tail -n +2 > {outf}'
        #cmd = '{cli} -i {serial} -B | tail -n +3 > {outf}'

        path = os.path.join(config.DUMP_DIR, serialno+"_ios")
        cmd = 'ideviceinstaller -u {serial} -l -o xml -o list_all > {path}/ios_apps.plist'

        #dumpf = self.dump_file_name(serialno, 'json')
        #dumpf = self.dump_file_name(serialno, 'xml')
        dumpf = path+"/ios_apps.plist"

        if self.catch_err(self.run_command(cmd, serial=serialno, outf=dumpf)) != -1:
            print("Dumped the data into: {}".format(dumpf))
            s = parse_dump.IosDump(dumpf)
            self.installed_apps = s.installed_apps()
        else:
            connected, connected_reason = self.setup()
            if not connected:
                print(connected_reason)
                # FIXME: error here?
            self.installed_apps = []
        return self.installed_apps

    def get_system_apps(self, serialno):
        dumpf = self.dump_file_name(serialno, 'json')
        if os.path.exists(dumpf):
            s = parse_dump.IosDump(dumpf)
            return s.system_apps()
        else:
            return []

    def devices(self):
        def _is_device(x):
            """Is it looks like a serial number"""
            return re.match(r'[a-f0-9]+', x) is not None

        #cmd = '{cli} --detect -t1 | tail -n 1'
        cmd = 'idevice_id -l | tail -n 1'
        self.serialno = None
        s = self.catch_err(self.run_command(cmd), cmd=cmd, msg="")
        d = [l.strip() for l in s.split('\n')
                 if l.strip() and _is_device(l.strip())]
        print("Devices found:", d)
        return d

    def uninstall(self, serial, appid):
        #cmd = '{cli} -i {serial} --uninstall_only --bundle_id {appid!r}'
        cmd = 'ideviceinstaller -udid {serial} -uninstall {appid!r}'
        s = self.catch_err(self.run_command(cmd, serial=serial, appid=appid),
                           cmd=cmd, msg="Could not uninstall")
        return s != -1

    def isrooted(self, serial):
        with open(os.path.join(config.DUMP_DIR,"{serial}_ios/ios_jailbroken.log",'r')) as fh:
            JAILBROKEN_LOG = fh.readlines()


        # if app["Path"].split("/")[-1] in ["Cydia.app"]

        ''' check for jailbroken status after attempts logged by ios_dump.sh '''
        if "Your device needs to be jailbroken and have the AFC2 service installed.\n" in JAILBROKEN_LOG:
            reason = "Filesystem is not rooted. *Highly unlikely* to be jailbroken."
            print(reason)
            return (False, reason)
	else:
	    reason = "Filesystem has been rooted. This device is jailbroken."
            print(reason)
            return (True, reason)


class TestScan(AppScan):
    def __init__(self):
        super(TestScan, self).__init__('android', cli='cli')

    def get_apps(self, serialno):
        # assert serialno == 'testdevice1'
        installed_apps = open(config.TEST_APP_LIST, 'r').read().splitlines()
        return installed_apps

    def devices(self):
        return ["testdevice1", "testdevice2"]

    def get_system_apps(self, serialno):
        return self.get_apps(serialno)[:10]

    def get_offstore_apps(self, serialno):
        return self.get_apps(serialno)[-4:]

    def uninstall(self, serial, appid):
        return True


