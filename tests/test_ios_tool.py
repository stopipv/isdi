"""isdi.scanner.ios_device: the pymobiledevice3 library path and the limited CLI path."""

import datetime
import json
import sys
import textwrap

import pytest

import pymobiledevice3.lockdown as lockdown_mod
import pymobiledevice3.services.installation_proxy as proxy_mod
import pymobiledevice3.usbmux as usbmux_mod

from isdi.scanner import ios_device, parse_dump
from isdi.scanner.ios_device import IosCli, IosDeviceError, IosLibrary
from isdi.scanner.root_check import check_ios_jailbreak

APPS = {
    "com.example.spy": {"CFBundleIdentifier": "com.example.spy", "CFBundleDisplayName": "Spy",
                        "ApplicationType": "User", "Path": "/private/var/x"},
    "com.apple.mobilenotes": {"CFBundleIdentifier": "com.apple.mobilenotes",
                              "CFBundleDisplayName": "Notes", "ApplicationType": "System"},
}
VALUES = {"DeviceName": "Test iPhone", "ProductType": "iPhone10,1", "ProductVersion": "16.7.10",
          "UniqueDeviceID": "UDID1", "DeviceClass": "iPhone",
          "WiFiAddress": "aa:bb", "ProximitySensorCalibration": b"\x01\x02",
          "LastBackup": datetime.datetime(2026, 1, 2, 3, 4, 5)}


class FakeLockdown:
    def __init__(self, serial, log):
        self.serial, self.log = serial, log
        self.all_values = VALUES
        self.short_info = {"Identifier": serial, **{k: VALUES[k] for k in
                                                    ("DeviceName", "ProductType", "ProductVersion", "DeviceClass")}}

    async def close(self):
        self.log.append(("close", self.serial))


class FakeProxy:
    uninstalled = []

    def __init__(self, lockdown):
        self.lockdown = lockdown

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_apps(self, application_type="Any", calculate_sizes=False):
        assert application_type == "Any" and calculate_sizes is False   # same as `apps list`
        return APPS

    async def uninstall(self, bundle_id):
        if bundle_id == "com.fails":
            raise RuntimeError("APIInternalError")
        FakeProxy.uninstalled.append(bundle_id)


@pytest.fixture
def fake_device(monkeypatch):
    log = []

    class Mux:
        def __init__(self, serial, kind="USB"):
            self.serial, self.connection_type = serial, kind

    async def list_devices(usbmux_address=None):
        return [Mux("UDID1"), Mux("LOCKED")]

    async def create(serial=None, autopair=True, connection_type=None, **kwargs):
        log.append(("create", serial, autopair))
        if serial == "LOCKED":
            raise RuntimeError("PairingDialogResponsePendingError")
        return FakeLockdown(serial, log)

    monkeypatch.setattr(usbmux_mod, "list_devices", list_devices)
    monkeypatch.setattr(lockdown_mod, "create_using_usbmux", create)
    monkeypatch.setattr(proxy_mod, "InstallationProxyService", lambda lockdown: FakeProxy(lockdown))
    return log


def test_library_lists_trusted_and_untrusted(fake_device):
    devices = IosLibrary().list_devices()
    assert devices[0]["Identifier"] == "UDID1" and devices[0]["ProductType"] == "iPhone10,1"
    assert devices[1] == {"Identifier": "LOCKED", "_state": "untrusted"}
    assert ("create", "UDID1", False) in fake_device                    # never triggers pairing
    assert ("close", "UDID1") in fake_device


def test_library_dump_matches_cli_format_and_parses(fake_device, tmp_path):
    dump = IosLibrary().dump("UDID1")
    path = tmp_path / "x_ios.json"
    ios_device.write_dump(str(path), dump)
    data = json.loads(path.read_text())
    assert data["devinfo"]["ProximitySensorCalibration"] == {"$hex": "0102"}   # as pymobiledevice3 prints it
    assert data["devinfo"]["LastBackup"] == "2026-01-02T03:04:05"
    parsed = parse_dump.IosDump(str(path))
    assert "com.example.spy" in parsed.installed_apps()
    assert ("close", "UDID1") in fake_device


def test_library_dump_of_locked_phone_raises(fake_device):
    with pytest.raises(IosDeviceError, match="PairingDialogResponsePending"):
        IosLibrary().dump("LOCKED")


