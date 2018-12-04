from .context import parse_dump as pdump


D = {
    'a': {'bc1': {'cd11': [1, 3]},
          'bc2': {'cd21': [2]}},
    'aa': {}
}


def test_match_keys_w_one():
    assert pdump._match_keys_w_one(D, '^a$') == ['a']


def test_match_keys():
    assert pdump.match_keys(D, '^a$//^b.*1$//^.*d11$') == {
        'a': {'bc1': ['cd11']},
    }
    assert pdump.match_keys(D, 'a//^b.*1$//^.*d11$') == {
        'a': {'bc1': ['cd11']},
        'aa': {},
    }

    assert pdump.match_keys(D, '^a$//^b.*$//^.*d11$') == {
        'a': {'bc1': ['cd11'], 'bc2': []},
    }

    # assert pdump.match_keys(D, '^a$//^b.*$//^.*d11$', only_last=True) == {
    #     'a': {'bc2': []},
    # }


def test_prune_leaves():
    keys = pdump.match_keys(D, '^a$//^b.*$//^.*d11$')
    assert pdump.prune_empty_leaves(keys) == {
        'a': {'bc1': ['cd11']}
    }
    assert pdump.prune_empty_leaves(pdump.match_keys(D, 'a//^b.*1$//^.*d11$')) == {
        'a': {'bc1': ['cd11']},
    }


def test_extract():
    keys = pdump.prune_empty_leaves(pdump.match_keys(D, '^a$//^b.*$//^.*d11$'))
    assert keys == {'a': {'bc1': ['cd11']}}
    assert pdump.extract(D, keys) == [[1, 3]]


def test_get_all_leaves():
    assert sorted(pdump.get_all_leaves(D)) == [1, 2, 3]
    keys = pdump.prune_empty_leaves(pdump.match_keys(D, '^a$//^b.*$//^.*d'))
    assert sorted(pdump.get_all_leaves(keys)) == ['cd11', 'cd21']


class TestAndroidDump(object):
    ad = pdump.AndroidDump('./phone_dumps/83c6500a47585595f72d654829cab29edd2c4f5253e6c05d5576cf04661fd6eb_android.txt')

    def test_apps(self):
        apps = self.ad.apps()
        assert ('com.conducivetech.android.traveler', '56b26bf') in apps
        assert ('cn.xender', 'fa6702e') in apps
        assert ('com.gaana', 'db6e2b0') in apps

    def test_info(self):
        info = self.ad.info('cn.xender')
        expected = {
            'firstInstallTime': '2018-10-09 05:52:01',
            'lastUpdateTime': '2018-11-01 01:31:48',
            'data_usage': {'foreground': '0.00 MB', 'background': '0.01 MB'},
            'battery_usage': "Didn't run"
        }
        for k, v in expected.items():
            assert info[k] == v


class TestIosDump(object):
    # TODO - Write IosDump
    pass


