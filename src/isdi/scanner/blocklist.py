"""
This file have different ways to detect spyware apps add flags to them.
The csv file has two column appId, store, and flag
store: {'playstore', 'appstore', 'offstore'}
flag: {'dual-use', 'spyware', 'safe'}

Flags added to them are from the following four classes
1. "onstore-dual-use": onstore dual-use apps
2. "onstore-spyware": onstore apps which are clearly spyware based on our analysis
3. "offstore-spyware": offstore spyware apps
4. "regex-spy": Regex based spyware detection
5. "odds-ratio": Spyware based on high co-occurrence with other offstore-spyware
"""

import re
from isdi.config import get_config
from .lightweight_df import LightDataFrame

config = get_config()

# Load blocklist using lightweight DataFrame
try:
    APP_FLAGS = (
        LightDataFrame.read_csv(config.APP_FLAGS_FILE, encoding="latin1")
        .fillna(
            {
                "title": "",
                "store": "",
                "flag": "",
                "human": 0,
                "ml_score": 0.0,
                "source": "",
            }
        )
        .isin("flag", {"dual-use", "spyware", "co-occurrence"})
    )
except FileNotFoundError as e:
    print(f"I can't find the blocklist file: {config.APP_FLAGS_FILE!r}.")
    exit(0)

SPY_REGEX = {
    "pos": re.compile(r"(?i)(spy|track|keylog|cheating)"),
    "neg": re.compile(r"(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])"),
}


def dedup_app_flags(apps_list):
    """
    Takes list of dicts like [{"appId": "com.x", "title": "X", "flag": [...]}, ...]
    Returns deduplicated version by appId
    """
    result = {}
    for app in apps_list:
        appid = app.get("appId", "")
        if not appid:
            continue
        if appid not in result:
            result[appid] = {
                "appId": appid,
                "title": app.get("title", ""),
                "flags": [],
            }
        # Collect titles
        title = app.get("title", "")
        if result[appid]["title"] == "":
            result[appid]["title"] = title
        elif title and title != result[appid]["title"]:
            result[appid]["title"] = result[appid]["title"] + " -+- " + title
        # Collect flags
        flags = app.get("flag", [])
        if isinstance(flags, str):
            flags = [flags] if flags else []
        elif isinstance(flags, list):
            flags = flags
        else:
            flags = []
        for flag in flags:
            if flag and flag not in result[appid]["flags"]:
                result[appid]["flags"].append(flag)

    return list(result.values())


def _regex_blocklist(app):
    # print("_regex_balcklist: {}".format(app))
    # return ['regex-spy'] if (SPY_REGEX['pos'].search(app) and not SPY_REGEX['neg'].search(app)) \
    #     else []
    return (
        SPY_REGEX["pos"].search(app) is not None
        and SPY_REGEX["neg"].search(app) is None
    )


def score(flags):
    """The weights are completely arbitrary"""
    weight = {
        "onstore-dual-use": 0.8,
        "dual-use": 0.8,
        "onstore-spyware": 1.0,
        "offstore-spyware": 1.0,
        "offstore-app": 0.8,
        "regex-spy": 0.3,
        "odds-ratio": 0.2,
        "system-app": -0.1,
    }
    return sum(map(lambda x: weight.get(x, 0.0), flags))


def assign_class(flags):
    """Assigns bootstrap text-classes to each flag."""
    # TODO: This is a view function, should not be here
    w = score(flags)
    norm_w = 0 if w <= 0 else 1 if w <= 0.3 else 2 if w <= 0.8 else 3
    _classes = ["", "alert-info", "alert-warning", "alert-primary"]
    return _classes[norm_w]


