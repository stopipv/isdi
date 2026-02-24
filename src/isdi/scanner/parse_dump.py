import io
import itertools
import json
import operator
import os
import re
import sys
import logging
from isdi.config import get_config
from collections import OrderedDict
from functools import reduce
from pathlib import Path
from typing import List, Dict, Any
from rsonlite import simpleparse

config = get_config()


def complexparse(lines: list[str]) -> dict:
    """Binary search how much str can be parsed without error"""

    def _find_length_of_valid_string(text: str, s: int, e: int) -> int:
        """Finds the length of the valid string"""
        if s == e:
            return s
        mid = (s + e) // 2
        try:
            simpleparse("".join(text[:mid]))
            return _find_length_of_valid_string(text, mid + 1, e)
        except Exception as ex:
            return _find_length_of_valid_string(text, s, mid)

    try:
        d = simpleparse("".join(lines))
        return d
    except IndentationError as ex:
        pass
        # logging.error(f"IndentationError: {ex}")
    n = _find_length_of_valid_string(lines, 0, len(lines)) - 1
    logging.info(f"Parsed {n} (out of {len(lines)}) lines. starting {lines[:2]}")
    d = simpleparse("".join(lines[:n]))
    if isinstance(d, list):
        d.append({"UNPARSED": lines[n:]})
    else:
        d["UNPARSED"] = lines[n:]
    return d


def count_lspaces(lspaces: str) -> int:
    """Counts the number of leading spaces in a line"""
    # print(">>", repr(l))
    return re.search(r"\S", lspaces).start()


def get_d_at_level(d: dict, lvl: list) -> dict:
    """Returns the dictionary at the level specified by lvl"""
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


def _match_keys_w_one(d, key: str) -> list:
    """Returns a list of keys that matches @key"""
    sk = re.compile(key)
    if not d:
        return []
    if isinstance(d, list):
        d = d[0]
    ret = [k for k in d if sk.match(k) is not None]
    return ret


def match_keys(d, keys: str | list) -> OrderedDict | list:
    """d is a dictionary, and finds all keys that matches @keys
    Returns a list of lists
    """
    if isinstance(keys, str):
        keys = keys.split("//")
    # Handle non-dictionary input
    if not isinstance(d, (dict, list)):
        return OrderedDict() if len(keys) > 1 else []
    ret = _match_keys_w_one(d, keys[0])
    if len(keys) == 1:
        return ret
    result = OrderedDict()
    for k in ret:
        # Only recurse if d[k] is a dictionary or list
        if isinstance(d, list):
            d = d[0]
            continue
        if isinstance(d[k], (dict, list)):
            result[k] = match_keys(d[k], keys[1:])
        else:
            # If we've reached a leaf node but still have keys to match, skip it
            result[k] = OrderedDict() if len(keys) > 1 else d[k]
    return result


def prune_empty_leaves(dkeys: list | dict) -> dict | list:
    """Remove the entries from dkeys all the paths that lead to empty keys"""
    if isinstance(dkeys, list):
        return dkeys
    for k, v in dkeys.items():
        dkeys[k] = prune_empty_leaves(v)
    return {k: v for k, v in dkeys.items() if v}


def get_all_leaves(d: dict) -> list:
    """Returns all leaves in a dictionary"""
    if not isinstance(d, dict):
        return d
    return list(itertools.chain(*(get_all_leaves(v) for v in d.values())))


def extract(d: list | dict, lkeys_dict: list | dict) -> list:
    """Extracts the values from d that match the keys in lkeys_dict"""
    if isinstance(d, list):
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


def split_equalto_delim(k: str) -> list[str]:
    return k.split("=", 1)


def prune_empty_keys(d: dict) -> dict | list:
    """d is an multi-layer dictionary. The function
    converts a sequence of keys into
    array if all have empty values. Also, if keys are of the
    format {"key=value": []}, then convert this into
    a dictionary of {key: value}."""
    if not isinstance(d, dict):
        return d
    if not any(d.values()):
        return list(d.keys())
    remove_keys = []
    for k, v in d.items():
        if len(k.split("=")) == 2 and len(v) == 0:
            remove_keys.append(k)
        else:
            d[k] = prune_empty_keys(v)
    for k in remove_keys:
        if k in d:
            t = k.split("=")
            del d[k]
            d[t[0]] = t[1]
    return d


