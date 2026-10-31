"""Listing attached devices for the home page."""

import json

from isdi.scanner import AndroidScanner, IosScanner
from isdi.scanner import runcmd


ADB_DEVICES_L = """List of devices attached
1A2B3C         device usb:1-1 product:panther model:Pixel_7 device:panther transport_id:3
R58M123        unauthorized usb:1-2 transport_id:4
0123ABCD       no permissions (missing udev rules? user is in the plugdev group); see [http://developer.android.com/tools/device.html] usb:1-3

"""


def test_android_connected_devices(monkeypatch):
    monkeypatch.setattr(runcmd, "output", lambda *a, **k: ADB_DEVICES_L)
    sc = AndroidScanner()
    assert sc.connected_devices() == [
        {"serial": "1A2B3C", "label": "Pixel 7", "state": "ready"},
        {"serial": "R58M123", "label": "Android device", "state": "unauthorized"},
        {"serial": "0123ABCD", "label": "Android device", "state": "no permissions"},
    ]
    # Only devices that allowed USB debugging can be scanned.
    assert sc.devices() == ["1A2B3C"]


def test_ios_connected_devices(monkeypatch):
    usbmux = [
        {
            "ConnectionType": "USB",
            "DeviceClass": "iPhone",
            "DeviceName": "iPhone",
            "Identifier": "7814198a0183d848fe949642d52629fee003906a",
            "ProductType": "iPhone10,1",
            "ProductVersion": "16.7.10",
        },
        {"DeviceClass": "iPad", "Identifier": "00008101-unknownmodel", "ProductType": "iPad99,9"},
    ]
    # pymobiledevice3 may print warnings before the JSON.
    output = "Downloading something...\n" + json.dumps(usbmux)
    monkeypatch.setattr(runcmd, "output", lambda *a, **k: output)
    sc = IosScanner()
    assert sc.connected_devices() == [
        {
            "serial": "7814198a0183d848fe949642d52629fee003906a",
            "label": "iPhone 8 (iOS 16.7.10)",
            "state": "ready",
        },
        {"serial": "00008101-unknownmodel", "label": "iPad", "state": "ready"},
    ]
    assert sc.devices() == [d["Identifier"] for d in usbmux]


def test_no_devices_when_tool_fails(monkeypatch):
    monkeypatch.setattr(runcmd, "output", lambda *a, **k: "")
    assert AndroidScanner().connected_devices() == []
    assert IosScanner().connected_devices() == []
