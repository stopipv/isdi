from phone_scanner import parse_dump as pdump
import os

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


test_cond = {
     "./phone_dumps/test/test1-pixel4-rc.txt": {
         "in_apps" : [("com.conducivetech.android.traveler", "56b26bf"), 
                    ("cn.xender", "fa6702e"),
                    ("com.gaana", "db6e2b0")],
         "in_info" : [ ("cn.xender", {
             "firstInstallTime": "2018-10-09 05:52:01",
             "lastUpdateTime": "2018-11-01 01:31:48",
             "data_usage": {"foreground": "0.00 MB", "background": "0.01 MB"},
             "battery_usage": "0 (mAh)",
         })]
    },
    "./phone_dumps/test/test2-lge-rc.txt": {
        "in_apps" : [("com.hy.system.fontserver", "10f809f"),
                    ('com.lge.penprime.overlay', 'ba26d8b'),
                    ('com.android.incallui.overlay', '86a753f')],
        "in_info" : []
    }  
}


class TestAndroidDump(object):
    def test_apps(self):
        for fname, conds in test_cond.items():
            if not os.path.exists(fname):
                print(f"File {fname} does not exist. Skipping test.")
                continue
            self.ad = pdump.AndroidDump(fname)
            apps = self.ad.all_apps()
            # Check if the apps are in the dump
            for app,_ in conds["in_apps"]:
                assert app in apps
            # Check if the app info is correct
            for app, expected in conds["in_info"]:
                info = self.ad.info(app)
                print(info)
                for k, v in expected.items():
                    assert info[k] == v



class TestIosDump(object):
    # TODO - Write IosDump
    pass