def retrieve(dict_: dict, nest: list) -> str | dict:
    """
    Navigates dictionaries like dict_[nest0][nest1][nest2]...
    gracefully.
    """
    try:
        return reduce(operator.getitem, nest, dict_)
    except KeyError as e:
        logging.error(f"KeyError: {e} for dict_={dict_} and nest={nest}")
        return ""
    except TypeError as e:
        logging.error(f"TypeError: {e} for dict_={dict_} and nest={nest}")
        return ""


################ CUSTOM ANDROID PARSING #########################
def parse_procstats(text: str) -> dict:
    """Parses the output of `adb shell dumsys procstats`"""
    apps = {}
    current_app = None

    app_re = re.compile(r"^\s*\* ([^ ]+) / ([^ ]+) / (v\d+):")
    stat_re = re.compile(
        r"^\s+([\w\s]+): ([\d\.]+%) \(([^/]+)/([^/]+)/([^)]+)\s+over\s+(\d+)\)"
    )

    for line in text.splitlines():
        app_match = app_re.match(line)
        stat_match = stat_re.match(line)

        if app_match:
            name, uid, version = app_match.groups()
            current_app = {"process": name, "uid": uid, "version": version, "stats": {}}
            apps[current_app["process"]] = current_app

        elif stat_match and current_app:
            stat_type, percent, ram, swap, zram, over = stat_match.groups()
            current_app["stats"][stat_type.strip()] = {
                "percent": percent,
                "ram": ram.split("-"),
                "swap": swap.split("-"),
                "zram": zram.split("-"),
                "samples": int(over),
            }

    return apps


class PhoneDump(object):
    def __init__(self, dev_type, fname):
        self.device_type = dev_type
        self.dumpf = fname
        # df must be a dictionary
        self.df = self.load_file()

    def apps(self):
        raise Exception("Not Implemented")

    def load_file(self):
        raise Exception("Not Implemented")

    def info(self, appid):
        raise Exception("Not Implemented")

    def offstore_apps(self):
        return []


