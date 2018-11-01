#!/usr/bin/env python3

import subprocess
import pandas as pd
import config
import os
import sqlite3
from datetime import datetime
from android_permissions import all_permissions
import parse_dump
import blacklist
import datetime
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
        if self.device_type == 'ios':
            if fsuffix == 'jailbreak':
                devicedumpsdir = os.path.join(config.DUMP_DIR, \
                        '{}_{}'.format(serial, 'ios'))
                return os.path.join(devicedumpsdir, 'ios_jailbroken.log')
            elif fsuffix == 'devinfo':
                devicedumpsdir = os.path.join(config.DUMP_DIR, \
                        '{}_{}'.format(serial, 'ios'))
                return os.path.join(devicedumpsdir, 'ios_info.xml')
            else:
                devicedumpsdir = os.path.join(config.DUMP_DIR, \
                        '{}_{}'.format(serial, 'ios'))
                return os.path.join(devicedumpsdir, 'ios_apps.plist')

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
                #dfname = os.path.join(config.DUMP_DIR, serialno+"_ios")
                # FIXME: better suffix renaming scheme
                devinfo = self.dump_file_name(serialno, 'devinfo')
                ddump = parse_dump.IosDump(dfname, devinfo)
            else:
                ddump = parse_dump.AndroidDump(dfname)

            info = ddump.info(appid)

            print('BEGIN INFO')
            print(info)
            print('END INFO')
            # FIXME: sloppy iOS hack but should fix later, just add these to DF directly.
            if self.device_type == 'ios':
                d['permissions'] = [info['permissions']]
                d['title'] = [info['title']]
                #print(info['permissions'])
                del info['permissions']
            elif self.device_type == 'android':
                hf_recent, not_hf_recent, not_hf, stats = all_permissions(appid)

                #FIXME: 
                # some appopps in not_hf_recent are not included in the output.
                # maybe concat hf_recent with them?
                info['Date of Scan'] = datetime.datetime.now()
                info['Installation Date'] = stats['firstInstallTime']
                info['Last Updated'] = stats['lastUpdateTime']
                info['Last Used'] = stats['used']
                
                # TODO: what is the difference between usedScr and used? 
                # Does a background process count as used? Probably not since
                # appOps permissions have been more recent than 'used' on some scans.
                #info['Last Used Screen'] = stats['usedScr']
                info['App Version'] = stats['versionName']
                #info['App Version Code'] = stats['versionCode']

                print(d)
                print(hf_recent['label'].tolist())

                # FIXME: if Unknown, use 'permission_abbrv' instead.
                #hf_recent.apply()
                hf_recent.loc[hf_recent['label'] == 'unknown', 'label'] = hf_recent['permission_abbrv']
                
                #hf_recent['label'] = hf_recent[['label', 'timestamp']].apply(lambda x: ''.join(str(x), axis=1))
                hf_recent['label'] = hf_recent['label'].map(str) + " (last used by app: "+hf_recent['timestamp'].map(str)+")"
                d.set_value(0, 'permissions', hf_recent['label'].tolist())

                #d['recent_permissions'] = hf_recent['timestamp']
                #print(d['recent_permissions'])

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
        if self.device_type == 'ios':
            installed_apps, titles = self.get_apps(serialno, titles=True)
        else:
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
        
        if self.device_type == 'ios':
            r['title'] = titles
        else:
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

    def device_info(self, serial):
        pass

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

    def device_info(self, serial):
        cmd = '{cli} -s {serial} shell getprop ro.product.brand'
        brand = self.run_command(cmd, serial=serial).stdout.read().decode('utf-8')

        cmd = '{cli} -s {serial} shell getprop ro.product.model'
        model = self.run_command(cmd, serial=serial).stdout.read().decode('utf-8')

        cmd = '{cli} -s {serial} shell getprop ro.build.version.release'
        version = self.run_command(cmd, serial=serial).stdout.read().decode('utf-8')
        return brand.title()+" "+model+"(running Android "+version.strip()+")"
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
        '''
            Doesn't return all reasons by default. First match will return.
        '''
        cmd = "{cli} -s {serial} shell 'which su'"
        s = self.catch_err(self.run_command(cmd, serial=shlex.quote(serial)))
        if s == -1 or 'su: not found' in s or len(s) == 0:
            print(config.error())
            reason = "couldn't find 'su' tool on the phone."
            return (False, reason)
        else:
            reason = "found '{}' tool on the phone.".format(s.strip())
            return (True, reason)
        
        installed_apps = self.installed_apps
        if not installed_apps:
            installed_apps = self.get_apps(serial)
        
        # FIXME: load these from a private database instead.
        # from OWASP, 
        #https://sushi2k.gitbooks.io/the-owasp-mobile-security-testing-guide/content/0x05j-Testing-Resiliency-Against-Reverse-Engineering.html
        root_pkgs = ['com.noshufou.android.su','com.thirdparty.superuser',\
                'eu.chainfire.supersu', 'com.koushikdutta.superuser',\
                'com.zachspong.temprootremovejb' ,'com.ramdroid.appquarantine']
        root_pkgs_check = list(set(root_pkgs) & set(installed_apps))
        if root_pkgs_check:
            reason = "found the following app(s) on the phone: '{}'."\
                    .format(str(root_pkgs_check))
            return (True, reason)
    