def test_library_uninstall(fake_device):
    assert IosLibrary().uninstall("UDID1", "com.example.spy") is True
    assert FakeProxy.uninstalled[-1] == "com.example.spy"
    assert IosLibrary().uninstall("UDID1", "com.fails") is False


def test_library_errors_listing_return_empty(monkeypatch):
    async def no_usbmuxd(usbmux_address=None):
        raise ConnectionRefusedError("usbmuxd")
    monkeypatch.setattr(usbmux_mod, "list_devices", no_usbmuxd)
    assert IosLibrary().list_devices() == []


# --- limited CLI path (WSL / Termux) ------------------------------------------------

FAKE_PMD3 = textwrap.dedent("""
    import json, sys
    args = sys.argv[1:]
    print("A newer pymobiledevice3 is available")        # noise before the JSON
    if args[:2] == ["usbmux", "list"]:
        print(json.dumps([{"Identifier": "UDID1", "ProductType": "iPhone10,1", "ProductVersion": "16.7"}]))
    elif args[:2] == ["apps", "list"]:
        print(json.dumps(%r))
    elif args[:2] == ["lockdown", "info"]:
        print(json.dumps({"DeviceName": "Test iPhone", "ProductType": "iPhone10,1"}))
    elif args[:2] == ["apps", "uninstall"]:
        sys.exit(0 if args[-1] == "com.example.spy" else 1)
""") % (APPS,)


@pytest.fixture
def cli_tool(tmp_path):
    script = tmp_path / "pmd3.py"
    script.write_text(FAKE_PMD3)
    return IosCli([sys.executable, str(script)])


def test_cli_tool(cli_tool):
    assert cli_tool.list_devices()[0]["Identifier"] == "UDID1"
    dump = cli_tool.dump("UDID1")
    assert set(dump["apps"]) == set(APPS) and dump["devinfo"]["DeviceName"] == "Test iPhone"
    assert cli_tool.uninstall("UDID1", "com.example.spy") is True
    assert cli_tool.uninstall("UDID1", "com.other") is False
    assert cli_tool.afc2_active("UDID1") is None


def test_cli_missing_tool():
    tool = IosCli(["isdi-no-such-pymobiledevice3"])
    assert tool.list_devices() == []
    with pytest.raises(IosDeviceError):
        tool.dump("UDID1")


def test_jailbreak_check_on_cli_platforms_is_inconclusive(cli_tool):
    rooted, reasons = check_ios_jailbreak("UDID1", ["pymobiledevice3.exe"], [], cli_tool)
    assert rooted is None and any("not available" in r for r in reasons)
    rooted, _ = check_ios_jailbreak("UDID1", ["pymobiledevice3.exe"],
                                    [{"CFBundleIdentifier": "org.coolstar.SileoStore"}], cli_tool)
    assert rooted is True                    # package-based checks still work


def test_tool_selection(monkeypatch):
    cfg = type("Cfg", (), {"PLATFORM": "linux", "IOS_CLI": ["pymobiledevice3.exe"], "IOS_CLI_ENV": None})()
    monkeypatch.delenv("PREFIX", raising=False)
    assert isinstance(ios_device.get_tool(cfg), IosLibrary)
    for platform in ("darwin", "windows"):
        cfg.PLATFORM = platform
        assert isinstance(ios_device.get_tool(cfg), IosLibrary)
    cfg.PLATFORM = "wsl"
    assert isinstance(ios_device.get_tool(cfg), IosCli)


# --- IosScanner on top of the tool ---------------------------------------------------


def test_scanner_uses_tool(monkeypatch, tmp_path, fake_device):
    from isdi.scanner import IosScanner

    scanner = IosScanner()
    scanner.tool = IosLibrary()
    listed = scanner.connected_devices()
    assert [d["state"] for d in listed] == ["ready", "untrusted"]
    assert listed[0]["label"].startswith("iPhone 8")
    assert scanner.devices() == ["UDID1"]
    monkeypatch.setattr(scanner, "dump_path", lambda serial, hashed=False: str(tmp_path / f"{serial}_ios.json"))
    assert "com.example.spy" in scanner.get_apps("UDID1")
    assert scanner.device_info("UDID1")[1]                         # parsed device info
    assert scanner._dump_phone("LOCKED") is False
