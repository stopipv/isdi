"""Start and stop PhoneView, the optional screen viewer, as a separate process.

PhoneView is a separate program and runs as a separate process. ISDi starts it
on demand, when a consultant presses the PhoneView button, and never runs more
than one copy. It stops when ISDi stops:

* a clean exit runs `stop()` (atexit);
* any other exit (the /kill route's SIGTERM, a crash) closes the pipe ISDi holds
  on PhoneView's stdin, and PhoneView's `--exit-on-stdin-eof` watchdog exits.

Install it into ISDi's own environment with `pip install "isdi-scanner[phoneview]"`
(Python 3.11+). Both pin the same pymobiledevice3 range, and ISDi runs it as
`python -m phoneview` with its own interpreter, so they always share one copy.

PhoneView listens on 127.0.0.1 only and requires its own per-run token. ISDi
derives that token from its own access token, so a signed-in ISDi user can be
handed a PhoneView link, while the PhoneView link never reveals ISDi's token.
"""

import atexit
import base64
import hashlib
import hmac
import importlib.util
import os
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlsplit

STARTUP_TIMEOUT = 20
LOOPBACK = ("127.0.0.1", "localhost", "::1", "[::1]")
DEFAULT_PUBLIC_PORT = 8443
STOP_WHEN_CLOSED = 30      # seconds after the PhoneView page closes


class PhoneViewError(RuntimeError):
    pass


def derive_token(access_token: str) -> str:
    digest = hmac.new(access_token.encode(), b"isdi-phoneview-v1", hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def public_url_for(host_header: str, configured: str = "") -> Optional[str]:
    """The PhoneView origin a browser on `host_header` should use.

    None means the browser is on this machine (use 127.0.0.1). Behind
    `tailscale serve` the Host header is the tailnet name (Tailscale keeps it),
    so PhoneView is served on the same name, port 8443 unless configured.
    """
    hostname = (urlsplit("//" + (host_header or "")).hostname or "").lower()
    if not hostname or hostname in LOOPBACK:
        return None
    if configured:
        return configured.rstrip("/")
    return f"https://{hostname}:{DEFAULT_PUBLIC_PORT}"


def _proxy_port(target: str) -> Optional[int]:
    """Local port of a `tailscale serve` proxy target: "http://127.0.0.1:6201", "localhost:6201", "6201"."""
    target = (target or "").strip()
    if target.isdigit():
        return int(target)
    parts = urlsplit(target if "://" in target else "http://" + target)
    if (parts.hostname or "") not in LOOPBACK:
        return None
    return parts.port


def tailscale_serve_problem(public_url: str, local_port: int, status_json: Optional[str] = None) -> Optional[str]:
    """Why a *.ts.net PhoneView address will not reach PhoneView, or None if it should.

    Reads `tailscale serve status --json`. None also when that can't be read
    (no tailscale CLI, not a ts.net address): ISDi only reports what it can see.
    """
    import json

    parts = urlsplit(public_url)
    host = (parts.hostname or "").lower()
    if not host.endswith(".ts.net"):
        return None
    port = parts.port or 443
    fix = f"tailscale serve --bg --https={port} http://127.0.0.1:{local_port}"
    if status_json is None:
        from isdi.scanner import runcmd

        p = runcmd.run(["tailscale", "serve", "status", "--json"], timeout=5)
        if p.returncode != 0:
            return None
        status_json = p.stdout
    try:
        status = json.loads(status_json or "{}") or {}
    except ValueError:
        return None
    configs = [status, *(status.get("Foreground") or {}).values()]
    targets = []
    for cfg in configs:
        handlers = ((cfg.get("Web") or {}).get(f"{host}:{port}") or {}).get("Handlers") or {}
        if "/" in handlers:
            targets.append(handlers["/"].get("Proxy", ""))
    if not targets:
        return (f"Nothing is published on port {port} of {host}, so the PhoneView tab "
                f"cannot open. On this computer, run:\n{fix}")
    if not any(_proxy_port(t) == local_port for t in targets):
        return (f"Port {port} of {host} forwards to {targets[0]}, not to PhoneView "
                f"(127.0.0.1:{local_port}). On this computer, run:\n{fix}")
    return None


class PhoneViewLauncher:
    def __init__(self, command: str, port: int, access_token: str, log_dir: Path,
                 screenshot_dir: Optional[Path] = None):
        self.command = command
        self.screenshot_dir = screenshot_dir
        self.port = port
        self.token = derive_token(access_token)
        self.log_dir = Path(log_dir)
        self.proc: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    def argv(self) -> Optional[List[str]]:
        """ISDI_PHONEVIEW_CMD, else PhoneView installed with ISDi, else `phoneview` on PATH."""
        if self.command:
            return shlex.split(self.command)
        if importlib.util.find_spec("phoneview") is not None:
            return [sys.executable, "-m", "phoneview"]   # same interpreter, same pymobiledevice3
        found = shutil.which("phoneview")
        return [found] if found else None

    def available(self) -> bool:
        return self.argv() is not None

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def link(self, base: str) -> str:
        return f"{base}/?token={self.token}"

    def start(self, public_url: Optional[str] = None) -> None:
        """Start PhoneView if needed; restart it if a new public URL must be allowed."""
        with self._lock:
            if self.running() and (public_url is None or public_url == self.public_url):
                return
            self._stop_locked()
            argv = self.argv()
            if argv is None:
                raise PhoneViewError('PhoneView is not installed. Run: pip install "isdi-scanner[phoneview]" '
                                     "(needs Python 3.11+), or set ISDI_PHONEVIEW_CMD.")
            argv += ["--port", str(self.port), "--no-browser", "--exit-on-stdin-eof",
                     "--audit-log", str(self.log_dir / "phoneview-audit.jsonl")]
            # PhoneView stops 30 s after its page is closed (a reload is fine) and then
            # deletes its screenshots; the next button press starts it again.
            argv += ["--stop-when-closed", str(STOP_WHEN_CLOSED)]
            if self.screenshot_dir is not None:
                argv += ["--screenshot-dir", str(self.screenshot_dir)]
            if public_url:
                argv += ["--public-origin", public_url]
            self.log_dir.mkdir(parents=True, exist_ok=True)
            log = open(self.log_dir / "phoneview.log", "ab")
            env = dict(os.environ, PHONEVIEW_TOKEN=self.token)
            env.pop("ISDI_ACCESS_TOKEN", None)   # PhoneView never needs ISDi's own token
            try:
                self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=log,
                                             stderr=subprocess.STDOUT, env=env)
            except OSError as exc:
                raise PhoneViewError(f"Could not start PhoneView: {exc}") from exc
            finally:
                log.close()
            self.public_url = public_url
            self._wait_listening()

    def _wait_listening(self) -> None:
        deadline = time.monotonic() + STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise PhoneViewError(
                    f"PhoneView exited during startup (code {self.proc.returncode}); "
                    f"see {self.log_dir / 'phoneview.log'}")
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.3).close()
                return
            except OSError:
                time.sleep(0.2)
        self._stop_locked()
        raise PhoneViewError(f"PhoneView did not start listening on port {self.port}")

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()               # PhoneView's watchdog exits on EOF
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except Exception:
            pass


_launcher: Optional[PhoneViewLauncher] = None


def get_launcher(config) -> PhoneViewLauncher:
    global _launcher
    if _launcher is None:
        _launcher = PhoneViewLauncher(config.PHONEVIEW_CMD, config.PHONEVIEW_PORT,
                                      config.ACCESS_TOKEN, config.logs_dir, config.screenshots_dir)
    return _launcher
