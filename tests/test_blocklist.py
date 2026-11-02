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


def _csv_rows():
    import csv
    from isdi.scanner import blocklist

    with open(blocklist.config.APP_FLAGS_FILE, encoding="latin1") as fh:
        return list(csv.DictReader(fh))


def test_blocklist_flags_are_kept():
    """Every flagged app in app-flags.csv must keep its flag after lookup."""
    rows = [
        r
        for r in _csv_rows()
        if r["flag"] in {"dual-use", "spyware", "stalkerware", "co-occurrence"}
    ]
    assert rows
    expected = {r["appId"]: r["flag"] for r in rows}
    ret = app_title_and_flag([{"appId": a} for a in expected])
    assert len(ret) == len(expected)
    for app in ret:
        assert expected[app["appId"]] in app["flags"], app


def test_spyware_and_stalkerware_get_top_class():
    from isdi.scanner.blocklist import assign_class, flag_str, score

    for flag in ("spyware", "stalkerware"):
        assert score([flag]) == 1.0
        assert assign_class([flag]) == "alert-primary"
        assert "text-primary" in flag_str([flag])
    assert assign_class(["dual-use"]) == "alert-warning"

    ids = [r["appId"] for r in _csv_rows() if r["flag"] in ("spyware", "stalkerware")]
    for app in app_title_and_flag([{"appId": a} for a in ids]):
        assert assign_class(app["flags"]) == "alert-primary", app
