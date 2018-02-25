from phone_scanner import AndroidScan, IosScan

"""Fake Tests!!"""


def test_android():
    a = AndroidScan()
    print(a.find_spyapps())


def test_ios():
    a = IosScan()
    print(a.find_spyapps())


if __name__ == '__main__':
    test_android()
