"""The PhoneView button: launcher lifecycle, URLs, and that the route is protected."""

import json
import shlex
import socket
import sys
import textwrap
import time

import pytest

from isdi import phoneview
from isdi.config import get_config
from isdi.phoneview import PhoneViewError, PhoneViewLauncher, derive_token, public_url_for

FAKE = textwrap.dedent("""
    # Stands in for `phoneview`: records argv/env, listens, exits on stdin EOF.
    import json, os, socket, sys, threading
    out, port = sys.argv[1], int(sys.argv[sys.argv.index("--port") + 1])
    with open(out, "w") as f:
        json.dump({"argv": sys.argv[2:], "token": os.environ.get("PHONEVIEW_TOKEN"),
                   "isdi_token": os.environ.get("ISDI_ACCESS_TOKEN")}, f)
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port)); s.listen()
    threading.Thread(target=lambda: [s.accept()[0].close() for _ in iter(int, 1)], daemon=True).start()
    sys.stdin.read()
""")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake(tmp_path):
    script = tmp_path / "fake_phoneview.py"
    script.write_text(FAKE)
    record = tmp_path / "record.json"
    command = " ".join(shlex.quote(p) for p in (sys.executable, str(script), str(record)))
    launcher = PhoneViewLauncher(command, free_port(), "isdi-access-token", tmp_path / "logs",
                                 tmp_path / "screenshots")
    yield launcher, record
    launcher.stop()


def test_token_is_derived_not_reused():
    token = derive_token("isdi-access-token")
    assert token == derive_token("isdi-access-token")
    assert token != "isdi-access-token" and len(token) >= 40
    assert token != derive_token("another-run")


@pytest.mark.parametrize("host,configured,expected", [
    ("127.0.0.1:6200", "", None),
    ("localhost:6200", "https://x.ts.net:8443", None),
    ("[::1]:6200", "", None),
    ("laptop.tail1.ts.net", "", "https://laptop.tail1.ts.net:8443"),
    ("Laptop.tail1.ts.net:443", "", "https://laptop.tail1.ts.net:8443"),
    ("laptop.tail1.ts.net", "https://pv.tail1.ts.net/", "https://pv.tail1.ts.net"),
])
def test_public_url(host, configured, expected):
    assert public_url_for(host, configured) == expected


def test_start_once_and_stop_on_stdin_close(fake):
    launcher, record = fake
    launcher.start()
    first = launcher.proc
    data = json.loads(record.read_text())
    assert data["token"] == launcher.token
    assert data["isdi_token"] is None                     # ISDi's own token is not passed on
    assert "--exit-on-stdin-eof" in data["argv"] and "--no-browser" in data["argv"]
    assert "--public-origin" not in data["argv"]
    # Screenshots go to ISDi's private temporary folder, and PhoneView stops (deleting
    # them) 30 s after its page is closed.
    argv = data["argv"]
    assert argv[argv.index("--screenshot-dir") + 1] == str(launcher.screenshot_dir)
    assert argv[argv.index("--stop-when-closed") + 1] == "30"
    launcher.start()
    assert launcher.proc is first                          # never a second copy
    launcher.stop()
    assert first.poll() == 0                               # exited on its own after stdin EOF
    assert not launcher.running()


def test_restart_to_allow_remote_origin(fake):
    launcher, record = fake
    launcher.start()
    first = launcher.proc
    launcher.start("https://laptop.tail1.ts.net:8443")
    assert launcher.proc is not first and first.poll() is not None
    argv = json.loads(record.read_text())["argv"]
    assert argv[argv.index("--public-origin") + 1] == "https://laptop.tail1.ts.net:8443"
    launcher.start(None)                                   # local use keeps the remote origin allowed
    assert launcher.public_url == "https://laptop.tail1.ts.net:8443"


def test_missing_or_failing_program(tmp_path):
    missing = PhoneViewLauncher("/no/such/phoneview", free_port(), "t", tmp_path)
    with pytest.raises(PhoneViewError):
        missing.start()
    crashing = PhoneViewLauncher(f"{shlex.quote(sys.executable)} -c 'raise SystemExit(3)'",
                                 free_port(), "t", tmp_path)
    with pytest.raises(PhoneViewError, match="exited during startup"):
        crashing.start()


# --- the web route --------------------------------------------------------------


@pytest.fixture
def authed(app):
    client = app.test_client()
    assert client.get(f"/?token={get_config().ACCESS_TOKEN}").status_code == 302
    with client.session_transaction() as s:
        csrf = s["csrf"]
    return client, csrf


def test_route_requires_login_and_csrf(app, authed, fake, monkeypatch):
    launcher, _ = fake
    monkeypatch.setattr(phoneview, "_launcher", launcher)
    assert app.test_client().post("/phoneview").status_code == 403
    client, csrf = authed
    assert client.post("/phoneview").status_code == 403
    assert not launcher.running()


def test_route_starts_and_redirects(authed, fake, monkeypatch):
    launcher, _ = fake
    monkeypatch.setattr(phoneview, "_launcher", launcher)
    client, csrf = authed
    r = client.post("/phoneview", data={"csrf_token": csrf})
    assert r.status_code == 303
    assert r.headers["Location"] == f"http://127.0.0.1:{launcher.port}/?token={launcher.token}"
    assert launcher.running()
    # A consultant arriving through tailscale serve gets the tailnet URL.
    import isdi.web.view.phoneview as view
    monkeypatch.setattr(view, "tailscale_serve_problem", lambda *a: None)
    r = client.post("/phoneview", data={"csrf_token": csrf},
                    headers={"X-Forwarded-Host": "laptop.tail1.ts.net"})
    assert r.headers["Location"] == f"https://laptop.tail1.ts.net:8443/?token={launcher.token}"


