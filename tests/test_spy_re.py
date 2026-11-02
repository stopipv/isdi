import re
from isdi.scanner.blocklist import _regex_blocklist, app_title_and_flag
from isdi.scanner.lightweight_df import LightDataFrame
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
    d = LightDataFrame(
        [
            {"appId": "core.framework"},
            {"appId": "com.android.system"},
            {"appId": "LEM.TrackMe"},
            {"appId": "com.spy2mobile.light"},
        ]
    )
    ret = app_title_and_flag(d, ["core.framework", "com.android.system"])
    assert len(ret) == len({app.get("appId") for app in ret})
    appids = {app.get("appId") for app in ret}
    assert "core.framework" in appids
    assert "com.android.system" in appids
