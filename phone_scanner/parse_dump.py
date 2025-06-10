import io
import itertools
import json
import operator
import os
import re
import sys
from collections import OrderedDict
from functools import reduce
from pathlib import Path
from plistlib import load
from pprint import pprint
from typing import Dict, List

import pandas as pd
from rsonlite import simpleparse

import config


def count_lspaces(lspaces):
    # print(">>", repr(l))
    return re.search(r"\S", lspaces).start()


def get_d_at_level(d, lvl):
    for level in lvl:
        if level not in d:
            d[level] = {}
        d = d[level]
    return d


def clean_json(d):
    if not any(d.values()):
        return list(d.keys())
    else:
        for k, v in d.items():
            d[k] = clean_json(v)


def _match_keys_w_one(d, key, only_last=False):
    """Returns a list of keys that matches @key"""
    sk = re.compile(key)
    if not d:
        return []
    if isinstance(d, list):
        d = d[0]
    ret = [k for k in d if sk.match(k) is not None]
    if only_last:
        return ret[-1:]
    else:
        return ret


def match_keys(d, keys):
    """d is a dictionary, and finds all keys that matches @keys
    Returns a list of lists
    """
    if isinstance(keys, str):
        keys = keys.split("//")
    ret = _match_keys_w_one(d, keys[0])
    if len(keys) == 1:
        return ret
    return OrderedDict((k, match_keys(d[k], keys[1:])) for k in ret)


def prune_empty_leaves(dkeys):
    """Remove the entries from dkeys all the paths that lead to empty keys"""
    if isinstance(dkeys, list):
        return dkeys
    for k, v in dkeys.items():
        dkeys[k] = prune_empty_leaves(v)
    return {k: v for k, v in dkeys.items() if v}


def get_all_leaves(d):
    if not isinstance(d, dict):
        return d
    return itertools.chain(*(get_all_leaves(v) for v in d.values()))


def extract(d, lkeys_dict):
    """This is super inefficient"""
    if isinstance(d, list) and len(d) > 0:
        d = d[0]
    if isinstance(lkeys_dict, list):
        return [d[k] for k in lkeys_dict if k in d]
    r = []
    for k, v in lkeys_dict.items():
        if k in d:
            r.extend(extract(d[k], v))
    return r


def _extract_one(d, lkeys):
    for k in lkeys:
        if isinstance(d, list):
            d = d[0]
        d = d.get(k, {})
    return d


def split_equalto_delim(k):
    return k.split("=", 1)


def prune_empty_keys(d):
    """d is an multi-layer dictionary. The function
    converts a sequence of keys into
    array if all have empty values"""
    if not isinstance(d, dict):
        return d
    if not any(d.values()):
        return list(d.keys())
    for k, v in d.items():
        d[k] = prune_empty_keys(v)
    return d


class PhoneDump(object):
    def __init__(self, dev_type, fname):
        self.device_type = dev_type
        self.fname = fname
        # df must be a dictionary
        self.df = self.load_file()

    def load_file(self):
        raise Exception("Not Implemented")

    def info(self, appid):
        raise Exception("Not Implemented")


