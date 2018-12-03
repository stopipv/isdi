from .context import parse_dump as pdump


def test_android_dump():
    ad = pdump.AndroidDump('./phone_dumps/83c6500a47585595f72d654829cab29edd2c4f5253e6c05d5576cf04661fd6eb_android.txt')
    apps = ad.apps()
    print(apps)
    pass
