"""
Must work completely from the dumps, no interaction with the device is required.
Extract permission usage from the dumps for an appid
"""

import csv
import itertools
from rsonlite import simpleparse
import datetime
from isdi.config import get_config
import re
from collections import defaultdict
from .runcmd import run_command, catch_err
from . import parse_dump

config = get_config()

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


def _read_csv_rows(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _fill_unknowns(row: dict, value: str = "Unknown permission") -> dict:
    return {k: (value if v in (None, "") else v) for k, v in row.items()}


def recent_permissions_used(ddump: parse_dump.AndroidDump, appid: str) -> list[dict]:
    rows = []
    ## TODO: Fix this with new Android appops formatting style!
    # cmd = "{cli} shell appops get {app}"
    # recently_used = catch_err(run_command(cmd, app=appid))
    a = ddump.info(appid)
    uid = get_uid_to_username_map(int(a["userId"]))
    recently_used = None
    d = ddump.df["appops"].get(f"Uid {uid}", {})
    # Some newer Android uses a slightly different format for appops
    if not d:
        d = ddump.df["appops"].get("Current AppOps Service state").get(f"Uid {uid}", {})
    for k, v in d.items():
        if appid in k:
            recently_used = v
            break
    if not recently_used or "No operations." in recently_used:
        return []

    now = datetime.datetime.now()
    # print(recently_used)
    for permission in recently_used:
        match = re.match(r"^(.*?):\s*mode=(\d+);?\s*time=(.*)\s*ago;?", permission)
        if not match:
            continue
        record = {
            "appId": appid,
            "op": match.group(1).strip(),
            "mode": match.group(2).strip(),
            "timestamp": (now - _parse_time(match.group(3).strip())).strftime(
                config.DATE_STR
            ),
            "time_ago": match.group(3).strip(),
        }
        rows.append(record)
    rows.sort(key=lambda row: _parse_time(row.get("time_ago", "+0s")))
    return rows


def package_info(ddump, appid):
    a = ddump.info(appid)
    if not a:
        print(f"No package info found for appid: {appid}")
        return [], {}
    permission_keys = [
        "install permissions",
        "declared permissions",
        "runtime permissions",
    ]
    all_perms = list(itertools.chain(*[a[k] for k in permission_keys]))
    pkg_info = {
        k: a.get(k, [])
        for k in ["versionCode", "versionName", "firstInstallTime", "lastUpdateTime"]
    }
    return all_perms, pkg_info


def permissions_map():
    groupcols = ["group", "group_package", "group_label", "group_description"]
    pcols = ["permission", "package", "label", "description", "protectionLevel"]
    sp = simpleparse(open("Pixel2.permissions", "r").read())
    rows = []
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
                rows.append({**record, **ungrouped_d})
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
                        rows.append(dict(record))
    with open(
        "static_data/android_permissions.csv", "w", encoding="utf-8", newline=""
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=groupcols + pcols)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return rows


def all_permissions(dumpf, appid):
    """
    Returns a tuple of human-friendly permissions (including recently used), non human-friendly app ops,
    non human-friendly permissions, and summary stats.
    """
    ddump = parse_dump.AndroidDump(dumpf)
    app_perms, pkg_info = package_info(ddump, appid)
    # print("--->>> all_permissions\n", app_perms)
    recent_permissions = recent_permissions_used(ddump, appid)

    permissions = _read_csv_rows(config.ANDROID_PERMISSIONS_CSV)
    for row in permissions:
        label = row.get("label", "")
        permission = row.get("permission", "")
        if label == "null":
            row["label"] = permission.rsplit(".", 1)[-1] if permission else label

    app_permissions_tbl = [
        row for row in permissions if row.get("permission") in app_perms
    ]
    for row in app_permissions_tbl:
        permission = row.get("permission", "")
        row["permission_abbrv"] = permission.rsplit(".", 1)[-1] if permission else ""

    recent_by_op = defaultdict(list)
    for row in recent_permissions:
        recent_by_op[row.get("op", "")].append(row)

    hf_recent_permissions = []
    for app_row in app_permissions_tbl:
        op = app_row.get("permission_abbrv", "")
        matches = recent_by_op.get(op, [])
        if matches:
            for match in matches:
                merged = dict(app_row)
                merged.update(match)
                hf_recent_permissions.append(_fill_unknowns(merged))
        else:
            merged = dict(app_row)
            for key in ["appId", "op", "mode", "timestamp", "time_ago", "duration"]:
                merged.setdefault(key, None)
            hf_recent_permissions.append(_fill_unknowns(merged))

    app_perm_abbrvs = {row.get("permission_abbrv", "") for row in app_permissions_tbl}
    no_hf_recent_permissions = [
        row for row in recent_permissions if row.get("op", "") not in app_perm_abbrvs
    ]
    no_hf = {
        perm
        for perm in app_perms
        if perm not in {row.get("permission") for row in app_permissions_tbl}
    }

    stats = {
        "total_permissions": len(app_perms),
        "hf_permissions": len(app_permissions_tbl),
        "recent_permissions": len(recent_permissions),
        "not_hf_ops": len(no_hf_recent_permissions),
        "not_hf_permissions": len(no_hf),
    }
    return hf_recent_permissions, no_hf_recent_permissions, no_hf, {**stats, **pkg_info}


if __name__ == "__main__":
    import sys

    dumpf = [
        "phone_dumps/test/test2-lge-rc.txt",
        "phone_dumps/test/test1-rc-pixel4_android.txt",
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
    app_perms, pkg_info = package_info(ddump, appid)

    print(app_perms, pkg_info)
    exit()
    recent_permissions = recent_permissions_used(ddump, appid)

    permissions = _read_csv_rows(config.ANDROID_PERMISSIONS)
    for row in permissions:
        label = row.get("label", "")
        permission = row.get("permission", "")
        if label == "null":
            row["label"] = permission.rsplit(".", 1)[-1] if permission else label
    app_permissions_tbl = [
        row for row in permissions if row.get("permission") in app_perms
    ]
    hf_app_permissions = [
        (row.get("permission"), row.get("label")) for row in app_permissions_tbl
    ]

    # FIXME: delete 'null' labels from counting as human readable.
    print("'{}' uses {} app permissions:".format(appid, len(app_perms)))
    print(
        "{} have human-readable names, and {} were recently used:".format(
            len(app_permissions_tbl), len(recent_permissions)
        )
    )

    for row in app_permissions_tbl:
        permission = row.get("permission", "")
        row["permission_abbrv"] = permission.rsplit(".", 1)[-1] if permission else ""

    recent_by_op = defaultdict(list)
    for row in recent_permissions:
        recent_by_op[row.get("op", "")].append(row)
    hf_recent_permissions = []
    for app_row in app_permissions_tbl:
        op = app_row.get("permission_abbrv", "")
        matches = recent_by_op.get(op, [])
        if matches:
            for match in matches:
                merged = dict(app_row)
                merged.update(match)
                hf_recent_permissions.append(_fill_unknowns(merged, value="unknown"))
        else:
            merged = dict(app_row)
            for key in ["appId", "op", "mode", "timestamp", "time_ago", "duration"]:
                merged.setdefault(key, None)
            hf_recent_permissions.append(_fill_unknowns(merged, value="unknown"))

    print(
        [
            {
                "label": row.get("label"),
                "permission_abbrv": row.get("permission_abbrv"),
                "timestamp": row.get("timestamp"),
            }
            for row in hf_recent_permissions
        ]
    )

    app_perm_abbrvs = {row.get("permission_abbrv", "") for row in app_permissions_tbl}
    no_hf_recent_permissions = [
        row for row in recent_permissions if row.get("op", "") not in app_perm_abbrvs
    ]
    print(
        "\nCouldn't find human-friendly descriptions for {} recently used app operations:".format(
            len(no_hf_recent_permissions)
        )
    )

    print(
        [
            {
                "op": row.get("op"),
                "timestamp": row.get("timestamp"),
                "time_ago": row.get("time_ago"),
                "duration": row.get("duration"),
            }
            for row in no_hf_recent_permissions
        ]
    )

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
