"""
This file have different ways to detect spyware apps add flags to them.
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
    "pos": re.compile(r'(?i)(spy|track|keylog)'),
    "neg": re.compile(r'(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])'),
}


def _regex_blacklist(app):
    return ['regex-spy'] if (SPY_REGEX['pos'].search(app) and not SPY_REGEX['neg'].search(app)) \
        else []


def flag_apps(apps, device=''):
    """Flag a list of apps based on the APP_FLAGS obtained from the csv file, or spy regex flags"""
    _td = (pd.DataFrame({'appId': apps}).set_index('appId')
           .join(APP_FLAGS.set_index('appId'), how="left"))
    flagged_apps = (_td['store'] + '-' + _td['flag']).fillna('').apply(lambda x: [x] if x else [])
    print(flagged_apps)
    return flagged_apps + flagged_apps.index.map(_regex_blacklist)


def flag_app(app, device=''):
    return flag_apps([app], device=device).iloc[0]