def test_csp_allows_the_redirect_to_phoneview(authed, fake, monkeypatch):
    """Browsers apply form-action to the 303 after POST /phoneview; with only
    'self' allowed the PhoneView tab stayed blank."""
    launcher, _ = fake
    monkeypatch.setattr(phoneview, "_launcher", launcher)
    client, _ = authed

    def form_action(**headers):
        csp = client.get("/", headers=headers).headers["Content-Security-Policy"]
        return next(d for d in csp.split("; ") if d.startswith("form-action")).split()[1:]

    assert form_action() == ["'self'", f"http://127.0.0.1:{launcher.port}"]
    assert form_action(**{"X-Forwarded-Host": "laptop.tail1.ts.net"}) == \
        ["'self'", "https://laptop.tail1.ts.net:8443"]


def test_csp_unchanged_without_phoneview(authed, tmp_path, monkeypatch):
    monkeypatch.setattr(phoneview, "_launcher", PhoneViewLauncher("", free_port(), "t", tmp_path))
    monkeypatch.setattr(PhoneViewLauncher, "available", lambda self: False)
    client, _ = authed
    assert "form-action 'self';" in client.get("/").headers["Content-Security-Policy"]


def test_route_explains_missing_tailscale_serve(authed, fake, monkeypatch):
    launcher, _ = fake
    monkeypatch.setattr(phoneview, "_launcher", launcher)
    import isdi.web.view.phoneview as view
    status = {"TCP": {"443": {"HTTPS": True}},
              "Web": {"laptop.tail1.ts.net:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:6200"}}}}}
    monkeypatch.setattr(view, "tailscale_serve_problem",
                        lambda url, port: phoneview.tailscale_serve_problem(url, port, json.dumps(status)))
    client, csrf = authed
    r = client.post("/phoneview", data={"csrf_token": csrf},
                    headers={"X-Forwarded-Host": "laptop.tail1.ts.net"})
    assert r.status_code == 503
    assert f"tailscale serve --bg --https=8443 http://127.0.0.1:{launcher.port}".encode() in r.data


def _serve(web, foreground=False):
    cfg = {"Web": web}
    return json.dumps({"Foreground": {"abc": cfg}} if foreground else cfg)


@pytest.mark.parametrize("status,problem", [
    (_serve({"h.t.ts.net:8443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:6201"}}}}), None),
    (_serve({"h.t.ts.net:8443": {"Handlers": {"/": {"Proxy": "localhost:6201"}}}}), None),
    (_serve({"h.t.ts.net:8443": {"Handlers": {"/": {"Proxy": "6201"}}}}, foreground=True), None),
    (_serve({"h.t.ts.net:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:6200"}}}}), "Nothing is published"),
    ("{}", "Nothing is published"),
    (_serve({"h.t.ts.net:8443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:9999"}}}}), "not to PhoneView"),
    ("not json", None),
])
def test_tailscale_serve_problem(status, problem):
    got = phoneview.tailscale_serve_problem("https://h.t.ts.net:8443", 6201, status)
    if problem is None:
        assert got is None
    else:
        assert problem in got and "tailscale serve --bg --https=8443 http://127.0.0.1:6201" in got


def test_tailscale_check_only_for_tailnet_names():
    assert phoneview.tailscale_serve_problem("https://192.168.1.5:8443", 6201, "{}") is None


def test_route_reports_missing_phoneview(authed, tmp_path, monkeypatch):
    monkeypatch.setattr(phoneview, "_launcher", PhoneViewLauncher("/no/such/phoneview", free_port(), "t", tmp_path))
    client, csrf = authed
    r = client.post("/phoneview", data={"csrf_token": csrf})
    assert r.status_code == 503 and b"Could not start PhoneView" in r.data


def test_button_rendered(authed, fake, monkeypatch):
    launcher, _ = fake
    monkeypatch.setattr(phoneview, "_launcher", launcher)
    client, _ = authed
    page = client.get("/").data.decode()
    assert 'action="/phoneview"' in page and "PhoneView" in page
    assert 'name="csrf_token"' in page


# --- which PhoneView ISDi runs ------------------------------------------------------


def test_command_priority(tmp_path, monkeypatch):
    monkeypatch.setattr(phoneview.shutil, "which", lambda name: "/usr/bin/phoneview")
    monkeypatch.setattr(phoneview.importlib.util, "find_spec", lambda name: None)
    launcher = PhoneViewLauncher("", 1, "t", tmp_path)
    assert launcher.argv() == ["/usr/bin/phoneview"]          # PATH when nothing else
    monkeypatch.setattr(phoneview.importlib.util, "find_spec", lambda name: object())
    # Installed with ISDi: same interpreter, so the same pymobiledevice3.
    assert launcher.argv() == [sys.executable, "-m", "phoneview"]
    launcher.command = "/opt/pv/bin/phoneview --verbose"
    assert launcher.argv() == ["/opt/pv/bin/phoneview", "--verbose"]   # explicit setting wins


def test_cli_status_when_missing(monkeypatch, tmp_path):
    from click.testing import CliRunner
    from isdi.cli import cli

    monkeypatch.setattr(phoneview, "_launcher", PhoneViewLauncher("", 1, "t", tmp_path))
    monkeypatch.setattr(phoneview.shutil, "which", lambda name: None)
    monkeypatch.setattr(phoneview.importlib.util, "find_spec", lambda name: None)
    result = CliRunner().invoke(cli, ["phoneview", "status"])
    assert result.exit_code == 0 and "isdi-scanner[phoneview]" in result.output