class AndroidDump(PhoneDump):
    def __init__(self, fname):
        self.dumpf = fname
        super(AndroidDump, self).__init__("android", fname)
        self.df = self.load_file()

    # def _extract_lines(self, service):
    #     """Extract lines for te DUMP OF SERVICE <service> """
    #     cmd = "sed -n -e '/DUMP OF SERVICE {}/,/DUMP OF SERVICE/p' '{fname}' "\
    #           "| head -n -1"
    #     s = "DUMP OF SERVICE {}".format(service)
    #     started = False
    #     with open(self.dumpf) as f:
    #         for l in f:
    #             if started:
    #                 if "DUMP OF SERVICE" in l:
    #                     break
    #                 else:
    #                     yield l
    #             elif s in l:
    #                 started = True

    @staticmethod
    def custom_parse(service, lines):
        if service == "appops":
            return lines

    @staticmethod
    def new_parse_dump_file(self, fname):
        """Not used working using simple parse to parse the files."""
        if not Path(fname).exists():
            print("File: {!r} does not exists".format(fname))
        data = open(fname)
        d = {}
        service = ""
        join_lines = []
        custom_parse_services = {"appops"}

        def _parse(lines):
            try:
                if service in custom_parse_services:
                    return AndroidDump.custom_parse(service, lines)
                else:
                    return simpleparse("\n".join(join_lines))
            except Exception as ex:
                print(
                    "Could not parse for {} service={}. Exception={}".format(
                        fname, service, ex
                    )
                )
                return lines

        for i, l in enumerate(data):
            if l.startswith("----"):
                continue
            if l.startswith("DUMP OF SERVICE"):
                if service:
                    d[service] = _parse(join_lines)
                service = l.strip().rsplit(" ", 1)[1]
                join_lines = []
            else:
                join_lines.append(l)
        if len(join_lines) > 0 and len(d.get(service, [])) == 0:
            d[service] = _parse(join_lines)
        return d

    def _extract_info_lines(self, fp) -> list:
        lastpos = fp.tell()
        content: List[str] = []
        a = True
        while a:
            line = fp.readline()
            if not line:
                a = False
                break
            if line.startswith("DUMP OF"):
                fp.seek(lastpos)
                return content
            lastpos = fp.tell()
            content.append(line.rstrip())
        return content

    def _parse_dump_service_info_lines(self, lines) -> dict:
        res: Dict[str, dict] = {}
        curr_spcnt = [0]
        curr_lvl = 0
        lvls = ["" for _ in range(20)]  # Max 20 levels allowed
        i = 0
        while i < len(lines):
            line = lines[i]
            i += 1
            if not line.strip():  # subsection ends
                continue
            line = line.replace("\t", " " * 5)
            t_spcnt = count_lspaces(line)
            # print(t_spcnt, curr_spcnt, curr_lvl)
            # if t_spcnt == 1:
            #     print(repr(l))
            if t_spcnt >= 0 and t_spcnt >= curr_spcnt[-1] + 2:
                curr_lvl += 1
                curr_spcnt.append(t_spcnt)
            while curr_spcnt and curr_spcnt[-1] > 0 and t_spcnt <= curr_spcnt[-1] - 2:
                curr_lvl -= 1
                curr_spcnt.pop()
            if curr_spcnt[-1] > 0:
                curr_spcnt[-1] = t_spcnt
            # assert (t_spcnt != 0) or (curr_lvl == 0), \
            #         "t_spc: {} <--> curr_lvl: {}\n{}".format(t_spcnt, curr_lvl, l)
            # print(lvls[:curr_lvl], curr_lvl, curr_spcnt)
            curr = get_d_at_level(res, lvls[:curr_lvl])
            k = line.strip().rstrip(":")
            lvls[curr_lvl] = k  # '{} --> {}'.format(curr_lvl, k)
            curr[lvls[curr_lvl]] = {}
        return prune_empty_keys(res)

    # @staticmethod
    def parse_dump_file(self, fname) -> dict:
        if not Path(fname).exists():
            #print("File: {!r} does not exists".format(fname))
            raise FileNotFoundError(fname)
        fp = open(fname)
        d = {}
        service = ""
        # curr_spcnt, curr_lvl = 0, 0
        while True:
            line = fp.readline().rstrip()
            if line.startswith("----"):
                continue

            if line.startswith("DUMP OF SERVICE"):  # Service
                service = line.strip().rsplit(" ", 1)[1]
                content = self._extract_info_lines(fp)
                print(f"Content: {service!r}", content[:10])
                d[service] = self._parse_dump_service_info_lines(content)

            elif line.startswith("DUMP OF SETTINGS"):  # Setting
                setting = "settings_" + line.strip().rsplit(" ", 1)[1]
                content = self._extract_info_lines(fp)
                settings_d = dict(line.split("=", 1) for line in content if "=" in line)
                d[setting] = settings_d
            else:
                if not line:
                    break
                print(f"Something wrong! --> {line!r}")
        return d

    def load_file(self, failed_before=False):
        fname = self.fname.rsplit(".", 1)[0] + ".txt"
        json_fname = fname.rsplit(".", 1)[0] + ".json"
        d = {}
        if os.path.exists(json_fname):
            with open(json_fname, "r") as f:
                try:
                    d = json.load(f)
                except Exception as ex:
                    print(f">> AndroidDump.load_file(): {ex}", file=sys.stderr)
                    if not failed_before:
                        os.unlink(json_fname)
                        return self.load_file(failed_before=True)
        else:
            with open(json_fname, "w") as f:
                try:
                    d = self.parse_dump_file(fname)
                    json.dump(d, f, indent=2)
                except Exception as ex:
                    print("File ({!r}) could not be opened or parsed.".format(fname))
                    print("Exception: {}".format(ex))
                    raise (ex)
                    return {}
        return d

    @staticmethod
    def get_data_usage(d, process_uid):
        if "net_stats" not in d:
            return {"foreground": "unknown", "background": "unknown"}
        # FIXME: pandas.errors.ParserError: Error tokenizing data. C error: Expected 21 fields in line 556, saw 22
        # parser error (tested on SM-G965U,Samsung,8.0.0)
        try:
            net_stats = pd.read_csv(
                io.StringIO("\n".join(d["net_stats"])), on_bad_lines="warn"
            )
        except pd.errors.EmptyDataError:
            config.logging.warning(
                f"No net_stats for {d['appId']} is empty and has been skipped."
            )
            net_stats = pd.DataFrame()

        d = net_stats.query('uid_tag_int == "{}"'.format(process_uid))[
            ["uid_tag_int", "cnt_set", "rx_bytes", "tx_bytes"]
        ].astype(int)

        def s(c):
            return d[d["cnt_set"] == c].eval("rx_bytes+tx_bytes").sum() / (1024 * 1024)

        return {
            "foreground": "{:.2f} MB".format(s(1)),
            "background": "{:.2f} MB".format(s(0)),
        }

    @staticmethod
    def get_battery_stat(d, uidu):
        b = list(
            get_all_leaves(
                match_keys(
                    d,
                    "batterystats//Statistics since last charge//Estimated power use .*"
                    "//^Uid {}:.*".format(uidu),
                )
            )
        )
        if not b:
            return "0 (mAh)"
        else:
            t = b[0].split(":")
            return t[1]
        return b

    def apps(self):
        d = self.df
        if not d:
            return {}

        def get_appid_h(txt):
            m = re.match(r"Package \[(?P<appId>.*)\] \((?P<h>.*)\)", txt)
            if m:
                return m.groups()

        packages = map(
            get_appid_h,
            get_all_leaves(match_keys(d, "^package$//^Packages//^Package .*")),
        )
        return [c for c in packages if c]

    def info(self, appid):
        d = self.df
        if not d:
            return {}
        package = extract(
            d, match_keys(d, "^package$//^Packages//^Package [{}].*".format(appid))
        )

        other_info = [
            get_all_leaves(match_keys(package, v))
            for v in ["userId", "firstInstallTime", "lastUpdateTime"]
        ]
        res = dict(map(split_equalto_delim, [x[0] for x in other_info if x]))

        if "userId" not in res:
            print("UserID not found in res={}".format(res))
            return {}
        process_uid = res["userId"]
        del res["userId"]
        # memory = match_keys(d, "meminfo//Total PSS by process//.*: {}.*".format(appid))
        uidu_match = list(
            get_all_leaves(
                match_keys(d, "procstats//CURRENT STATS//* {} / .*".format(appid))
            )
        )
        print(uidu_match)
        if uidu_match:
            uidu = uidu_match[-1].split(" / ")
        else:
            uidu = "Not Found"
        if len(uidu) > 1:
            uidu = uidu[1]
        else:
            uidu = uidu[0]
        res["data_usage"] = self.get_data_usage(d, process_uid)
        res["battery_usage"] = self.get_battery_stat(d, uidu)  # (mAh)
        # print('RESULTS')
        # print(res)
        # print('END RESULTS')
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
    def __init__(self, fplist, finfo=None):
        self.device_type = "ios"
        self.fname = fplist
        if finfo:
            self.finfo = finfo
            self.deviceinfo = self.load_device_info()
            self.device_class = self.deviceinfo.get("DeviceClass", "")
        else:
            self.device_class = "iPhone/iPad"
        self.df = self.load_file()

        # FIXME: not efficient to load here everytime?
        # load permissions mappings and apps plist
        self.permissions_map = {}
        self.model_make_map = {}
        with open(os.path.join(config.STATIC_DATA, "ios_permissions.json"), "r") as fh:
            self.permissions_map = json.load(fh)
        with open(
            os.path.join(config.STATIC_DATA, "ios_device_identifiers.json"), "r"
        ) as fh:
            self.model_make_map = json.load(fh)

    def __nonzero__(self):
        return len(self.df) > 0

    def __len__(self):
        return len(self.df)

    def load_device_info(self):
        try:
            with open(self.finfo, "rb") as data:
                device_info = json.load(data)
            return device_info

        except Exception as ex:
            print("Load_deviceinfo in parse_dump failed with exception {!r}".format(ex))
            return {
                "DeviceClass": "",
                "ProductType": "",
                "ModelNumber": "",
                "RegionInfo": "",
                "ProductVersion": "",
            }

    def load_file(self):
        # d = pd.read_json(self.fname)[self.COLS].set_index(self.INDEX)
        try:
            print("fname is: {}".format(self.fname))
            apps_list = []
            with open(self.fname, "r") as app_data:
                apps_json = json.load(app_data)
                for k in apps_json:
                    apps_list.append(apps_json[k])

            d = pd.DataFrame(apps_list)
            d["appId"] = d["CFBundleIdentifier"]
            return d
        except Exception as ex:
            print(ex)
            print("Could not load the json file: {}".format(self.fname))
            return pd.DataFrame([], columns=["appId"])

    def check_unseen_permissions(self, permissions):
        # flatten the permissions list
        pprint(permissions)

        for permission in permissions:
            if not permission:
                continue  # Empty permission, skip
            if permission not in list(self.permissions_map.keys()):
                print(f"Have not seen {permission} before. Making note of this...")
                permission_human_readable = permission.replace("kTCCService", "")
                with open(
                    os.path.join(config.THIS_DIR, "ios_permissions.json"), "w"
                ) as fh:
                    self.permissions_map[permission] = permission_human_readable
                    fh.write(json.dumps(self.permissions_map))
                print("Noted.")
            # print('\t'+msg+": "+str(PERMISSIONS_MAP[permission])+"\tReason: "+app.get(permission,'system app'))

    def get_permissions(self, app: str) -> list:
        """
        Returns a list of tuples (permission, developer-provided reason for permission).
        Could modify this function to include whether or not the permission can be adjusted
        in Settings.
        """
        system_permissions = app["Entitlements"].get("com.apple.private.tcc.allow", [])

        # Need to clean up some permissions that are nested lists
        if any(isinstance(item, list) for item in system_permissions):
            # Flatten the list of lists
            new_sys_perms = []
            for perm in system_permissions:
                if isinstance(perm, list):
                    for p in perm:
                        new_sys_perms.append(p)
                else:
                    new_sys_perms.append(perm)

        adjustable_system_permissions = app["Entitlements"].get("com.apple.private.tcc.allow.overridable", [])
        
        third_party_permissions = list(set(app.keys()) & set(self.permissions_map))

        # unpack
        new_sys_permissions = []
        for permission in system_permissions:
            if type(permission) == list:
                for p in permission:
                    new_sys_permissions.append(p)
            else:
                new_sys_permissions.append(permission)
        system_permissions = new_sys_permissions

        self.check_unseen_permissions(
            list(system_permissions) + list(adjustable_system_permissions)
        )

        pprint("SYSTEM PERMISSIONS")
        pprint(system_permissions)

        # (permission used, developer reason for requesting the permission)
        all_permissions = list(
            set(
                map(
                    lambda x: (
                        self.permissions_map[x],
                        app.get(x, default="Permission granted by system"),
                    ),
                    list(
                        set(system_permissions)
                        | set(adjustable_system_permissions)
                        | set(third_party_permissions)
                    ),
                )
            )
        )
        # pii = retrieve(
        #     app,
        #     ["Entitlements", "com.apple.private.MobileGestalt.AllowedProtectedKeys"],
        # )
        # print("\tPII: "+str(pii))
        return all_permissions

    def device_info(self):
        # TODO: see idevicediagnostics mobilegestalt KEY
        # https://blog.timac.org/2017/0124-deobfuscating-libmobilegestalt-keys/
        # can detect Airplane Mode, PasswordConfigured, lots of details about hardware.
        # https://gist.github.com/shu223/c108bd47b4c9271e55b5
        m = {}
        try:
            m["model"] = self.model_make_map[self.deviceinfo["ProductType"]]
        except KeyError:
            m["model"] = "{DeviceClass} (Model {ModelNumber} {RegionInfo})".format(
                **self.deviceinfo
            )
        m["version"] = self.deviceinfo["ProductVersion"]
        return "{model} (running iOS {version})".format(**m), m

    def info(self, appid):
        """
        Returns dict containing the following:
        'permission': tuple (all permissions of appid, developer
        reasons for requesting the permissions)
        'title': the human-friendly name of the app.
        'jailbroken': tuple (whether or not phone is suspected to be jailbroken, rationale)
        'phone_kind': tuple (make, OS version)
        """
        # d = self.df
        res = {
            "title": "",
            "jailbroken": "",  # TODO: These are never set: phone_kind and jailbroken
            "phone_kind": "",
        }
        # app = self.df.iloc[appidx,:].dropna()
        app = self.df[self.df["CFBundleIdentifier"] == appid].squeeze().dropna()
        party = app.ApplicationType.lower()
        permissions = []
        if party in ["system", "user", "hidden"]:
            print(
                f"{app['CFBundleName']} ({app['CFBundleIdentifier']}) is a {party} app and has permissions:"
            )
            # permissions are an array that returns the permission id and an explanation.
            permissions = self.get_permissions(app)
        res["permissions"] = [(p.capitalize(), r) for p, r in permissions]
        res["title"] = app["CFBundleExecutable"]
        res["App Version"] = app["CFBundleVersion"]
        res["Install Date"] = (
            """
        Apple does not officially record iOS app installation dates.  To view when
        '{}' was *last used*: [Settings -> General -> {} Storage].  To view the
        *purchase date* of '{}', follow these instructions:
        https://www.ipvtechresearch.org/post/guides/apple/.  These are the
        closest possible approximations to installation date available to
        end-users.  """.format(
                res["title"], self.device_class, res["title"]
            )
        )

        res["Battery Usage"] = (
            "To see recent battery usage of '{title}': "
            "[Settings -> Battery -> Battery Usage].".format(**res)
        )
        res["Data Usage"] = (
            "To see recent data usage (not including Wifi) of '{}': [Settings -> Cellular -> Cellular Data].".format(
                res["title"]
            )
        )

        return res

    # TODO: The following function is incorrect or incomplete. Commenting out for now.
    # def all(self):
    #     for appidx in range(self.df.shape[0]):
    #         app = self.df.iloc[appidx,:].dropna()
    #         party = app.ApplicationType.lower()
    #         if party in ['system','user']:
    #             print(app['CFBundleName'],"("+app['CFBundleIdentifier']+") is a {} app and has permissions:"\
    #                     .format(party))

    #             permissions = get_permissions(app)
    #             for permission in permissions:
    #                 print("\t"+str(permission[0])+"\tReason: "+str(permission[1]))
    #             print("")

    def system_apps(self):
        # return self.df.query('ApplicationType=="System"')['CFBundleIdentifier'].tolist()
        return self.df.query('ApplicationType=="System"')["CFBundleIdentifier"]

    def installed_apps_titles(self) -> pd.DataFrame:
        if self:
            return self.df.rename(
                index=str, columns={"CFBundleExecutable": "title"}
            ).set_index("appId")

    def installed_apps(self):
        # return self.df.index
        if self.df is None:
            return []
        print("parse_dump (installed_apps): >>", self.df.columns, len(self.df))
        return self.df["appId"].to_list()


if __name__ == "__main__":
    fname = sys.argv[1]
    # data = [l.strip() for l in open(fname)]
    ddump: PhoneDump
    if sys.argv[2] == "android":
        ddump = AndroidDump(fname)
        json.dump(
            ddump.parse_dump_file(fname),
            open(fname.rsplit(".", 1)[0] + ".json", "w"),
            indent=2,
        )
        print(json.dumps(ddump.info("ru.kidcontrol.gpstracker"), indent=2))
    elif sys.argv[2] == "ios":
        ddump = IosDump(fname)
        print(ddump.installed_apps())
        print(ddump.installed_apps_titles().to_csv())
