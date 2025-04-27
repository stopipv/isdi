"""
Must work completely from the dumps, no interaction with the device is required.
Extract permission usage from the dumps for an appid
"""

import itertools
from rsonlite import simpleparse
import pandas as pd
import datetime
import config
import re
from .runcmd import run_command, catch_err
from . import parse_dump

# MAP = config.ANDROID_PERMISSIONS
DUMPPKG = "dumppkg"


def _parse_time(time_str):
    """
    Parse a time string e.g. (2h13m) into a timedelta object.
    Modified from virhilo's answer at https://stackoverflow.com/a/4628148/851699
    :param time_str: A string identifying a duration.  (eg. 2h13m)
    :return datetime.timedelta: A datetime.timedelta object
        r'^+((?P<days>[\\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\\.\d]+?)s)?((?P<milliseconds>[\.\d]+?)ms)?')
    """
    timedelta_re = re.compile(
        r"^.((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?((?P<milliseconds>[\.\d]+?)ms)?"
    )
    parts = timedelta_re.match(time_str)
    assert parts is not None, (
        "Could not parse any time information from '{}'."
        "Examples of valid strings: '+8h', '+2d8h5m20s', '+2m4s'".format(time_str)
    )
    time_params = {
        name: float(param) for name, param in parts.groupdict().items() if param
    }
    return datetime.timedelta(**time_params)


s = """VIBRATE: allow; time=+29d3h41m32s800ms ago; duration=+1s13ms
CAMERA: allow; time=+38d23h30m11s6ms ago; duration=+420ms
RECORD_AUDIO: allow; time=+38d23h19m35s283ms ago; duration=+10s237ms
WAKE_LOCK: allow; time=+16m12s788ms ago; duration=+10s67ms
TOAST_WINDOW: allow; time=+38d23h22m57s645ms ago; duration=+4s2ms
READ_EXTERNAL_STORAGE: allow; time=+2h7m13s715ms ago
WRITE_EXTERNAL_STORAGE: allow; time=+2h7m13s715ms ago
RUN_IN_BACKGROUND: allow; time=+15m2s867ms ago"""


def get_uid_to_username_map(uid: int) -> str:
    if uid > 10000:
        return "u0a{uid-10000}"
    else:
        return str(uid)

def recent_permissions_used(ddump: parse_dump.AndroidDump, appid: str) -> pd.DataFrame:
    cols = ["appId", "op", "mode", "timestamp", "time_ago", "duration"]
    df = pd.DataFrame([], columns=cols)
    ## TODO: Fix this with new Android appops formatting style! 
    # cmd = "{cli} shell appops get {app}"
    # recently_used = catch_err(run_command(cmd, app=appid))
    a = ddump.info(appid)
    uid = get_uid_to_username_map(int(a['userId']))
    recently_used = None
    d = ddump.df['appops'].get(f"Uid {uid}", {})
    # Some newer Android uses a slightly different format for appops
    if not d:
        d = ddump.df['appops'].get('Current AppOps Service state').get(f"Uid {uid}", {})
    for k, v in d.items():
        if appid in k:
            recently_used = v
            break
    if not recently_used or "No operations." in recently_used:
        return df

    record = {"appId": appid}
    now = datetime.datetime.now()
    # print(recently_used)
    for permission in recently_used:
        match = re.match(r"^(.*?):\s*mode=(\d+);?\s*time=(.*)\s*ago;?", permission)
        if not match:
            continue
        record["op"] = match.group(1).strip()
        record["mode"] = match.group(2).strip()
        record["timestamp"] = (now - _parse_time(match.group(3).strip())).strftime(config.DATE_STR)
        record["time_ago"] = match.group(3).strip()
        df.loc[df.shape[0]] = record
    return df.sort_values(by=["time_ago"]).reset_index(drop=True)


def package_info(ddump, appid):
    a = ddump.info(appid)
    if not a:
        print(f"No package info found for appid: {appid}")
        return [], {}
    permission_keys = ["install permissions", "declared permissions", "runtime permissions"]
    all_perms = list(itertools.chain(*[a[k] for k in permission_keys]))
    pkg_info = {
        k: a.get(k, []) for k in ["versionCode", "versionName", "firstInstallTime", "lastUpdateTime"]
    }
    return all_perms, pkg_info


def permissions_map():
    groupcols = ["group", "group_package", "group_label", "group_description"]
    pcols = ["permission", "package", "label", "description", "protectionLevel"]
    sp = simpleparse(open("Pixel2.permissions", "r").read())
    df = pd.DataFrame(columns=groupcols + pcols)
    record = {}
    ungrouped_d = dict.fromkeys(groupcols, "ungrouped")
    for group in sp[1]:
        record["group"] = group.split(":")[1]
        if record["group"] == "":
            for permission in sp[1][group]:
                record["permission"] = permission.split(":")[1]
                for permission_attr in sp[1][group][permission]:
                    label, val = permission_attr.split(":")
                    record[label.replace("+ ", "")] = val
                df.loc[df.shape[0]] = {**record, **ungrouped_d}
        else:
            for group_attr in sp[1][group]:
                if isinstance(group_attr, str):
                    label, val = group_attr.split(":")
                    record["group_" + label.replace("+ ", "")] = val
                else:
                    for permission in group_attr:
                        record["permission"] = permission.split(":")[1]
                        for permission_attr in group_attr[permission]:
                            label, val = permission_attr.split(":")
                            record[label.replace("+ ", "")] = val
                        df.loc[df.shape[0]] = record
    df.to_csv("static_data/android_permissions.csv")
    return df


