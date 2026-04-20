from isdi.scanner import parse_dump as pdump
import os
import pytest

D = {"a": {"bc1": {"cd11": [1, 3]}, "bc2": {"cd21": [2]}}, "aa": {}}


def test_match_keys_w_one():
    assert pdump._match_keys_w_one(D, "^a$") == ["a"]


def test_match_keys():
    assert pdump.match_keys(D, "^a$//^b.*1$//^.*d11$") == {
        "a": {"bc1": ["cd11"]},
    }
    assert pdump.match_keys(D, "a//^b.*1$//^.*d11$") == {
        "a": {"bc1": ["cd11"]},
        "aa": {},
    }

    assert pdump.match_keys(D, "^a$//^b.*$//^.*d11$") == {
        "a": {"bc1": ["cd11"], "bc2": []},
    }

    # assert pdump.match_keys(D, '^a$//^b.*$//^.*d11$', only_last=True) == {
    #     'a': {'bc2': []},
    # }


def test_prune_leaves():
    keys = pdump.match_keys(D, "^a$//^b.*$//^.*d11$")
    assert pdump.prune_empty_leaves(keys) == {"a": {"bc1": ["cd11"]}}
    assert pdump.prune_empty_leaves(pdump.match_keys(D, "a//^b.*1$//^.*d11$")) == {
        "a": {"bc1": ["cd11"]},
    }


def test_extract():
    keys = pdump.prune_empty_leaves(pdump.match_keys(D, "^a$//^b.*$//^.*d11$"))
    assert keys == {"a": {"bc1": ["cd11"]}}
    assert pdump.extract(D, keys) == [[1, 3]]


def test_get_all_leaves():
    assert sorted(pdump.get_all_leaves(D)) == [1, 2, 3]
    keys = pdump.prune_empty_leaves(pdump.match_keys(D, "^a$//^b.*$//^.*d"))
    assert sorted(pdump.get_all_leaves(keys)) == ["cd11", "cd21"]


@pytest.mark.parametrize(
    "fname, conds",
    [
        (
            "./phone_dumps/test/test1-rc-pixel4_android.txt",
            {
                "in_apps": [
                    ("com.amazon.mShop.android.shopping", "56b26bf"),
                    ("com.aljazeera.mobile", "fa6702e"),
                    ("com.android.sdm.plugins.usccdm", "db6e2b0"),
                ],
                "in_info": [
                    (
                        "com.google.android.uwb.resources",
                        {
                            "firstInstallTime": "1969-12-31 18:00:00",
                            "lastUpdateTime": "1969-12-31 18:00:00",
                            "data_usage": {
                                "data_used": "unknown",
                                "background_data_allowed": "unknown",
                            },
                            "battery_usage": "0 (mAh)",
                        },
                    ),
                    (
                        "com.Slack",
                        {
                            "firstInstallTime": "2023-09-22 15:22:45",
                            "lastUpdateTime": "2025-04-06 01:03:03",
                            "data_usage": {
                                "data_used": "unknown",
                                "background_data_allowed": "unknown",
                            },
                            "battery_usage": "0 (mAh)",
                        },
                    ),
                    (
                        "com.android.providers.downloads",
                        {
                            "firstInstallTime": "2008-12-31 18:00:00",
                            "lastUpdateTime": "2008-12-31 18:00:00",
                            "data_usage": {
                                "data_used": "unknown",
                                "background_data_allowed": "unknown",
                            },
                            "battery_usage": "0 (mAh)",
                        },
                    ),
                ],
            },
        ),
        (
            "./phone_dumps/test/test2-lge-rc.txt",
            {
                "in_apps": [
                    ("com.hy.system.fontserver", "10f809f"),
                    ("com.lge.penprime.overlay", "ba26d8b"),
                    ("com.android.incallui.overlay", "86a753f"),
                ],
                "in_info": [],
            },
        ),
    ],
)
def test_apps(fname, conds):
    if not os.path.exists(fname):
        pytest.skip(f"File {fname} does not exist. Skipping test.")
    ad = pdump.AndroidDump(fname)
    apps = ad.all_apps()
    print(fname, apps[:5])
    # Check if the apps are in the dump
    for app, _ in conds["in_apps"]:
        assert app in apps
    # Check if the app info is correct
    for app, expected in conds["in_info"]:
        info = ad.info(app)
        # print(info)
        for k, v in expected.items():
            assert info[k] == v


class TestIosDump(object):
    # TODO - Write IosDump
    pass
