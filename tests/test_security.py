"""Regression tests for the 1.0.9 security fixes."""

import pytest

from isdi.config import get_config
from isdi.scanner import (
    AndroidScanner,
    redact_emails,
    sanitize_description,
    valid_appid,
)
from isdi.scanner import runcmd


# --- Device commands --------------------------------------------------------


def test_run_never_uses_a_shell():
    p = runcmd.run(["echo", "$(id)", ";", "touch", "/tmp/isdi-pwned"])
    assert p.returncode == 0
    assert p.stdout.strip() == "$(id) ; touch /tmp/isdi-pwned"


def test_run_missing_binary_does_not_raise():
    p = runcmd.run(["isdi-no-such-binary"])
    assert p.returncode == 127
    assert runcmd.output(["isdi-no-such-binary"]) == ""


@pytest.mark.parametrize(
    "appid,ok",
    [
        ("com.example.app", True),
        ("com.example_app-2", True),
        ("com.apple.mobilenotes", True),
        ("", False),
        ("com.x; reboot", False),
        ("$(id)", False),
        ("-k", False),
        ("../../etc/passwd", False),
    ],
)
def test_valid_appid(appid, ok):
    assert valid_appid(appid) is ok


def test_uninstall_rejects_bad_appid(monkeypatch):
    sc = AndroidScanner()
    monkeypatch.setattr(runcmd, "run", lambda *a, **k: pytest.fail("ran a command"))
    monkeypatch.setattr(runcmd, "output", lambda *a, **k: pytest.fail("ran a command"))
    assert sc.uninstall("serial", "com.x; reboot") is False


def test_dumps_are_keyed_by_serial(monkeypatch):
    sc = AndroidScanner()
    assert sc.dump_path("serial-a") != sc.dump_path("serial-b")
    # Reading a dump never talks to the device, and a missing dump is None
    # rather than another device's dump.
    monkeypatch.setattr(sc, "_dump_phone", lambda s: pytest.fail("dumped device"))
    assert sc._get_dump("serial-b") is None


# --- Redaction and sanitizing -----------------------------------------------


def test_redact_emails():
    out = redact_emails(
        "account bob.smith@example.co.uk a@b.museum "
        "/data/data/com.google.android.gms/databases/alice_gmail.com.db"
    )
    assert "bob.smith" not in out and "a@b.museum" not in out
    assert "alice" not in out
    assert "<db_email>.db" in out


def test_sanitize_description_keeps_only_br():
    out = sanitize_description('Hi<br>there<BR /><script>alert(1)</script><img src=x onerror="x">')
    assert "<br>" in out
    assert "<script" not in out and "<img" not in out
    assert "&lt;script&gt;" in out


# --- Web UI -------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    from isdi.app import create_app

    config = get_config("test")
    app = create_app(config)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authed(client):
    token = get_config().ACCESS_TOKEN
    r = client.get(f"/instruction?token={token}")
    assert r.status_code == 302
    assert "token" not in r.headers["Location"]
    with client.session_transaction() as s:
        csrf = s["csrf"]
    return client, csrf


def test_default_host_is_loopback():
    assert get_config().host == "127.0.0.1"


def test_routes_require_token(client):
    assert client.get("/instruction").status_code == 403
    assert client.get("/instruction?token=wrong").status_code == 403
    assert client.post("/kill").status_code == 403


def test_token_grants_access(authed):
    client, _ = authed
    r = client.get("/instruction")
    assert r.status_code == 200
    assert "Content-Security-Policy" in r.headers
    assert r.headers["X-Frame-Options"] == "DENY"


def test_static_files_do_not_need_token(client):
    assert client.get("/static/myjscript.js").status_code == 200


def test_post_requires_csrf(authed):
    client, csrf = authed
    assert client.post("/delete_device", data={"serial": "x"}).status_code == 403
    r = client.post("/delete_device", data={"serial": "x"}, headers={"X-CSRFToken": "bad"})
    assert r.status_code == 403
    r = client.post("/delete_device", data={"serial": "x", "csrf_token": csrf})
    assert r.status_code == 400  # past CSRF; rejected for the invalid serial


@pytest.mark.parametrize("path", ["/kill", "/delete/app/1", "/privacy/android/account"])
def test_state_changing_routes_reject_get(authed, path):
    client, _ = authed
    assert client.get(path).status_code == 405


def test_live_scan_requires_post(authed):
    client, _ = authed
    with client.session_transaction() as s:
        s["clientid"] = "test-client"
    r = client.get("/scan?device=test&device_owner=x&devid=testdevice1")
    assert r.status_code == 302


def test_scan_start_rejects_unknown_serial(authed):
    client, csrf = authed
    with client.session_transaction() as s:
        s["clientid"] = "test-client"
    r = client.post(
        "/scan/start",
        data={"device": "test", "device_owner": "x", "devid": "$(reboot)"},
        headers={"X-CSRFToken": csrf},
    )
    assert r.status_code == 400


def test_privacy_rejects_unknown_serial(authed):
    client, csrf = authed
    r = client.post(
        "/privacy/test/account",
        data={"serial": "evil; reboot"},
        headers={"X-CSRFToken": csrf},
    )
    assert r.status_code == 400


def test_details_rejects_unknown_serial(authed):
    client, _ = authed
    r = client.get("/details/app/test?appId=com.example&serial=not-connected")
    assert r.status_code == 400
    r = client.get("/details/app/test?appId=$(id)&serial=testdevice1")
    assert r.status_code == 400


def test_screenshot_route_only_serves_screenshot_names(authed, tmp_path):
    client, _ = authed
    screenshots = get_config().screenshots_dir
    (screenshots / "0123456789abcdef.png").write_bytes(b"\x89PNG")
    r = client.get("/privacy/screenshot/0123456789abcdef.png")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    assert client.get("/privacy/screenshot/..%2Fpii.key").status_code == 404
    assert client.get("/privacy/screenshot/tmp.png").status_code == 404
