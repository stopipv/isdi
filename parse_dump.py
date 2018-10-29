import json
import re
import sys
import os
import pandas as pd
import io
import config
from functools import reduce
import operator


def count_lspaces(l):
    # print(">>", repr(l))
    return re.search(r'\S', l).start()


def get_d_at_level(d, lvl):
    for l in lvl:
        if l not in d:
            d[l] = {}
        d = d[l]
    return d

def clean_json(d):
    if not any(d.values()):
        return list(d.keys())
    else:
        for k, v in d.items():
            d[k] = clean_json(v)



def match_keys(d, keys, only_last=False):
    ret = []
    # print(keys)
    # print(keys)
    for sk in keys.split('//'):
        sk = re.compile(sk)
        for k, v in d.items():
            if sk.match(k):
                ret.append(k)
                d = d[k]
                break
    if only_last:
        return 'key=NOTFOUND' if not ret else ret[-1]
    else:
        return ret


def extract(d, lkeys):
    for k in lkeys:
        d = d.get(k, {})
    return d


def split_equalto_delim(k):
    return k.split('=', 1)

class PhoneDump(object):
    def __init__(self, dev_type, fname):
        self.device_type = dev_type
        self.fname = fname
        self.df = self.load_file()

    def load_file(self):
        raise Exception("Not Implemented")

    def info(self, appid):
        raise Exception("Not Implemented")


class AndroidDump(PhoneDump):
    def __init__(self, fname):
        txtfname = fname.rsplit('.', 1)[0] + '.txt'
        jsonfname = fname.rsplit('.', 1)[0] + '.json'
        fname = jsonfname
        if not os.path.exists(fname):
            d = self.parse_dump_file(txtfname)
            with open(jsonfname, 'w') as f:
                json.dump(d, f, indent=2)
        super(AndroidDump, self).__init__('android', fname)

    @staticmethod
    def parse_dump_file(fname):
        data = open(fname)
        d = {}
        service = ''
        lvls = ['' for _ in range(20)]  # Max 100 levels allowed
        curr_spcnt, curr_lvl = 0, 0
        for i, l in enumerate(data):
            if l.startswith('----'): continue
            if l.startswith('DUMP OF SERVICE'):
                service = l.strip().rsplit(' ', 1)[1]
                d[service] = res = {}
                curr_spcnt = [0]
                curr_lvl = 0
            else:
                if not l.strip():  # subsection ends
                    continue
                l = l.replace('\t', '     ')
                t_spcnt = count_lspaces(l)
                # print(t_spcnt, curr_spcnt, curr_lvl)
                # if t_spcnt == 1:
                #     print(repr(l))
                if t_spcnt > 0 and t_spcnt >= curr_spcnt[-1]*2:
                    curr_lvl += 1
                    curr_spcnt.append(t_spcnt)
                while curr_spcnt and curr_spcnt[-1] > 0 and t_spcnt <= curr_spcnt[-1]/2:
                    curr_lvl -= 1
                    curr_spcnt.pop()
                if curr_spcnt[-1]>0:
                    curr_spcnt[-1] = t_spcnt
                assert (t_spcnt != 0) or (curr_lvl == 0), \
                        "t_spc: {} <--> curr_lvl: {}\n{}".format(t_spcnt, curr_lvl, l)
                # print(lvls[:curr_lvl], curr_lvl, curr_spcnt)
                curr = get_d_at_level(res, lvls[:curr_lvl])
                k = l.strip().rstrip(':')
                lvls[curr_lvl] = k   # '{} --> {}'.format(curr_lvl, k)
                curr[lvls[curr_lvl]] = {}
        return d

    def load_file(self):
        fname = self.fname
        json_fname = fname.rsplit('.', 1)[0] + '.json'
        if os.path.exists(json_fname):
            with open(json_fname, 'r') as f:
                try:
                    d = json.load(f)
                except Exception as ex:
                    print(ex)
                    return {}
        else:
            with open(json_fname, 'w') as f:
                d = self.parse_dump_file(fname)
                json.dump(d, f, indent=2)
        return d

    @staticmethod
    def get_data_usage(d, process_uid):
        net_stats = pd.read_csv(io.StringIO(
            '\n'.join(d['net_stats'].keys())
        ))
        d = net_stats.query('uid_tag_int == "{}"'.format(process_uid))[
            ['uid_tag_int', 'cnt_set', 'rx_bytes', 'tx_bytes']]
        def s(c):
            return (d.query('cnt_set == {}'.format(c)).eval('rx_bytes+tx_bytes').sum()
                    /(1024*1024))
        return {
            "foreground": "{:.2f} MB".format(s(1)),
            "background": "{:.2f} MB".format(s(0))
        }

    @staticmethod
    def get_battery_stat(d, uidu):
        b = (match_keys(
            d, "batterystats//Statistics since last charge//Estimated power use .*"
            "//^Uid {}:.*".format(uidu))
        )[-1].split(':')
        if len(b) > 1:
            b = b[1]
        else:
            b = "Not known"
        return b

    def info(self, appid):
        d = self.df
        if not d:
            return {}
        package = extract(
            d,
            match_keys(d, '^package$//^Packages//^Package \[{}\].*'.format(appid))
        )
        res = dict(
            split_equalto_delim(match_keys(package, v, only_last=True))
            for v in ['userId', 'firstInstallTime', 'lastUpdateTime']
        )
        if 'userId' not in res:
            print("UserID not found in res={}".format(res))
            return {}
        process_uid = res['userId']
        del res['userId']
        memory = match_keys(d, 'meminfo//Total PSS by process//.*: {}.*'.format(appid))
        uidu_match = match_keys(d, 'procstats//CURRENT STATS//\* {} / .*'.format(appid))
        if uidu_match:
            uidu = uidu_match[-1].split(' / ')
        else:
            uidu = "Not Found"
        if len(uidu) > 1:
            uidu = uidu[1]
        else:
            uidu = uidu[0]
        res['data_usage'] = self.get_data_usage(d, process_uid)
        res['battery (mAh)'] = self.get_battery_stat(d, uidu)
        print('RESULTS')
        print(res)
        print('END RESULTS')
        return res


