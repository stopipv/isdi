from phone_scanner import AndroidScan, IosScan

"""Fake Tests!!"""

def test_android():
    a = AndroidScan()
    d = a.devices()
    if not d:
        print("No Android phone connected")
        return
    print(a.find_spyapps(d[0]))


def test_ios():
    a = IosScan()
    d = a.devices()
    if not d:
        print("No iOS phone connected")
        return
    print(a.find_spyapps(d[0]))



if __name__ == '__main__':
    test_android()
