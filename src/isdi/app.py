"""Flask application factory"""

import hmac
import secrets
from pathlib import Path
from time import perf_counter
from urllib.parse import urlencode
from flask import Flask, abort, redirect, request, session
from flask_sqlalchemy import SQLAlchemy

__all__ = ["create_app"]

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

# Inline <script> blocks and on* handlers are still used by the templates,
# hence 'unsafe-inline'; everything else is restricted to this origin.
def content_security_policy(form_targets=()) -> str:
    """ISDi's CSP. form_targets: extra origins a form POST may redirect to.

    Browsers apply form-action to the redirect after a form POST too, so the
    PhoneView button (POST /phoneview -> 303 to PhoneView's port) needs
    PhoneView's origin listed here, or the new tab silently stays blank.
    """
    form_action = " ".join(["'self'", *form_targets])
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'none'; "
        f"form-action {form_action}; "
        "frame-ancestors 'none'"
    )


CONTENT_SECURITY_POLICY = content_security_policy()

LOGIN_PATH = "/login"

LOGIN_PAGE = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ISDi - sign in</title>
<style>
  body {{ font-family: sans-serif; background: #f4f6f8; margin: 0; }}
  main {{ max-width: 460px; margin: 12vh auto; background: #fff; padding: 28px;
         border: 1px solid #d8dee4; border-radius: 14px; }}
  h1 {{ font-size: 1.3em; color: #156c2f; margin-top: 0; }}
  .err {{ color: #b00020; font-weight: bold; }}
  input[type=password] {{ width: 100%; box-sizing: border-box; font: 1.1em monospace;
         padding: 10px; margin: 8px 0 14px; border: 1px solid #999; border-radius: 6px; }}
  button {{ font-size: 1em; padding: 8px 18px; background: #156c2f; color: #fff;
           border: 0; border-radius: 6px; cursor: pointer; }}
  p.small {{ color: #555; font-size: .9em; }}
</style>
<main>
  <h1>ISDi needs its access token</h1>
  {error}
  <form method="post" action="{login_path}">
    <input type="hidden" name="next" value="{next}">
    <label for="token">Paste the access token shown in the terminal where ISDi runs:</label>
    <input type="password" id="token" name="token" autocomplete="off" autofocus required>
    <button type="submit">Sign in</button>
  </form>
  <p class="small">ISDi has just printed the token again in its terminal,
  in a box labelled <b>ISDi ACCESS TOKEN</b>. It changes every time ISDi starts.</p>
</main>
"""

_last_banner = 0.0


def token_banner(token: str, link: str = "") -> str:
    """The access token, framed so it is easy to find and copy in a terminal."""
    import sys

    color = sys.stderr.isatty()
    bold = (lambda t: f"\033[1;33m{t}\033[0m") if color else (lambda t: t)
    rule = "=" * max(60, len(token) + 8)
    lines = ["", rule, "  ISDi ACCESS TOKEN  (paste it into the browser's sign-in page)", "",
             "    " + bold(token), ""]
    if link:
        lines.append(f"  or open: {link}")
    lines += [rule, ""]
    return "\n".join(lines)


def _announce_token(token: str, min_interval: float = 10.0) -> None:
    """Re-print the token banner when someone reaches the sign-in page (like Jupyter)."""
    import sys
    import time

    global _last_banner
    now = time.monotonic()
    if now - _last_banner < min_interval:
        return
    _last_banner = now
    proto = request.headers.get("X-Forwarded-Proto") or request.scheme
    host = request.headers.get("X-Forwarded-Host") or request.host
    print(token_banner(token, f"{proto}://{host}/?token={token}"), file=sys.stderr, flush=True)


def _safe_next(target: str) -> str:
    """Only local paths: never redirect a sign-in to another site."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    return target


def _login_page(token: str, next_path: str, error: str = ""):
    from html import escape

    _announce_token(token)
    body = LOGIN_PAGE.format(
        error=f'<p class="err">{escape(error)}</p>' if error else "",
        login_path=LOGIN_PATH,
        next=escape(_safe_next(next_path), quote=True),
    )
    return body, 403


def _same(a, b) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(str(a), str(b))


def install_security(app, token: str) -> None:
    """Require the per-run token on every route and a CSRF token on writes.

    The browser is opened at /?token=<token>. A matching token marks the
    session as authenticated for this run and gets a fresh CSRF token; the
    token is then stripped from the URL by a redirect. Static files are
    exempt because they contain nothing device- or client-specific.
    """
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
    )

    @app.before_request
    def _check_access():
        if request.endpoint == "static":
            return None

        args = request.args.to_dict(flat=False)
        url_token = args.pop("token", [None])[0]
        query = ("?" + urlencode(args, doseq=True)) if args else ""
        if url_token is not None and _same(url_token, token):
            session["auth"] = token
            session["csrf"] = secrets.token_urlsafe(32)
            return redirect(request.path + query)

        # The sign-in form: the token is POSTed, so it stays out of URLs and logs.
        if request.path == LOGIN_PATH and request.method == "POST":
            next_path = request.form.get("next", "/")
            if _same(request.form.get("token", "").strip(), token):
                session["auth"] = token
                session["csrf"] = secrets.token_urlsafe(32)
                return redirect(_safe_next(next_path), code=303)
            return _login_page(token, next_path, "Invalid token. Copy it again from the terminal.")

        if not _same(session.get("auth"), token):
            if request.method in SAFE_METHODS:
                error = "Invalid token." if url_token is not None else ""
                return _login_page(token, request.path + query, error)
            abort(403, "Not signed in.")

        if request.method not in SAFE_METHODS:
            sent = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
            if not _same(sent, session.get("csrf")):
                abort(403, "Missing or invalid CSRF token. Reload the page and try again.")
        return None

    @app.context_processor
    def _csrf_token():
        return {"csrf_token": lambda: session.get("csrf", "")}

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        # Keep the ?token= URL out of Referer headers.
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp


def create_app(config=None):
    """Create and configure Flask application"""
    from isdi.config import get_config

    if config is None:
        config = get_config()

    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "web" / "templates"),
        static_folder=str(Path(__file__).parent / "web" / "static"),
    )

    # Configuration
    app.config["SECRET_KEY"] = config.FLASK_SECRET
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{config.database_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Store config in app
    app.config["ISDI_CONFIG"] = config

    install_security(app, config.ACCESS_TOKEN)

    # Initialize extensions
    from isdi.web import sa

    db_init_started = perf_counter()
    sa.init_app(app)

    try:
        from isdi.scanner.db import init_db

        init_db(app, sa, force=config.TEST)
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    else:
        print(f"Database init: {perf_counter() - db_init_started:.2f}s")

    # Register routes
    routes_started = perf_counter()
    try:
        from isdi.web import init_routes

        init_routes(app)
    except Exception as e:
        print(f"Warning: Could not register routes: {e}")

        # Create a simple test route
        @app.route("/")
        def index():
            return f"""
            <html>
            <head><title>ISDI</title></head>
            <body>
                <h1>ISDi - Stalkerware Scanner</h1>
                <p>Server is running but web routes are not fully initialized.</p>
                <p>Data directory: {config.dirs['data']}</p>
                <p>Database: {config.database_path}</p>
            </body>
            </html>
            """
    else:
        print(f"Route import/init: {perf_counter() - routes_started:.2f}s")

    return app
