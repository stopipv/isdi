#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hmac
import hashlib
import pandas as pd
import config
import os
import sqlite3
from datetime import datetime
from android_permissions import all_permissions
from runcmd import run_command, catch_err
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

    def devices(self):
        raise Exception("Not implemented")

    def get_apps(self, serialno):
        pass

    def get_offstore_apps(self, serialno):
        return []

    def dump_path(self, serial, fkind='json'):
        serial = config.hmac_serial(serial)
        if self.device_type == 'ios':
            devicedumpsdir = os.path.join(config.DUMP_DIR, \
                        '{}_{}'.format(serial, 'ios'))
            if fkind == 'Jailbroken':
                return os.path.join(devicedumpsdir, config.IOS_DUMPFILES.get('Jailbroken',''))
            elif fkind == 'Device_Info':
                return os.path.join(devicedumpsdir, config.IOS_DUMPFILES.get('Info',''))
            elif fkind == 'Apps':
                return os.path.join(devicedumpsdir, config.IOS_DUMPFILES.get('Apps',''))
            elif fkind == 'Dir':
                return devicedumpsdir
            else:
                # returns apps dumpfile if fkind isn't explicitly specified.
                return os.path.join(devicedumpsdir, config.IOS_DUMPFILES.get('Apps',''))

        return os.path.join(config.DUMP_DIR, '{}_{}.{}'.format(
            serial, self.device_type, fkind))

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
            dfname = self.dump_path(serialno)

            if self.device_type == 'ios':
                ddump = self.parse_dump
                if not ddump:
                    ddump = parse_dump.IosDump(dfname)
            else:
                ddump = parse_dump.AndroidDump(dfname)

            info = ddump.info(appid)

            print('BEGIN INFO')
            print("info={}".format(info))
            print('END INFO')
            # FIXME: sloppy iOS hack but should fix later, just add these to DF
            # directly.
            if self.device_type == 'ios':
                # TODO: add extra info about iOS? Like idevicediagnostics
                # ioregentry AppleARMPMUCharger or IOPMPowerSource or
                # AppleSmartBattery.
                d['permissions'] = pd.Series(info.get('permissions',''))
                #d['permissions'] = [info.get('permissions','')]
                d['title'] = pd.Series(info.get('title',''))
                del info['permissions']
            print("AppInfo: ", info, appid, dfname, ddump)
            return d.fillna(''), info
        except KeyError as ex:
            print("Exception:::", ex)
            return pd.DataFrame([]), dict()

    def find_spyapps(self, serialno):
        """Finds the apps in the phone and add flags to them based on @blacklist.py
        Return the sorted dataframe
        """
        installed_apps = self.get_apps(serialno)

        if len(installed_apps) <= 0:
            return pd.DataFrame(
                [],
                columns=['title', 'flags', 'score', 'class_', 'html_flags']
            )
        r = blacklist.app_title_and_flag(
            pd.DataFrame({'appId': installed_apps}),
            offstore_apps=self.get_offstore_apps(serialno),
            system_apps=self.get_system_apps(serialno)
        )
        r['title'] = r.title.fillna('')
        if self.device_type == 'android':
            td = pd.read_sql(
                'select appid as appId, title from apps where appid in (?{})'.format(
                    ', ?'*(len(installed_apps)-1)
                    ), self.app_info_conn, params=(installed_apps)).set_index('appId')
            td.index.rename('appId', inplace=True)
        elif self.device_type == 'ios':
            td = self.get_app_titles(serialno)

        r.set_index('appId', inplace=True)
        print("td=", td)
        r.loc[td.index, 'title'] = td.get('title','')
        r.reset_index(inplace=True)

        r['class_'] = r.flags.apply(blacklist.assign_class)
        r['score'] = r.flags.apply(blacklist.score)
        r['title'] = r.title.str.encode('ascii', errors='ignore')\
          .str.decode('ascii')
        r['title'] = r.title.fillna('')
        r['html_flags'] = r.flags.apply(blacklist.flag_str)
        r.sort_values(by=['score', 'appId'], ascending=[False, True],
                      inplace=True, na_position='last')
        r.set_index('appId', inplace=True)

        return r[['title', 'flags', 'score', 'class_', 'html_flags']]

    def flag_apps(self, serialno):
        installed_apps = self.get_apps(serialno)
        app_flags = blacklist.flag_apps(installed_apps)
        return app_flags

    def uninstall(self, serial, appid):
        pass

    def save(self, table, **kwargs):
        try:
            tab = db.get_table(table)
            kwargs['device'] = kwargs.get('device', self.device_type)
            tab.insert(kwargs)
            db.commit()
            return True
        except Exception as ex:
            print("Exception:", ex)
            return False

    def device_info(self, serial):
        return "Test Phone", {}


    def isrooted(self, serial):
        return (False, [])


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
        p = run_command(
            '{cli} kill-server; {cli} start-server'
        )
        if p != 0:
            print("Setup failed with returncode={}. ~~ ex={!r}"
                  .format(p.returncode, p.stderr.read() + p.stdout.read()))

    def _get_apps_(self, serialno, flag):
        cmd = "{cli} -s {serial} shell pm list packages {flag} | sed 's/^package://g' | sort"
        s = catch_err(run_command(cmd, serial=serialno, flag=flag),
                           msg="App search failed", cmd=cmd)
        if not s:
            self.setup()
            return []
        else:
            installed_apps = [x for x in s.splitlines() if x]
            return installed_apps

    def get_apps(self, serialno):
        installed_apps = self._get_apps_(serialno, '-u')
        hmac_serial = config.hmac_serial(serialno)
        if installed_apps:
            q = run_command(
                'bash scripts/android_scan.sh scan {ser} {hmac_serial}',
                ser=serialno, hmac_serial=hmac_serial, nowait=True)
            self.installed_apps = installed_apps
        return installed_apps

    def get_system_apps(self, serialno):
        apps = self._get_apps_(serialno, '-s')
        return apps

    def get_offstore_apps(self, serialno):
        offstore = []
        rooted, reason = self.isrooted(serialno)
        approved = config.APPROVED_INSTALLERS
        if not rooted:
            for l in self._get_apps_(serialno, '-i -u -s'):
                l = l.split()
                if len(l) == 2:
                    apps, t = l
                    installer = t.replace('installer=', '')
                    if installer not in approved and installer != 'null':
                        # if system is rooted, won't make any difference spoofing wise
                        approved.add(installer)
        print(approved)
        for l in self._get_apps_(serialno, '-i -u -3'):
            l = l.split()
            if len(l) == 2:
                apps, t = l
                installer = t.replace('installer=', '')
                if installer not in approved:
                    offstore.append(apps)
            else:
                print(">>>>>> ERROR: {}".format(l))
        return offstore

    def devices(self):
        # FIXME: check for errors related to err in runcmd.py.
        #cmd = '{cli} devices | tail -n +2 | cut -f2'
        #runcmd = catch_err(run_command(cmd), cmd=cmd).strip()
        #cmd = '{cli} kill-server; {cli} start-server'
        #s = catch_err(run_command(cmd), time=30, msg="ADB connection failed", cmd=cmd)
        cmd = '{cli} devices | tail -n +2'
        runcmd = catch_err(run_command(cmd), cmd=cmd).strip().split('\n')
        conn_devices = []
        for rc in runcmd:
            d = rc.split()
            if len(d) != 2: continue
            device, state = rc.split()
            device = device.strip()
            if state.strip() == 'device':
                 conn_devices.append(device)
        return conn_devices

    def devices_info(self):
        cmd = '{cli} devices -l'
        return run_command(cmd).stdout.read().decode('utf-8')

    def device_info(self, serial):
        m = {}
        cmd = '{cli} -s {serial} shell getprop ro.product.brand'
        m['brand'] = run_command(cmd, serial=serial).stdout.read().decode('utf-8').title()

        cmd = '{cli} -s {serial} shell getprop ro.product.model'
        m['model'] = run_command(cmd, serial=serial).stdout.read().decode('utf-8')

        cmd = '{cli} -s {serial} shell getprop ro.build.version.release'
        m['version'] = run_command(cmd, serial=serial).stdout.read().decode('utf-8').strip()

        cmd = '{cli} -s {serial} shell dumpsys batterystats | grep -i "Start clock time:" | head -n1'
        runcmd = catch_err(run_command(cmd, serial=serial), cmd=cmd)
        #m['last_full_charge'] = datetime.strptime(runcmd.split(':')[1].strip(), '%Y-%m-%d-%H-%M-%S')
        m['last_full_charge'] = datetime.now()
        return "{brand} {model} (running Android {version})".format(**m), m

    # def dump_phone(self, serialno=None):
    #     if not serialno:
    #         serialno = self.devices()[0]
    #     cmd = '{cli} -s {serial} shell dumpsys'
    #     p = run_command(cmd, serial=serialno)
    #     outfname = os.path.join(config.DUMP_DIR, '{}.txt.gz'.format(serialno))
    #     # if p.returncode != 0:
    #     #     print("Dump command failed")
    #     #     return
    #     with gzip.open(outfname, 'w') as f:
    #         f.write(p.stdout.read())
    #     print("Dump success! Written to={}".format(outfname))

    def uninstall(self, serial, appid):
        cmd = '{cli} uninstall {appid!r}'
        s = catch_err(run_command(cmd,
                                  appid=shlex.quote(appid)),
                      cmd=cmd, msg="Could not uninstall")
        return s != -1

    def app_details(self, serialno, appid):
        d, info = super(AndroidScan, self).app_details(serialno, appid)
        # part that requires android to be connected / store this somehow.
        hf_recent, not_hf_recent, not_hf, stats = all_permissions(
            self.dump_path(serialno), appid
        )

        # FIXME: some appopps in not_hf_recent are not included in the
        # output.  maybe concat hf_recent with them?
        info['Date of Scan'] = datetime.now().strftime(config.DATE_STR)
        info['Installation Date'] = stats.get('firstInstallTime', '')
        info['Last Updated'] = stats.get('lastUpdateTime', '')
        # info['Last Used'] = stats['used']

        # TODO: what is the difference between usedScr and used?  Does a
        # background process count as used? Probably not since appOps
        # permissions have been more recent than 'used' on some scans.
        # info['Last Used Screen'] = stats['usedScr']
        info['App Version'] = stats.get('versionName', '')
        # info['App Version Code'] = stats['versionCode']

        # FIXME: if Unknown, use 'permission_abbrv' instead.
        hf_recent.loc[hf_recent['label']=='unknown', 'label'] = hf_recent.get('permission_abbrv','')

        # hf_recent['label'] = hf_recent[['label',
        # 'timestamp']].apply(lambda x: ''.join(str(x), axis=1))

        if len(hf_recent.get('label','')) > 0:
            hf_recent['label'] = hf_recent.apply(
                lambda x: "{} (last used: {})".format(
                    x['label'], 'never' if 'unknown' in x['timestamp'].lower() else x['timestamp']),
                axis=1
            )

        print("App info dict:", d)
        print("hf_recent['label']=", hf_recent['label'].tolist())

        #hf_recent['label'] = hf_recent['label'].map(str) + " (last used by app: "+\
        #        (hf_recent['timestamp'].map(str) if isinstance(hf_recent['timestamp'], datetime) else 'nooo') +")"

        #print(~hf_recent['timestamp'].str.contains('unknown'))
        d.set_value(0, 'permissions', hf_recent['label'].tolist())

        #d['recent_permissions'] = hf_recent['timestamp']
        #print(d['recent_permissions'])
        return d, info

    def isrooted(self, serial):
        '''
            Doesn't return all reasons by default. First match will return.
        '''
        cmd = "{cli} -s {serial} shell 'command -v su'"
        s = catch_err(run_command(cmd, serial=shlex.quote(serial)))
        if s == -1 or 'not found' in s or len(s) == 0:
            print(config.error())
            reason = "couldn't find 'su' tool on the phone."
            return (False, reason)
        else:
            reason = "found '{}' tool on the phone.".format(s.strip())
            return (True, reason)
        
        installed_apps = self.installed_apps
        if not installed_apps:
            installed_apps = self.get_apps(serial)
        
        # FIXME: load these from a private database instead.  from OWASP,
        # https://sushi2k.gitbooks.io/the-owasp-mobile-security-testing-guide/content/0x05j-Testing-Resiliency-Against-Reverse-Engineering.html
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
        super(IosScan, self).__init__('ios', cli=config.LIBIMOBILEDEVICE_PATH)
        self.installed_apps = None
        self.serialno = None
        self.parse_dump = None

    def setup(self, attempt_remount=False):
        ''' FIXME: iOS setup. '''
        if config.PLATFORM == 'linux' and attempt_remount:
            # should show GUI prompt for password. sudo apt install policykit-1 if not there.
            cmd = "pkexec '"+config.SCRIPT_DIR + "/ios_mount_linux.sh' mount"
            #mountmsg = run_command(cmd).stderr.read().decode('utf-8')
            if catch_err(run_command(cmd)) == -1:
                return (False, "Couldn't detect device. See {}/ios_mount_linux.sh."\
                        .format(config.SCRIPT_DIR))
        cmd = '{}idevicepair pair'.format(self.cli)
        pairmsg = run_command(cmd).stdout.read().decode('utf-8')
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

    # TODO: This might send titles out of order. Fix this to send both appid and
    # titles.
    def get_app_titles(self, serialno):
        if not self.parse_dump:
            self._dump_phone(serialno)
        return self.parse_dump.installed_apps_titles()

    def get_apps(self, serialno):
        self.serialno = serialno
        dumped = self._dump_phone(self.serialno)
        if dumped:
            # print(self.parse_dump.load_file())
            if not self.parse_dump:
                print("Couldn't connect to the device. Trying to reconnect. Here.")
                connected, connected_reason = self.setup()
                if not connected:
                    print(connected_reason)
                    # FIXME: error here?
                self.installed_apps = []
            else:
                self.installed_apps = self.parse_dump.installed_apps()
        else:
            print("Couldn't connect to the device. Trying to reconnect. Over here.")
            connected, connected_reason = self.setup()
            if not connected:
                print(connected_reason)
                # FIXME: error here?
            self.installed_apps = []
        print('iOS INFO DUMPED.')
        return self.installed_apps

    def get_system_apps(self, serialno):
        if self.parse_dump:
            return self.parse_dump.system_apps()
        else:
            return []

    def devices(self):
        def _is_device(x):
            """Is it looks like a serial number"""
            return re.match(r'[a-f0-9]+', x) is not None

        #cmd = '{cli} --detect -t1 | tail -n 1'
        cmd = '{}idevice_id -l | tail -n 1'.format(self.cli)
        self.serialno = None
        s = catch_err(run_command(cmd), cmd=cmd, msg="")
        d = [l.strip() for l in s.split('\n')
                 if l.strip() and _is_device(l.strip())]
        print("Devices found:", d)
        return d

    def device_info(self, serial):
        dumped = self._dump_phone(serial)
        if dumped:
            device_info_print, device_info_map = self.parse_dump.device_info()
            return (device_info_print, device_info_map)
        else:
            return ("", {})


    def _dump_phone(self, serial):
        print('DUMPING iOS INFO...')
        # FIXME: pathlib migration at some point
        hmac_serial = config.hmac_serial(serial)
        cmd = "'{}/ios_dump.sh' {} {Apps} {Info} {Jailbroken}"\
            .format(config.SCRIPT_DIR, hmac_serial, **config.IOS_DUMPFILES)
        print(cmd)
        path = self.dump_path(serial, fkind='Dir')
        # dumped = catch_err(run_command(cmd)).strip()
        dumpf = os.path.join(path, config.IOS_DUMPFILES['Apps'])
        dumpfinfo = os.path.join(path, config.IOS_DUMPFILES['Info'])

        dumped = catch_err(run_command(cmd)).strip()
        print('iOS INFO DUMPED.')
        if dumped == serial or True:
            print("Dumped the data into: {}".format(dumpf))
            self.parse_dump = parse_dump.IosDump(dumpf, finfo=dumpfinfo)
            return True
        else:
            print("Couldn't connect to the device. Trying to reconnect. This way.")
            #connected, connected_reason = self.setup()
            #if not connected:
            #    print(connected_reason)
            return False
                # FIXME: error here?



    def uninstall(self, serial, appid):
        #cmd = '{cli} -i {serial} --uninstall_only --bundle_id {appid!r}'
        #cmd = 'ideviceinstaller --udid {} --uninstall {appid!r}'.format(serial, appid)
        cmd = '{}ideviceinstaller --uninstall {appid!r}'.format(self.cli)
        s = catch_err(run_command(cmd, appid=appid),
                           cmd=cmd, msg="Could not uninstall")
        return s != -1

    def isrooted(self, serial):
        with open(self.dump_path(serial, 'Jailbroken'),'r') as fh:
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
                "WinterBoard.app", "3uTools.app", "Absinthe.app", 
                "backr00m.app", "blackra1n.app", "Corona.app", 
                "doubleH3lix.app", "Electra.app", "EtasonJB.app", 
                "evasi0n.app", "evasi0n7.app", "G0blin.app", "Geeksn0w.app", 
                "greenpois0n.app", "h3lix.app", "Home Depot.app", "ipwndfu.app", 
                "JailbreakMe.app", "LiberiOS.app", "LiberTV.app", "limera1n.app", 
                "Meridian.app", "p0sixspwn.app", "Pangu.app", "Pangu8.app", "Pangu9.app", 
                "Phœnix.app", "PPJailbreak.app", "purplera1n.app", "PwnageTool.app", 
                "redsn0w.app", "RockyRacoon.app","Rocky Racoon.app", "Saïgon.app", "Seas0nPass.app", 
                "sn0wbreeze.app", "Spirit.app", "TaiG.app", "unthredera1n.app", "yalu.app"]:
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