class IosScan(AppScan):
    """
    Run `bash scripts/setup.sh to get libimobiledevice dependencies`
    """
    def __init__(self):
        super(IosScan, self).__init__('ios', config.MOBILEDEVICE_PATH)
        self.installed_apps = None
        self.serialno = None

    def setup(self, attempt_remount=False):
        ''' FIXME: iOS setup. '''
        if config.PLATFORM == 'linux' and attempt_remount:
            # FIXME: need to prompt system maintainer for sudo password?
            cmd = config.SCRIPT_DIR + '/ios_mount_linux.sh mount'
            #mountmsg = self.run_command(cmd).stderr.read().decode('utf-8')
            if self.catch_err(self.run_command(cmd)) == -1:
                return (False, "Couldn't detect device. See {}/ios_mount_linux.sh."\
                        .format(config.SCRIPT_DIR))
        cmd = 'idevicepair pair'
        pairmsg = self.run_command(cmd).stdout.read().decode('utf-8')
        if "No device found, is it plugged in?" in pairmsg:
            return (False, pairmsg)
        elif "Please enter the passcode on the device and retry." in pairmsg:
            return (False, "Please unlock your device and follow the trust dialog"\
                    " (you will need to enter your passcode). Then try to scan again.")
        elif "SUCCESS: Paired with device" in pairmsg:
            return (True, "Device successfully paired. Setup complete.")
        elif "said that the user denied the trust dialog." in pairmsg:
            return (False, "The trust dialog was denied. Please unplug the device"\
                    ", reconnect it, and scan again -- accept the trust dialog to proceed.")
        return (True, "Follow trust dialog on iOS device to continue.")

    def get_apps(self, serialno, titles=False):
        self.serialno = serialno
        # cmd = '{cli} -i {serial} install browse | tail -n +2 > {outf}'
        #cmd = '{cli} -i {serial} -B | tail -n +3 > {outf}'

        path = os.path.join(config.DUMP_DIR, serialno+"_ios")
        #cmd = 'ideviceinstaller -u {} -l -o xml -o list_all > {}/ios_apps.plist'.format(serialno, path)
        #print(cmd)

        #dumpf = self.dump_file_name(serialno, 'json')
        #dumpf = self.dump_file_name(serialno, 'xml')
        dumpf = path+"/ios_apps.plist"
        dumpfinfo = path+"/ios_info.xml"
        #cmd2 = "ideviceinfo -u {} -x > {}/ios_info.xml".format(serialno, path)


        print('DUMPING iOS INFO...')
        cmd = '{}/ios_dump.sh'.format(config.THISDIR)
        print('iOS INFO DUMPED.')
        #if self.catch_err(self.run_command(cmd2, serial=serialno, outf=dumpfinfo)) == -1:
        #    connected, connected_reason = self.setup()
        #    if not connected:
        #        print(connected_reason)
        #        # FIXME: error here?

        dumpres = self.catch_err(self.run_command(cmd, serial=serialno)).strip()
        if dumpres == serialno:
            print("Dumped the data into: {}".format(dumpf))
            s = parse_dump.IosDump(dumpf, dumpfinfo)
            print(s.load_file())
            self.installed_apps = s.installed_apps()
            if titles:
                titles = s.installed_apps_titles()
                return self.installed_apps, titles
        else:
            print("Couldn't connect to the device. Trying to reconnect.") 
            connected, connected_reason = self.setup()
            if not connected:
                print(connected_reason)
                # FIXME: error here?
            self.installed_apps = []
        return self.installed_apps

    def get_system_apps(self, serialno):
        dumpf = self.dump_file_name(serialno, 'plist')
        dumpfinfo = self.dump_file_name(serialno, 'devinfo')
        
        if os.path.exists(dumpf):
            s = parse_dump.IosDump(dumpf, dumpfinfo)
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

    def device_info(self, serial):
        dfname = self.dump_file_name(serial)
        devinfo = self.dump_file_name(serial, 'devinfo')
        ddump = parse_dump.IosDump(dfname, devinfo)
        device_info = ddump.device_info()
        return device_info

    def uninstall(self, serial, appid):
        #cmd = '{cli} -i {serial} --uninstall_only --bundle_id {appid!r}'
        cmd = 'ideviceinstaller -udid {} -uninstall {!r}'.format(serial, appid)
        s = self.catch_err(self.run_command(cmd, serial=serial, appid=appid),
                           cmd=cmd, msg="Could not uninstall")
        return s != -1

    def isrooted(self, serial):
        with open(os.path.join(config.DUMP_DIR,"{}_ios/ios_jailbroken.log".format(serial)),'r') as fh:
            JAILBROKEN_LOG = fh.readlines()

        # if app["Path"].split("/")[-1] in ["Cydia.app"]
        ''' Summary of jailbroken detection: checks for commonly installed jailbreak apps,
        tries to mount root filesystem (AFC2, by default on iOS 7 and lower,
        tries to SSH into the phone (FIXME). iproxy 2222 22 `idevice_id -l` says
        "waiting for connection" perpertually if not work. says "accepted connection" on next line if it does.
        https://twitter.com/bellis1000/status/807527492810665984?lang=en
        # add to jailbroken log
        # FIXME: load from private data blacklist. More to be added.
        '''
        # FIXME: NEED to apply first to df. self.installed_apps not sufficient. dotapps.append(app["Path"].split("/")[-1])
        reasons = []
        for app in ["Cydia.app", "blackra1n.app", 
                "FakeCarrier.app", "Icy.app", "IntelliScreen.app", 
                "MxTube.app", "RockApp.app", "SBSettings.app", 
                "WinterBoard.app"]:
            if app in self.installed_apps:
                return (True, "{} was found on the device.".format(app))
        reasons.append("Did not find popular jailbreak apps installed.")
        ''' check for jailbroken status after attempts logged by ios_dump.sh '''

        if "Your device needs to be jailbroken and have the AFC2 service installed.\n" in JAILBROKEN_LOG:
            reasons.append("Filesystem is not rooted. *Highly unlikely* to be jailbroken.")
            print(reasons)
            return (False, reasons)
        else:
            reason = "Filesystem has been rooted. This device is jailbroken."
            print(reason)
            return (True, reason)
        return (False, reasons)

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


