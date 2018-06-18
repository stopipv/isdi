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
"""
import re
import config
import pandas as pd

APP_FLAGS = pd.read_csv(config.APP_FLAGS_FILE)
SPY_REGEX = {
    "pos": re.compile(r'(?i)(spy|track|keylog|cheating)'),
    "neg": re.compile(r'(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])'),
}


def _regex_blacklist(app):
    # print("_regex_balcklist: {}".format(app))
    # return ['regex-spy'] if (SPY_REGEX['pos'].search(app) and not SPY_REGEX['neg'].search(app)) \
    #     else []
    return (SPY_REGEX['pos'].search(app) and not SPY_REGEX['neg'].search(app)) is not None


def score(flags):
    """The weights are completely arbitrary"""
    weight = {
        'onstore-dual-use': 0.5,
        'onstore-spyware': 1.0,
        'offstore-spyware': 1.0,
        'offstore-app': 0.8,
        'regex-spy': 0.3,
        'system-app': 0.0
    }
    return sum(map(lambda x: weight.get(x, 0.0), flags))


def assign_class(flags):
    w = score(flags)
    norm_w = 0 if w<=0 else 1 if w<=0.3 else 2 if w<=0.8 else 3
    _classes = ['', 'alert-info', 'alert-warning', 'alert-primary']
    return _classes[norm_w]


def flag_str(flags):
    """Returns a comma seperated strings"""
    def _add_class(flag):
        return ('primary' if 'spyware' in flag else
                'warning' if 'dual-use' in flag else
                'info' if 'spy' in flag else ''
        )
    def _info(flag):
        return "App name or app-id contains words like 'spy', 'track', etc." if flag == "regex-spy"\
            else flag
    # If spyware <span class='text-danger'>{}</span>
    return ',  '.join("<span class=\"text-{0}\"><abbr title=\"{1}\">{2}</abbr></span>"\
                      .format(_add_class(flag), _info(flag), flag) for flag in flags)


def store_str(st):
    return 'onstore' if st in ('playstore', 'appstore') else 'offstore'


def app_title_and_flag(apps, offstore_apps=[], system_apps=[]):
    _td = apps.merge(APP_FLAGS, on='appId', how="left").set_index('appId')
    _td['flags'] = (_td['store'].apply(store_str) + '-' + _td['flag']).fillna('').apply(lambda x: [x] if x else [])
    _td.loc[offstore_apps, 'flags'].apply(lambda x: x.append('offstore-app'))
    _td.loc[system_apps, 'flags'].apply(lambda x: x.append('system-app'))
    # print(apps, flagged_apps)
    spy_regex_app = _td.index.map(_regex_blacklist).values | _td.title.fillna('').apply(_regex_blacklist).values
    _td.loc[spy_regex_app, 'flags'].apply(lambda x: x.extend(['regex-spy']))
    return _td[['title', 'flags']].reset_index()


def flag_apps(apps, device=''):
    """Flag a list of apps based on the APP_FLAGS obtained from the csv file, or spy regex flags"""
    _td = (pd.DataFrame({'appId': apps})
           .join(APP_FLAGS, on='appId', how="left", rsuffix='_r')).set_index('appId')
    flagged_apps = (_td['store'].apply(store_str) + '-' + _td['flag']).fillna('').apply(lambda x: [x] if x else [])
    # print(apps, flagged_apps)
    a = flagged_apps + flagged_apps.index.map(_regex_blacklist)
    return a


def flag_app(app, device=''):
    return flag_apps([app], device=device).iloc[0]
