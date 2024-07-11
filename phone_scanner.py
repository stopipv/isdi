#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import hmac
import os
import re
import shlex
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

import pandas as pd

import blocklist
import config
import parse_dump
from android_permissions import all_permissions
from runcmd import catch_err, run_command


class AppScan(object):
    device_type = ''
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

    def get_apps(self, serialno: str, from_device: bool) -> list:
        pass

    def get_offstore_apps(self, serialno):
        return []

    def dump_path(self, serial, fkind='json'):
        hmac_serial = config.hmac_serial(serial)
        if self.device_type == 'ios':
            devicedumpsdir = os.path.join(config.DUMP_DIR, \
                        '{}_{}'.format(hmac_serial, 'ios'))
            if fkind == 'Jailbroken-FS':
                return os.path.join(devicedumpsdir, config.IOS_DUMPFILES.get('Jailbroken-FS',''))
            elif fkind == 'Jailbroken-SSH':
                return os.path.join(devicedumpsdir, config.IOS_DUMPFILES.get('Jailbroken-SSH',''))
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
            hmac_serial, self.device_type, fkind))

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

            print('BEGIN APP INFO')
            print("info={}".format(info))
            print('END APP INFO')
            # FIXME: sloppy iOS hack but should fix later, just add these to DF
            # directly.
            if self.device_type == 'ios':
                # TODO: add extra info about iOS? Like idevicediagnostics
                # ioregentry AppleARMPMUCharger or IOPMPowerSource or
                # AppleSmartBattery.
                d['permissions'] = pd.Series(info.get('permissions',''))
                #d['permissions'] = [info.get('permissions','')]
                d['title'] = pd.Series(info.get('title',''))
                #del info['permissions']
            print("AppInfo: ", info, appid, dfname, ddump)
            return d.fillna(''), info
        except KeyError as ex:
            print(">>> Exception:::", ex, file=sys.stderr)
            return pd.DataFrame([]), dict()

    def find_spyapps(self, serialno, from_dump=True):
        """Finds the apps in the phone and add flags to them based on @blocklist.py
        Return the sorted dataframe
        This is the **main** function that is called from the views in web/view/scan.py
        """
        from_device = (not from_dump)
        installed_apps = self.get_apps(serialno, from_device=from_device)

        if len(installed_apps) <= 0:
            return pd.DataFrame(
                [],
                columns=['title', 'flags', 'score', 'class_', 'html_flags']
            )
        r = blocklist.app_title_and_flag(
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
        r.loc[td.index, 'title'] = td.get('title','')
        r.reset_index(inplace=True)

        r['class_'] = r['flags'].apply(blocklist.assign_class)
        r['score'] = r['flags'].apply(blocklist.score)
        r['title'] = r.title.str.encode('ascii', errors='ignore')\
          .str.decode('ascii')
        r['title'] = r.title.fillna('')
        r['html_flags'] = r['flags'].apply(blocklist.flag_str)
        r.sort_values(by=['score', 'appId'], ascending=[False, True],
                      inplace=True, na_position='last')
        r.set_index('appId', inplace=True)

        return r[['title', 'flags', 'score', 'class_', 'html_flags']]

    def flag_apps(self, serialno):
        installed_apps = self.get_apps(serialno, from_device=False)
        app_flags = blocklist.flag_apps(installed_apps)
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
            print(">> Exception:", ex, file=sys.stderr)
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
        self.dump_d = None
        # self.setup()

    def setup(self):
        p = run_command(
            '{cli} kill-server; {cli} start-server'
        )
        if p != 0:
            print(">> Setup failed with returncode={}. ~~ ex={!r}"
                  .format(p.returncode, p.stderr.read() + p.stdout.read()), file=sys.stderr)
    def _get_apps_from_device(self, serialno, flag) -> list:
        """get apps from the device"""
        cmd = "{cli} -s {serial} shell pm list packages {flag} | sed 's/^package://g' | sort"
        s = catch_err(run_command(cmd, serial=serialno, flag=flag),
                           msg="App search failed", cmd=cmd)
        if not s:
            self.setup()
            return []
        else:
            installed_apps = [x for x in s.splitlines() if x]
            return installed_apps

    def _get_apps_from_dump(self, serialno):
        hmac_serial = config.hmac_serial(serialno)
        # Try to read from the dump
        dump_file = self.dump_path(serialno)
        self.dump_d = parse_dump.AndroidDump(dump_file)
        app_and_codes = self.dump_d.apps()
        return [a for a,c in app_and_codes]

    def get_apps(self, serialno, from_device=True) -> list:
        print(f"Getting Android apps: {serialno} from_device={from_device}")
        hmac_serial = config.hmac_serial(serialno)
        if from_device:
            installed_apps = self._get_apps_from_device(serialno, '-u')
            if installed_apps:
                q = run_command(
                    'bash scripts/android_scan.sh scan {ser} {hmac_serial}',
                    ser=serialno, hmac_serial=hmac_serial, nowait=True)
        else:
            # Try loading from the dump
            installed_apps = self._get_apps_from_dump(hmac_serial)
        self.installed_apps = installed_apps
        return installed_apps

    def get_system_apps(self, serialno, from_device=False):
        if from_device:
            apps = self._get_apps_from_device(serialno, '-s')
        else:
            apps = []  ## TODO: fix this later, not sure how to get from dump
        return apps

    def get_offstore_apps(self, serialno, from_device=False):
        if not from_device:
            return []  # TODO: fix this later, not sure how to get from dump
        offstore = []
        rooted, reason = self.isrooted(serialno)
        approved = config.APPROVED_INSTALLERS
        if not rooted:
            for l in self._get_apps_from_device(serialno, '-i -u -s'):
                l = l.split()
                if len(l) == 2:
                    apps, t = l
                    installer = t.replace('installer=', '')
                    if installer not in approved and installer != 'null':
                        # if system is rooted, won't make any difference spoofing wise
                        approved.add(installer)
        print(f"Approved Installers:{approved}")
        for l in self._get_apps_from_device(serialno, '-i -u -3'):
            l = l.split()
            if len(l) == 2:
                apps, t = l
                installer = t.replace('installer=', '')
                if installer not in approved:
                    offstore.append(apps)
            else:
                print(">>>>>> ERROR: {}".format(l), file=sys.stderr)
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

    # def devices_info(self):
    #     cmd = '{cli} devices -l'
    #     return run_command(cmd).stdout.read().decode('utf-8')

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
        hf_recent, non_hf_recent, non_hf, stats = all_permissions(
            self.dump_path(serialno), appid
        )
        # print(f"Permissions:\n"\
        #       f"hf_recent=\n{hf_recent}\n"\
        #       f"non_hf_recent=\n{non_hf_recent}\n"\
        #       f"no_hf=\n{non_hf}\n"\
        #       f"stats=\n{stats}\n")

        # FIXME: some appopps in non_hf_recent are not included in the
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

        # print("hf_recent['label']=", hf_recent['label'].tolist())
        #print(~hf_recent['timestamp'].str.contains('unknown'))
        d.at[0, 'permissions'] = hf_recent['label'].tolist()
        non_hf_recent.drop('appId', axis=1, inplace=True)
        d.at[0, 'non_hf_permissions_html'] = non_hf_recent.to_html()

        print("App info dict:", d)

        #hf_recent['label'] = hf_recent['label'].map(str) + " (last used by app: "+\
        #        (hf_recent['timestamp'].map(str) if isinstance(hf_recent['timestamp'], datetime) else 'nooo') +")"
        #d['recent_permissions'] = hf_recent['timestamp']
        #print(d['recent_permissions'])
        return d, info

    def isrooted(self, serial):
        '''
            Doesn't return all reasons by default. First match will return.
            TODO: make consistent with iOS isrooted, which returns all reasons discovered.
        '''
        cmd = "{cli} -s {serial} shell 'command -v su'"
        s = catch_err(run_command(cmd, serial=shlex.quote(serial)))
        if not s or s == -1 or 'not found' in s or len(s) == 0 or (s == "[android]: Error running ''. Error (1):"):
            print(config.error())
            reason = "couldn't find 'su' tool on the phone."
            return (False, reason)
        else:
            reason = "found '{}' tool on the phone. Verify whether this is a su binary.".format(s.strip())
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

    def get_apps(self, serialno: str, from_device: bool) -> list:
        """iOS always read everything from dump, so nothing to change."""
        self.serialno = serialno
        if from_device:
            if not self._dump_phone(serialno):
                print("Failed to dump the phone. Check error on the terminal")
                return []
        self._load_dump(serialno)
        self.installed_apps = self.parse_dump.installed_apps()
        print('iOS INFO DUMPED.')
        return self.installed_apps

    def get_system_apps(self, serialno) -> list:
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
        self._load_dump(serial)
        if dumped:
            device_info_print, device_info_map = self.parse_dump.device_info()
            return (device_info_print, device_info_map)
        else:
            return ("", {})

    def _load_dump(self, serial) -> parse_dump.IosDump:
        hmac_serial = config.hmac_serial(serial)
        path = self.dump_path(serial, fkind='Dir')
        # dumped = catch_err(run_command(cmd)).strip()
        dumpf = os.path.join(path, config.IOS_DUMPFILES['Apps'])
        dumpfinfo = os.path.join(path, config.IOS_DUMPFILES['Info'])
        self.parse_dump = parse_dump.IosDump(dumpf, finfo=dumpfinfo)
        return self.parse_dump

    def _dump_phone(self, serial: str) -> bool:
        print('DUMPING iOS INFO...')
        connected, connected_reason = self.setup()
        if not connected:
            print("Couldn't connect to the device. Trying to reconnect. Over here.")
            print(connected_reason)
            return False
        hmac_serial = config.hmac_serial(serial)
        cmd = "'{}/ios_dump.sh' {} {Apps} {Info} {Jailbroken-FS} {Jailbroken-SSH}"\
            .format(config.SCRIPT_DIR, hmac_serial, **config.IOS_DUMPFILES)
        print(cmd)
        dumped = catch_err(run_command(cmd), cmd).strip()
        if dumped:
            print('iOS DUMP RESULTS for {}:'.format(hmac_serial))
            print(dumped)
            return True
        else:
            print(">> The iOS dumping failed for some reason. Check above for more information")
            return False
    def screenshot():
        cmd = "idb list-targets"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        lines = output.split('\n')
        obArray = []
        for line in lines:
            obArray.append(line.split('|'))
        deviceID = ""
        for deviceInfo in obArray:
            if deviceInfo[2] == " Booted ":
                deviceID = deviceInfo[1]
        cmd2 = "idb connect " + deviceID
        process = subprocess.Popen(cmd2.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        date = os.system("date")
        fileDestination = "./phone_dumps/"+date+"Video.mp4"
        cmd3 = " idb record-video --udid" + deviceID + " " + fileDestination
        process = subprocess.Popen(cmd3.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        os.system("cd ./phone_dumps/")
        os.system("ffmpeg -i "+date+"Video.mp4 -frames:v 1 "+date+"Pic.jpg")
    def uninstall(self, serial, appid):
        #cmd = '{cli} -i {serial} --uninstall_only --bundle_id {appid!r}'
        #cmd = 'ideviceinstaller --udid {} --uninstall {appid!r}'.format(serial, appid)
        cmd = f'{self.cli}ideviceinstaller --uninstall {appid!r}'
        s = catch_err(run_command(cmd, appid=appid),
                           cmd=cmd, msg="Could not uninstall")
        return s != -1

    def isrooted(self, serial):
        # dict with 'True' and 'False' mapping to a list of reasons for root/no root
        rooted = defaultdict(list)
        # TODO This should be removed once the check is fixed
        rooted['False'].append("Jailbreak and root checks are currently "
                               "disabled")
        return (False, rooted['False'])
        try:
            with open(self.dump_path(serial, 'Jailbroken-FS'),'r') as fh:
                JAILBROKEN_LOG = fh.readlines()
            if "Your device needs to be jailbroken and have the AFC2 service installed.\n" in JAILBROKEN_LOG:
                rooted['False'].append("Filesystem is not rooted. *Highly unlikely* to be jailbroken.")
            elif 'No such file or directory' in JAILBROKEN_LOG:
                rooted['False'].append("Unable to check device.")
            else:
                rooted['True'].append("Filesystem *might* be rooted. Conduct additional checks.")
        except FileNotFoundError as e:
            print("Couldn't find Jailbroken FS check log.")
            # TODO: trigger error message? like 
            # TODO: show a try again, maybe it's not plugged in properly. still not working? this could be due to many many many reasons.
            #return (True, ['FS check failed, jailbreak not necessarily occurring.'])

        try:
            with open(self.dump_path(serial, 'Jailbroken-SSH'),'r') as fh:
                JAILBROKEN_SSH_LOG = fh.readlines()
            if "0\n" in JAILBROKEN_SSH_LOG:
                rooted['True'].append("SSH is enabled.")
        except FileNotFoundError as e:
            # TODO: trigger error message? like 
            # TODO: show a try again, maybe it's not plugged in properly. still not working? this could be due to many many many reasons.
            print("Couldn't find Jailbroken SSH check log.")

        # if app["Path"].split("/")[-1] in ["Cydia.app"]
        ''' Summary of jailbroken detection: checks for commonly installed jailbreak apps,
        tries to mount root filesystem (AFC2, by default on iOS 7 and lower,
        tries to SSH into the phone (FIXME). iproxy 2222 22 `idevice_id -l` says
        "waiting for connection" perpertually if not work. says "accepted connection" on next line if it does.
        https://twitter.com/bellis1000/status/807527492810665984?lang=en
        # add to jailbroken log
        # FIXME: load from private data blocklist. More to be added.
        '''
        # FIXME: NEED to apply first to df. self.installed_apps not sufficient. dotapps.append(app["Path"].split("/")[-1])

        apps_titles = self.parse_dump.installed_apps_titles()['title'].tolist()
        # TODO: convert to set check
        for app in ["Cydia", "blackra1n", "Undecimus", 
                "FakeCarrier", "Icy", "IntelliScreen", 
                "MxTube", "RockApp", "SBSettings", 
                "WinterBoard", "3uTools", "Absinthe", 
                "backr00m", "blackra1n", "Corona", 
                "doubleH3lix", "Electra", "EtasonJB", 
                "evasi0n", "evasi0n7", "G0blin", "Geeksn0w", 
                "greenpois0n", "h3lix", "Home Depot", "ipwndfu", 
                "JailbreakMe", "LiberiOS", "LiberTV", "limera1n", 
                "Meridian", "p0sixspwn", "Pangu", "Pangu8", "Pangu9", 
                "Phœnix", "PPJailbreak", "purplera1n", "PwnageTool", 
                "redsn0w", "RockyRacoon","Rocky Racoon", "Saïgon", "Seas0nPass", 
                "sn0wbreeze", "Spirit", "TaiG", "unthredera1n", "yalu"]:
            if app in apps_titles:
                rooted['True'].append("{} was found on the device.".format(app))

        # if apps check passes
        if not rooted:
            rooted['False'].append("Did not find popular jailbreak apps installed.")
            ''' check for jailbroken status after attempts logged by ios_dump.sh ''' 
        if 'True' in rooted:
            return (True, rooted['True'])
        else:
            return (False, rooted['False'])


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


