from isdi.scanner import AndroidScanner, IosScanner
import pytest

"""Fake Tests!!"""


@pytest.mark.skip(reason="Fake test")
def test_android():
    a = AndroidScanner()
    d = a.devices()
    if not d:
        print("No Android phone connected")
        return
    print(a.find_spyapps(d[0]))


@pytest.mark.skip(reason="Fake test")
def test_ios():
    a = IosScanner()
    d = a.devices()
    if not d:
        print("No iOS phone connected")
        return
    print(a.find_spyapps(d[0]))


if __name__ == "__main__":
    test_android()
