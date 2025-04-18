import re
from phone_scanner.blocklist import _regex_blocklist, app_title_and_flag
import pandas as pd
import sys

test_list = [
    ("com.spyware.app", True),
    ("com.antispyware.app", False),
    ("com.spyware-anti.app", True),
    ("com.something.Anti-Spyware.com", False),
    ("com.something.Anti-something-Spyware.com", False),
    ("com.-something-Spyware.com", True),
    ("com.Trackware.com", True),
    ("com.AntiTrackware.com", False),
    ("com.spyware-removal.com", False),
]
# regex_ = r'(?i)(?!.*anti)[\-\s]*(spy|track|keylog)'
# regex_ = r'(?i)((?!.*anti)[\-\s]*.*(spy|track)).*'
regex_pos = r"(?i)(spy|track|keylog)"
regex_neg = r"(?i)(anti.*(spy|track|keylog)|(spy|track|keylog).*remov[ea])"


def test_regex():
    for a, m in test_list:
        assert (re.search(regex_pos, a) and not re.search(regex_neg, a)) == m


def test_blocklist():
    for a, m in test_list:
        assert _regex_blocklist(a) == m


def test_app_title_and_flags():
    d = pd.DataFrame(
        {
            "appId": [
                "core.framework",
                "com.android.system",
                "LEM.TrackMe",
                "com.spy2mobile.light",
            ]
        }
    )
    ret = app_title_and_flag(d, ["core.framework", "com.android.system"])
    assert len(ret) == len(ret.appId)
    # assert ret.flags ==
    ret.to_csv(
        index=None
    ) == """appId,title,flags
LEM.TrackMe,TrackMe - GPS Tracker,"['dual-use', 'regex-spy']"
com.android.system, System Service,"['spyware', 'co-occurrence', 'offstore-app']"
com.spy2mobile.light, Data Backup,"['spyware', 'co-occurrence', 'regex-spy']"
core.framework,mSpy,"['spyware', 'offstore-app', 'regex-spy']"
"""