class AndroidDump(PhoneDump):
    def __init__(self, fname):
        super(AndroidDump, self).__init__("android", fname)
        self.df = self.load_file()
        self.apps = None

    @staticmethod
    def custom_parse(service, lines):
        if service == "appops":
            return complexparse(lines)  # TODO: Creat custom parser for appops
        elif service == "procstats":
            return parse_procstats("\n".join(lines))

    def new_parse_dump_file(self, fname: str) -> dict:
        """Not used working using simple parse to parse the files."""
        if not Path(fname).exists():
            logging.error("File: {!r} does not exists".format(fname))
        data = open(fname)
        d = {}
        service = ""
        join_lines = []
        custom_parse_services = {"appops", "procstats"}

        def _clean_dictionary(d):
            """remove non-alphanumeric characters from the end of each key in the dictionary"""
            if isinstance(d, list):
                return [_clean_dictionary(i) for i in d]
            if not isinstance(d, dict):
                return d
            keys = list(d.keys())
            for k in keys:
                new_key = re.sub(r"\W+$", "", k)
                # if new_key != k:
                #   print(f"Cleaning key: {k} --> {new_key}")
                d[new_key] = _clean_dictionary(d.pop(k))
            return d

        def _parse(lines):
            try:
                if service in custom_parse_services:
                    return AndroidDump.custom_parse(service, lines)
                else:
                    r = complexparse(lines)
                    return r
            except Exception as ex:
                logging.error(
                    "Could not parse for {} service={}. Exception={}".format(
                        fname, service, ex
                    )
                )
                raise ex
                return lines

        for i, l in enumerate(data):
            if l.startswith("----"):
                continue
            if l.startswith("DUMP OF SERVICE") or l.startswith("DUMP OF SETTINGS"):
                if service:
                    d[service] = _parse(join_lines)
                service = re.sub(r"DUMP OF SERVICE |DUMP OF SETTINGS ", "", l).strip()
                if service == "netstats detail":
                    service = "net_stats"
                join_lines = []
            else:
                join_lines.append(l)
        if len(join_lines) > 0 and len(d.get(service, [])) == 0:
            d[service] = _parse(join_lines)
        return _clean_dictionary(d)

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
            if t_spcnt >= 0 and t_spcnt >= curr_spcnt[-1] + 2:
                curr_lvl += 1
                curr_spcnt.append(t_spcnt)
            while curr_spcnt and curr_spcnt[-1] > 0 and t_spcnt <= curr_spcnt[-1] - 2:
                curr_lvl -= 1
                curr_spcnt.pop()
            if curr_spcnt[-1] > 0:
                curr_spcnt[-1] = t_spcnt
            curr = get_d_at_level(res, lvls[:curr_lvl])
            k = line.strip().rstrip(":")
            lvls[curr_lvl] = k  # '{} --> {}'.format(curr_lvl, k)
            curr[lvls[curr_lvl]] = {}
        return prune_empty_keys(res)

    def load_file(self, failed_before: str = False) -> dict:
        fname = self.dumpf.rsplit(".", 1)[0] + ".txt"
        json_fname = fname.rsplit(".", 1)[0] + ".json"
        d = {}
        if os.path.exists(json_fname):
            logging.debug(f"Loading json file: {json_fname}")
            with open(json_fname, "r") as f:
                try:
                    d = json.load(f)
                except Exception as ex:
                    logging.error(f">> AndroidDump.load_file(): {ex}")
                    if not failed_before:
                        os.unlink(json_fname)
                        return self.load_file(failed_before=True)
        else:
            with open(json_fname, "w") as f:
                try:
                    d = self.new_parse_dump_file(fname)
                    json.dump(d, f, indent=2)
                except Exception as ex:
                    logging.error(
                        "File ({!r}) could not be opened or parsed.".format(fname)
                    )
                    logging.error("Exception: {}".format(ex))
                    raise (ex)
        return d

    @staticmethod
    def get_data_usage(d, appid, process_uid):
        """Get the data usage for the appid and process_uid"""
        res = {"data_used": "unknown", "background_data_allowed": "unknown"}
        if "net_stats" not in d or not d["net_stats"]:
            return res
        if isinstance(d["net_stats"], list):
            d["net_stats"] = d["net_stats"][0]
        dn = d["net_stats"]
        if process_uid.startswith("u0a"):
            process_uid = "10" + process_uid[3:]

        # Backgroud data allowed?
        bgdata = dn.get("BPF map content", {}).get("mUidCounterSetMap", [])
        allowed = False
        for l in bgdata:
            if l.values()[0].startswith(process_uid):
                allowed = True
                break
        # Get the data usage
        rxstats = dn.get("BPF map content", {}).get("mAppUidStatsMap", [])

        for l in rxstats:
            if l.startswith(process_uid):
                s = l.split(" ")
                if len(s) != 4:
                    logging.error(
                        f"Error parsing net_stats for {appid} with uid {process_uid}: {s}"
                    )
                    return {"foreground": "unknown", "background": "unknown"}
                else:
                    uid, rxBytes, rxPackets, txBytes, txPackets = s
                    res["data_used"] = "{:.2f} MB".format(
                        (int(rxBytes) + int(txBytes)) / (1024 * 1024)
                    )
                    res["background_data_allowed"] = "yes" if allowed else "not allowed"
                    return res
        return res

    @staticmethod
    def get_battery_stat(d, appid, uidu):
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

    def _get_apps(self) -> dict:
        if self.apps:
            return self.apps
        d = self.df
        if not d or not d["package"]:
            logging.error(f"'package' is not a key in self.df, where keys = {list(d.keys())}")
            return {}
        app_d = d["package"][0]["Packages"]
        # get_all_leaves(match_keys(d, "^package$//^Packages//^Package .*"))
        packages = {}
        for k, v in app_d.items():
            m = re.match(r"Package \[(?P<appId>.*)\] \((?P<h>.*)", k)
            if not m:
                logging.error(f"{k} is not an appId")
                continue
                # k is a valid appId
            appId, h = m.groups()
            if "firstInstallTime" not in v:
                t = v.get("User 0", {})
                if isinstance(t, list):
                    t = t[0]
                v["firstInstallTime"] = t.get("firstInstallTime", "")
            packages[appId] = {
                "packageKey": k,
                "flags": v.get("flags", ""),
                "installerPackageName": v.get("installerPackageName", ""),
                "userId": v.get("userId", ""),
                "firstInstallTime": v.get("firstInstallTime", ""),
                "lastUpdateTime": v.get("lastUpdateTime", ""),
            }
        self.apps = packages
        return self.apps

    def all_apps(self) -> list:
        """returns all apps"""
        a = self._get_apps()
        return list(a.keys())

    def system_apps(self) -> list:
        """Return system apps: flags=[ SYSTEM ]"""
        a = self._get_apps()
        system_apps = []
        for appid, meta in a.items():
            flags = meta.get("flags", "")
            if isinstance(flags, list):
                if any("SYSTEM" in str(flag) for flag in flags):
                    system_apps.append(appid)
            else:
                if "SYSTEM" in str(flags):
                    system_apps.append(appid)
        return system_apps

    def offstore_apps(self) -> list:
        approved_installers = {
            "com.android.vending",
            "com.dti.att",  # AT&T phones have this installer
            "com.facebook.system",  # Some phones sell themselves to Facebook
        }
        a = self._get_apps()
        sys_apps = self.system_apps()
        return [
            k
            for k, v in a.items()
            if k not in sys_apps
            and v["installerPackageName"] not in approved_installers
        ]

    def info(self, appid):
        d = self.df
        if not d:
            return {}
        a = self._get_apps()
        if appid not in a:
            logging.error(f"AppId {appid} not found in apps={a}")
            return {}
        app = d["package"][0]["Packages"][a[appid]["packageKey"]]
        res = {
            k: app.get(k, "")
            for k in [
                "userId",
                "firstInstallTime",
                "lastUpdateTime",
                "versionCode",
                "versionName",
                "install permissions",
                "declared permissions",
                "runtime permissions",
            ]
        }

        if "userId" not in res:
            logging.error("UserID not found in res={}".format(res))
            return {}
        process_uid = res["userId"]
        # del res["userId"]
        # memory = match_keys(d, "meminfo//Total PSS by process//.*: {}.*".format(appid))
        uidu_match = list(
            get_all_leaves(
                match_keys(d, "procstats//CURRENT STATS//* {} / .*".format(appid))
            )
        )
        logging.info(f"UIDU match found: {uidu_match}")
        if uidu_match:
            uidu = uidu_match[-1].split(" / ")
        else:
            uidu = "Not Found"
        if len(uidu) > 1:
            uidu = uidu[1]
        else:
            uidu = uidu[0]
        res["data_usage"] = self.get_data_usage(d, appid, process_uid)
        res["battery_usage"] = self.get_battery_stat(d, appid, uidu)  # (mAh)
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
    def __init__(self, fname):
        self.dumpf = fname
        super(IosDump, self).__init__("ios", fname)
        self.df, self.deviceinfo = self.load_file()
        self.device_class = self.deviceinfo.get("DeviceClass", "iPhone/iPad")

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

    def load_file(self):
        try:
            logging.info(f"fname is: {self.dumpf}")
            with open(self.dumpf, "r") as app_data:
                d = json.load(app_data)
        except Exception as ex:
            logging.error(f"Could not load the json file: {self.dumpf}. Exception={ex}")
            return [], {}

        apps = list(d.get("apps", {}).values())
        for app in apps:
            if "appId" not in app:
                app["appId"] = app.get("CFBundleIdentifier", "")
        self.appinfo = apps

        self.deviceinfo = {
            k: d["devinfo"].get(k, "")
            for k in [
                "DeviceClass",
                "ProductType",
                "ModelNumber",
                "RegionInfo",
                "ProductVersion",
            ]
        }
        return self.appinfo, self.deviceinfo

    def check_unseen_permissions(self, permissions):
        for permission in permissions:
            if not permission:
                continue  # Empty permission, skip
            if permission not in self.permissions_map:
                logging.info(
                    f"Have not seen {permission} before. Making note of this..."
                )
                permission_human_readable = permission.replace("kTCCService", "")
                with open(
                    os.path.join(config.STATIC_DATA, "ios_permissions.json"), "w"
                ) as fh:
                    self.permissions_map[permission] = permission_human_readable
                    fh.write(json.dumps(self.permissions_map))
                logging.info("Noted.")

    def get_permissions(self, app: dict) -> list:
        """
        Returns a list of tuples (permission, developer-provided reason for permission).
        Could modify this function to include whether or not the permission can be adjusted
        in Settings.
        """
        system_permissions = retrieve(
            app, ["Entitlements", "com.apple.private.tcc.allow"]
        )
        adjustable_system_permissions = retrieve(
            app, ["Entitlements", "com.apple.private.tcc.allow.overridable"]
        )
        third_party_permissions = list(set(app.keys()) & set(self.permissions_map))
        self.check_unseen_permissions(
            list(system_permissions) + list(adjustable_system_permissions)
        )

        # (permission used, developer reason for requesting the permission)
        all_permissions = list(
            set(
                map(
                    lambda x: (
                        self.permissions_map[x],
                        app.get(x, "permission granted by system"),
                    ),
                    list(
                        set(system_permissions)
                        | set(adjustable_system_permissions)
                        | set(third_party_permissions)
                    ),
                )
            )
        )
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
        # self.df is a list of app dictionaries, find the matching app
        app = next((a for a in self.df if a.get("CFBundleIdentifier") == appid), None)
        if not app:
            logging.warning(f"App with bundle identifier {appid} not found")
            return None

        party = app.get("ApplicationType", "").lower()
        permissions = []
        if party in ["system", "user", "hidden"]:
            logging.info(
                f"{app.get('CFBundleName', '')} ({app.get('CFBundleIdentifier', '')}) is a {party} app and has permissions:"
            )
            # permissions are an array that returns the permission id and an explanation.
            permissions = self.get_permissions(app)
        res["permissions"] = [(p.capitalize(), r) for p, r in permissions]
        res["title"] = app.get("CFBundleExecutable", "")
        res["App Version"] = app.get("CFBundleVersion", "")
        res["Install Date"] = """
        Apple does not officially record iOS app installation dates.  To view when
        '{}' was *last used*: [Settings -> General -> {} Storage].  To view the
        *purchase date* of '{}', follow these instructions:
        https://www.ipvtechresearch.org/post/guides/apple/.  These are the
        closest possible approximations to installation date available to
        end-users.  """.format(res["title"], self.device_class, res["title"])

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

    def system_apps(self):
        if not self.df:
            return []
        return [
            app.get("CFBundleIdentifier", "")
            for app in self.df
            if app.get("ApplicationType") == "System" and app.get("CFBundleIdentifier")
        ]

    def installed_apps_titles(self) -> Dict[str, str]:
        if not self.df:
            return {}
        return {
            app.get("appId", ""): app.get("CFBundleExecutable", "")
            for app in self.df
            if app.get("appId")
        }

    def installed_apps(self):
        # return self.df.index
        if self.df is None:
            return []
        logging.info(f"parse_dump (installed_apps): >> {len(self.df)}")
        return [app.get("appId", "") for app in self.df if app.get("appId")]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parse_dump.py <dump_file> <android|ios>")
        sys.exit(1)
    fname = sys.argv[1]
    # data = [l.strip() for l in open(fname)]
    ddump: PhoneDump
    if sys.argv[2] == "android":
        ddump = AndroidDump(fname)
        json.dump(
            ddump.new_parse_dump_file(fname),
            open(fname.rsplit(".", 1)[0] + ".json", "w"),
            indent=2,
        )
        # print(json.dumps(ddump.info("ru.kidcontrol.gpstracker"), indent=2))
        print(ddump.df["appops"].keys())
        # print(ddump.info("com.isharing.isharing"))
    elif sys.argv[2] == "ios":
        ddump = IosDump(fname)
        print(ddump.installed_apps())
        print(ddump.installed_apps_titles())