class IosDump(PhoneDump):
    # COLS = ['ApplicationType', 'BuildMachineOSBuild', 'CFBundleDevelopmentRegion',
    #    'CFBundleDisplayName', 'CFBundleExecutable', 'CFBundleIdentifier',
    #    'CFBundleInfoDictionaryVersion', 'CFBundleName',
    #    'CFBundleNumericVersion', 'CFBundlePackageType',
    #    'CFBundleShortVersionString', 'CFBundleSupportedPlatforms',
    #    'CFBundleVersion', 'DTCompiler', 'DTPlatformBuild', 'DTPlatformName',
    #    'DTPlatformVersion', 'DTSDKBuild', 'DTSDKName', 'DTXcode',
    #    'DTXcodeBuild', 'Entitlements', 'IsDemotedApp', 'IsUpgradeable',
    #    'LSRequiresIPhoneOS', 'MinimumOSVersion', 'Path', 'SequenceNumber',
    #    'UIDeviceFamily', 'UIRequiredDeviceCapabilities',
    #    'UISupportedInterfaceOrientations']
    # INDEX = 'CFBundleIdentifier'
    def __init__(self, fplist, finfo):
        self.device_type = 'ios'
        self.fname = fplist
        self.finfo = None
        if finfo:
            self.finfo = finfo
        self.df = self.load_file()
        self.deviceinfo = self.load_deviceinfo()

        # FIXME: not efficient to load here everytime?
        # load permissions mappings and apps plist
        self.permissions_map = {}
        self.model_make_map = {}
        with open(os.path.join(config.THISDIR, 'ios_permissions.json'), 'r') as fh:
            self.permissions_map = json.load(fh)
        with open(os.path.join(config.THISDIR, 'ios_device_identifiers.json'), 'r') as fh:
            self.model_make_map = json.load(fh)

    def load_deviceinfo(self):
        from plistlib import readPlist
        return readPlist(self.finfo)

    def load_file(self):
        # d = pd.read_json(self.fname)[self.COLS].set_index(self.INDEX)
        try:
            #d = pd.read_json(self.fname).T
            #d = pd.read_json(self.fname).T

            # FIXME: somehow, get the ios_apps.plist into a dataframe.
            from plistlib import readPlist
            APPS_PLIST = readPlist(self.fname)
            print("fname is: {}".format(self.fname))
            # load into pd...
            apps_json = json.dumps(APPS_PLIST)
            d = pd.read_json(apps_json)
            
            d['appId'] = d['CFBundleIdentifier']
            #d.index.rename('appId', inplace=True)
            return d
        except Exception as ex:
            print(ex)
            print("Could not load the json file: {}".format(self.fname))

    def retrieve(self, dict_, nest):
        '''
            Navigates dictionaries like dict_[nest0][nest1][nest2]...
            gracefully.
        '''
        dict_ = dict_.to_dict() # for pandas
        try:
            return reduce(operator.getitem, nest, dict_)
        except KeyError as e:
            return ""
        except TypeError as e:
            return ""

    def check_unseen_permissions(self, permissions):
        for permission in permissions:
            if permission not in self.permissions_map:
                print('Have not seen '+str(permission)+' before. Making note of this...')
                permission_human_readable = permission.replace('kTCCService','')
                with open(os.path.join(config.THISDIR,'ios_permissions.json'), 'w') as fh:
                    self.permissions_map[permission] = permission_human_readable
                    fh.write(json.dumps(self.permissions_map))
                print('Noted.')
            #print('\t'+msg+": "+str(PERMISSIONS_MAP[permission])+"\tReason: "+app.get(permission,'system app'))

    def get_permissions(self, app):
        '''
            Returns a list of tuples (permission, developer-provided reason for permission).
            Could modify this function to include whether or not the permission can be adjusted
            in Settings.
        '''
        system_permissions = self.retrieve(app, ['Entitlements','com.apple.private.tcc.allow'])
        adjustable_system_permissions = self.retrieve(app, ['Entitlements','com.apple.private.tcc.allow.overridable'])
        third_party_permissions = list(set(app.keys()) & set(self.permissions_map))
        self.check_unseen_permissions(list(system_permissions)+list(adjustable_system_permissions))

        # (permission used, developer reason for requesting the permission)
        all_permissions = list(set(map(lambda x: \
                (self.permissions_map[x], app.get(x, default="permission granted by system")),\
                list(set(system_permissions) | \
                set(adjustable_system_permissions) | set(third_party_permissions)))))
        pii = self.retrieve(app, ['Entitlements','com.apple.private.MobileGestalt.AllowedProtectedKeys'])
        #print("\tPII: "+str(pii))
        return all_permissions
    
    def info(self, appid):
        '''
            Returns dict containing the following:
            'permission': tuple (all permissions of appid, developer
            reasons for requesting the permissions)
            'title': the human-friendly name of the app.
            'jailbroken': tuple (whether or not phone is suspected to be jailbroken, rationale)
            'phone_kind': tuple (make, OS version)
        '''
        d = self.df
        res = {}
        

             
        # determine make and version
        try:
            make = self.model_make_map[self.deviceinfo['ProductType']]
        except KeyError as e:
            make = self.deviceinfo['DeviceClass']+" (Model "+self.deviceinfo['ModelNumber']+self.deviceinfo['RegionInfo']+")"
        print("Your device, an "+make+", is running version "+self.deviceinfo['ProductVersion'])
        
    
        
        #app = self.df.iloc[appidx,:].dropna()
        app = self.df[self.df['CFBundleIdentifier']==appid].squeeze().dropna()
        party = app.ApplicationType.lower()
        if party in ['system','user']:
            print(app['CFBundleName'],"("+app['CFBundleIdentifier']+") is a {} app and has permissions:"\
                    .format(party))

            permissions = self.get_permissions(app)
            for permission in permissions:
                print("\t"+str(permission[0])+"\tReason: "+str(permission[1]))
            print("")
        res['permissions'] = permissions
        res['title'] = app['CFBundleExecutable']
        res['Your iOS Device'] = make
        res['iOS Version'] = self.deviceinfo['ProductVersion']

        #entitlements = dict(d[d['CFBundleIdentifier'] == appid]["Entitlements"].tolist()[0])

        #''' remove kTCCService from beginning of string '''
        #def decruft(perms): 
        #    return perms[11:]
        #if "com.apple.private.tcc.allow" in entitlements.keys():
        #    permissions = [decruft(perms) for perms in entitlements["com.apple.private.tcc.allow"]]
        #    print(permissions)
        #elif "com.apple.private.tcc.allow.overridable" in entitlements.keys():
        #    permissions = [decruft(perms) for perms in entitlements["com.apple.private.tcc.allow.overridable"]]
        #    print(permissions)
        #else:
        #    print("Couldn't find any app permissions on '{}'".format(appid))
        #    permissions = []
        
        #res['permissions'] = permissions
        #res['title'] = d[d['CFBundleIdentifier'] == appid]["CFBundleExecutable"].iloc[0]
        
        return res

    def all():
        for appidx in range(self.df.shape[0]):
            app = self.df.iloc[appidx,:].dropna()
            party = app.ApplicationType.lower()
            if party in ['system','user']:
                print(app['CFBundleName'],"("+app['CFBundleIdentifier']+") is a {} app and has permissions:"\
                        .format(party))

                permissions = get_permissions(app)
                for permission in permissions:
                    print("\t"+str(permission[0])+"\tReason: "+str(permission[1]))
                print("")

    def system_apps(self):
        #return self.df.query('ApplicationType=="System"')['CFBundleIdentifier'].tolist()
        return self.df.query('ApplicationType=="System"')['CFBundleIdentifier']

    def installed_apps(self):
        #return self.df.index
        print(self.df)
        print(self.df.columns)
        return self.df['appId']


if __name__ == "__main__":
    fname = sys.argv[1]
    #data = [l.strip() for l in open(fname)]
    ddump = AndroidDump(fname)
    json.dump(ddump.parse_dump_file(fname), open(fname.rsplit('.', 1)[0] + '.json', 'w'), indent=2)
    print(json.dumps(ddump.info('ru.kidcontrol.gpstracker'), indent=2))