def all_permissions(dumpf, appid):
    """
    Returns a tuple of human-friendly permissions (including recently used), non human-friendly app ops,
    non human-friendly permissions, and summary stats.
    """
    ddump = parse_dump.AndroidDump(dumpf)
    app_perms, pkg_info = package_info(ddump, appid)
    # print("--->>> all_permissions\n", app_perms)
    recent_permissions = recent_permissions_used(ddump, appid)

    permissions = pd.read_csv(config.ANDROID_PERMISSIONS_CSV)
    permissions["label"] = permissions.apply(
        lambda x: (
            x["permission"].rsplit(".", n=1)[-1] if x["label"] == "null" else x["label"]
        ),
        axis=1,
    )
    app_permissions_tbl = permissions[
        permissions["permission"].isin(app_perms)
    ].reset_index(drop=True)
    app_permissions_tbl["permission_abbrv"] = app_permissions_tbl.permission.str.rsplit(
        ".", n=1
    ).str[-1]

    # TODO: really 'unknown'?
    hf_recent_permissions = pd.merge(
        recent_permissions,
        app_permissions_tbl,
        left_on="op",
        right_on="permission_abbrv",
        how="right",
    ).fillna("Unknown permission")

    no_hf_recent_permissions = recent_permissions[
        ~recent_permissions["op"].isin(app_permissions_tbl["permission_abbrv"])
    ]
    no_hf = set(app_perms) - set(app_permissions_tbl["permission"].tolist())

    stats = {
        "total_permissions": len(app_perms),
        "hf_permissions": app_permissions_tbl.shape[0],
        "recent_permissions": recent_permissions.shape[0],
        "not_hf_ops": no_hf_recent_permissions.shape[0],
        "not_hf_permissions": len(no_hf),
    }
    return hf_recent_permissions, no_hf_recent_permissions, no_hf, {**stats, **pkg_info}


if __name__ == "__main__":
    import sys
    dumpf = [
        "phone_dumps/test/test2-lge-rc.txt",
        "phone_dumps/test/test1-rc-pixel4_android.txt"
    ]

    ddump = parse_dump.AndroidDump(dumpf[1])
    print(
        package_info(
            ddump,
            "com.example.spyware",
        )
    )
    exit()

    appid = sys.argv[1]
    app_perms, pkg_info = package_info(appid)

    print(app_perms, pkg_info)
    exit()
    recent_permissions = recent_permissions_used(appid)

    # permissions = permissions_map()
    permissions = pd.read_csv(config.ANDROID_PERMISSIONS)
    app_permissions_tbl = permissions[
        permissions["permission"].isin(app_perms)
    ].reset_index(drop=True)
    hf_app_permissions = list(
        zip(app_permissions_tbl.permission, app_permissions_tbl.label)
    )

    # FIXME: delete 'null' labels from counting as human readable.
    print("'{}' uses {} app permissions:".format(appid, len(app_perms)))
    print(
        "{} have human-readable names, and {} were recently used:".format(
            app_permissions_tbl.shape[0], recent_permissions.shape[0]
        )
    )
    # for permission in hf_app_permissions:
    #    print(permission)

    app_permissions_tbl["permission_abbrv"] = app_permissions_tbl["permission"].apply(
        lambda x: x.rsplit(".", n=1)[-1]
    )

    # TODO: really 'unknown'?
    hf_recent_permissions = pd.merge(
        recent_permissions,
        app_permissions_tbl,
        left_on="op",
        right_on="permission_abbrv",
        how="right",
    ).fillna("unknown")
    # print(hf_recent_permissions.columns)
    # print(hf_recent_permissions.shape)
    # print(hf_recent_permissions.op == hf_recent_permissions.permission_abbrv)
    # print(hf_recent_permissions[['label','op','permission']])
    # print(hf_recent_permissions[['label','timestamp','time_ago','permission']])

    # print(hf_recent_permissions[['label','description','timestamp','time_ago', 'duration']])
    print(hf_recent_permissions[["label", "permission_abbrv", "timestamp"]])

    no_hf_recent_permissions = recent_permissions[
        ~recent_permissions["op"].isin(app_permissions_tbl["permission_abbrv"])
    ]
    print(
        "\nCouldn't find human-friendly descriptions for {} recently used app operations:".format(
            no_hf_recent_permissions.shape[0]
        )
    )

    print(no_hf_recent_permissions[["op", "timestamp", "time_ago", "duration"]])

    no_hf = set(app_perms) - set(app_permissions_tbl["permission"].tolist())
    print(
        "\nCouldn't find human-friendly descriptions for {} app permissions:".format(
            len(no_hf)
        )
    )
    for x in no_hf:
        hf = x.split(".")[-1]
        hf = hf[:1] + hf[1:].lower().replace("_", " ")
        print("\t" + str(x) + " (" + str(hf) + ")")