def flag_str(flags):
    """Returns a comma seperated strings"""

    def _add_class(flag):
        return (
            "primary"
            if "spyware" in flag
            else "warning" if "dual-use" in flag else "info" if "spy" in flag else ""
        )

    def _info(flag):
        return {
            "regex-spy": "This app's name or its app-id contain words like 'spy', 'track', etc.",
            "offstore-spyware": (
                "This app is a spyware app, distributed outside official applicate stores, e.g., "
                "Play Store or iTunes App Store"
            ),
            "co-occurrence": "This app appears very frequently with other offstore-spyware apps.",
            "onstore-dual-use": "This app has a legitimate usecase, but can be harmful in certain situations.",
            "offstore-app": "This app is installed outside Play Store. It might be a preinstalled app too.",
            "dual-use": "This app has a legitimate usecase, but can be harmful in certain situations.",
            "system-app": "This app came preinstalled with the device.",
        }.get(flag.lower(), flag)

    # If spyware <span class='text-danger'>{}</span>
    flags = [y.strip() for y in flags]
    return ",  ".join(
        '<span class="text-{0}"><abbr title="{1}">{2}</abbr></span>'.format(
            _add_class(flag), _info(flag), flag
        )
        for flag in flags
        if len(flag) > 0
    )


def store_str(st):
    if st in ("playstore", "appstore"):
        return "onstore"
    else:
        return "offstore"


def app_title_and_flag(apps_list, offstore_apps=None, system_apps=None):
    """
    Gets app flags and title from app-flags data.

    Args:
        apps_list: List of dicts with 'appId' key, LightDataFrame, or single dict
        offstore_apps: List of offstore app IDs
        system_apps: List of system app IDs

    Returns:
        List of dicts with keys: appId, title, flags
    """
    offstore_apps = offstore_apps or []
    system_apps = system_apps or []

    # Convert input to list of dicts
    if isinstance(apps_list, LightDataFrame):
        apps_data = apps_list.data
    elif isinstance(apps_list, dict):
        apps_data = [apps_list]
    else:
        apps_data = list(apps_list) if hasattr(apps_list, "__iter__") else [apps_list]

    # Get APP_FLAGS as dict keyed by appId for fast lookup
    flags_dict = {}
    for row in APP_FLAGS.data:
        appid = row.get("appId", "")
        if appid:
            flags_dict[appid] = row

    # Build result: merge with APP_FLAGS
    result = {}
    for app in apps_data:
        appid = app.get("appId", "")
        if not appid:
            continue

        # Get flags from APP_FLAGS
        flag_data = flags_dict.get(appid, {})
        title = flag_data.get("title", "") or app.get("title", "")
        flag_str = flag_data.get("flag", "")
        flags = [flag_str] if flag_str else []

        if appid not in result:
            result[appid] = {
                "appId": appid,
                "title": title,
                "flags": flags,
            }

    # Convert to list for dedup
    apps_list_for_dedup = list(result.values())
    deduped = dedup_app_flags(apps_list_for_dedup)

    # Now process the deduped list
    result_dict = {app["appId"]: app for app in deduped}

    # Add offstore-app flag
    for appid in offstore_apps:
        if appid in result_dict:
            if "offstore-app" not in result_dict[appid]["flags"]:
                result_dict[appid]["flags"].append("offstore-app")

    # Add system-app flag
    for appid in system_apps:
        if appid in result_dict:
            if "system-app" not in result_dict[appid]["flags"]:
                result_dict[appid]["flags"].append("system-app")

    # Regex-based flagging
    for appid, app_data in result_dict.items():
        is_spy = _regex_blocklist(appid) or _regex_blocklist(app_data.get("title", ""))
        if is_spy and "regex-spy" not in app_data["flags"]:
            app_data["flags"].append("regex-spy")

    # Return as list
    return list(result_dict.values())


# def flag_apps(apps, device=''):
#     """Flag a list of apps based on the APP_FLAGS obtained from the csv file, or spy regex flags"""
#     _td = APP_FLAGS.loc[set(apps) & set(APP_FLAGS.index)]
#     flagged_apps = (_td['store'].apply(store_str) + '-' + _td['flag']).fillna('').apply(lambda x: [x] if x else [])
#     # print(apps, flagged_apps)
#     a = flagged_apps + flagged_apps.index.map(_regex_blocklist)
#     return a


# def flag_app(app, device=''):
#     return flag_apps([app], device=device).iloc[0]
if __name__ == "__main__":
    apps = [{"appId": "com.TrackView"}, {"appId": "com.apple.mobileme.fmf1"}]
    print(app_title_and_flag(apps, system_apps=["com.apple.mobileme.fmf1"]))
