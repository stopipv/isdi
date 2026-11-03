"""Background device watchers (isdi.scanner.device_watch) and related helpers."""

import asyncio
import os
import plistlib
import socket
import struct
import sys
import tempfile
import textwrap
import threading
import time

import pytest

from isdi.scanner import device_watch, parse_adb_devices


def wait_for(cond, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        value = cond()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("condition not met in time")


# --- adb track-devices ------------------------------------------------------

FAKE_ADB = textwrap.dedent(
    """
    import sys, time
    assert sys.argv[1:] == ["track-devices", "-l"], sys.argv
    def frame(text):
        sys.stdout.write("%04x%s" % (len(text), text)); sys.stdout.flush()
    frame("")
    time.sleep(0.3)
    frame("1A2B3C         device usb:1-1 product:panther model:Pixel_7 transport_id:3\\n")
    time.sleep(0.3)
    frame("1A2B3C         device usb:1-1 model:Pixel_7\\nR58M123        unauthorized usb:1-2\\n")
    time.sleep(30)
    """
)


def test_adb_watcher_follows_track_devices(tmp_path):
    script = tmp_path / "fake_adb.py"
    script.write_text(FAKE_ADB)
    w = device_watch.AdbWatcher([sys.executable, str(script)], parse_adb_devices)
    assert w.snapshot() is None          # nothing known yet: callers poll
    w.start()
    try:
        devices = wait_for(lambda: (w.snapshot() or [None, None])[1:] and w.snapshot())
        assert devices == [
            {"serial": "1A2B3C", "label": "Pixel 7", "state": "ready"},
            {"serial": "R58M123", "label": "Android device", "state": "unauthorized"},
        ]
    finally:
        w.stop()
        w.join(5)


def test_adb_watcher_without_adb_reports_no_snapshot():
    w = device_watch.AdbWatcher(["/nonexistent/adb"], parse_adb_devices)
    w.start()
    try:
        time.sleep(0.3)
        assert w.is_alive() and w.snapshot() is None
    finally:
        w.stop()
        w.join(5)


def test_read_frame_handles_windows_crlf():
    """adb.exe writes "\r\n" but counts only "\n" (seen on Windows with a Pixel 10)."""
    import io

    line = b"58080DLCR00481         device product:frankel model:Pixel_10 device:frankel transport_id:13"
    win = io.BytesIO(b"005c" + line + b"\r\n" + b"0000" + b"0017R58M123        offline\r\n")
    frames = []
    while True:
        head = win.read(4)
        if len(head) < 4:
            break
        frames.append(device_watch.read_frame(win, int(head, 16)))
    assert frames == [line + b"\n", b"", b"R58M123        offline\n"]
    assert parse_adb_devices(frames[0].decode().splitlines()) == [
        {"serial": "58080DLCR00481", "label": "Pixel 10", "state": "ready"}]
    # Linux adb (no "\r") reads the same, and a cut-off frame is end of stream.
    assert device_watch.read_frame(io.BytesIO(line + b"\n"), 0x5c) == line + b"\n"
    assert device_watch.read_frame(io.BytesIO(b"abc"), 10) is None


# --- usbmuxd Listen ---------------------------------------------------------

def _async_pymobiledevice3():
    usbmux = pytest.importorskip("pymobiledevice3.usbmux")
    if not asyncio.iscoroutinefunction(getattr(usbmux, "create_mux", None)):
        pytest.skip("needs pymobiledevice3 11.x (async API)")


class FakeUsbmuxd(threading.Thread):
    """Plist-protocol usbmuxd: answers ReadBUID and Listen, then pushes events."""

    def __init__(self, path):
        super().__init__(daemon=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(path)
        self.server.listen(5)
        self.listener = None
        self.ready = threading.Event()

    @staticmethod
    def _send(conn, tag, msg):
        body = plistlib.dumps(msg)
        conn.sendall(struct.pack("<LLLL", 16 + len(body), 1, 8, tag) + body)

    @staticmethod
    def _recv(conn):
        head = conn.recv(16)
        size, _, _, tag = struct.unpack("<LLLL", head)
        body = b""
        while len(body) < size - 16:
            body += conn.recv(size - 16 - len(body))
        return tag, plistlib.loads(body)

    def run(self):
        while True:
            conn, _ = self.server.accept()
            tag, msg = self._recv(conn)
            if msg["MessageType"] == "ReadBUID":
                self._send(conn, tag, {"BUID": "test"})
                conn.close()
            elif msg["MessageType"] == "Listen":
                self._send(conn, tag, {"MessageType": "Result", "Number": 0})
                self.listener = conn
                self.ready.set()

    def push(self, msg):
        self._send(self.listener, 0, msg)

    @staticmethod
    def attached(devid, serial, conn_type="USB"):
        return {"MessageType": "Attached", "DeviceID": devid,
                "Properties": {"SerialNumber": serial, "ConnectionType": conn_type}}


def test_usbmux_watcher_follows_attach_detach_and_trust(monkeypatch):
    _async_pymobiledevice3()
    path = os.path.join(tempfile.mkdtemp(), "usbmuxd")
    mux = FakeUsbmuxd(path)
    mux.start()
    monkeypatch.setenv("USBMUXD_SOCKET_ADDRESS", path)
    monkeypatch.setattr(device_watch, "UNTRUSTED_RECHECK", 0.2)

    trusted = {"AAA"}
    asked = []

    async def describe(dev):
        asked.append(dev.serial)
        if dev.serial in trusted:
            return {"Identifier": dev.serial, "ProductType": "iPhone10,1"}
        return {"Identifier": dev.serial, "_state": "untrusted"}

    w = device_watch.UsbmuxWatcher(describe)
    w.start()
    try:
        assert mux.ready.wait(5)
        mux.push(mux.attached(1, "AAA"))
        mux.push(mux.attached(2, "AAA", "Network"))   # same phone over Wi-Fi: listed once
        wait_for(lambda: w.snapshot() == [{"Identifier": "AAA", "ProductType": "iPhone10,1"}])

        mux.push(mux.attached(3, "BBB"))
        wait_for(lambda: len(w.snapshot() or []) == 2)
        assert {"Identifier": "BBB", "_state": "untrusted"} in w.snapshot()
        trusted.add("BBB")                          # user taps "Trust"
        wait_for(lambda: {"Identifier": "BBB", "ProductType": "iPhone10,1"} in w.snapshot())

        mux.push({"MessageType": "Detached", "DeviceID": 1})
        mux.push({"MessageType": "Detached", "DeviceID": 2})
        wait_for(lambda: [d["Identifier"] for d in w.snapshot()] == ["BBB"])
        # A trusted phone is described once, not on every update.
        assert asked.count("AAA") == 1
    finally:
        w.stop()


def test_usbmux_watcher_without_usbmuxd(monkeypatch):
    _async_pymobiledevice3()
    monkeypatch.setenv("USBMUXD_SOCKET_ADDRESS", os.path.join(tempfile.mkdtemp(), "missing"))

    async def describe(dev):
        raise AssertionError("no devices expected")

    w = device_watch.UsbmuxWatcher(describe)
    w.start()
    time.sleep(0.3)
    assert w.is_alive() and w.snapshot() == []
    w.stop()


# --- "Last scanned" time ----------------------------------------------------

def test_display_time_in_central(app, monkeypatch):
    from isdi.web.view import index

    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    try:
        assert index.display_time("2026-11-03 02:12:13") == "2026-11-02 20:12 CST"
        assert index.display_time("2026-07-01 17:00:00") == "2026-07-01 12:00 CDT"
        assert index.display_time(None) is None
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


# --- parse_dump.complexparse ------------------------------------------------

def test_complexparse_cuts_at_reported_line(monkeypatch):
    from isdi.scanner import parse_dump

    calls = []
    real = parse_dump.simpleparse
    monkeypatch.setattr(parse_dump, "simpleparse", lambda text: calls.append(1) or real(text))
    lines = [l + "\n" for l in ["Packages:", "  Package [a.b]:", "    userId=1",
                                 "  Package [c.d]:", "    userId=2", " bad indent", "tail"]]
    d = parse_dump.complexparse(lines)
    assert d["UNPARSED"] == lines[5:]
    assert "Packages:" in d
    # whole text, the prefix before the reported line, and the final parse;
    # no binary search.
    assert len(calls) == 3
