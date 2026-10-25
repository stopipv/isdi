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
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

FORBIDDEN_PAGE = """<!doctype html>
<title>ISDi - access denied</title>
<h1>Access denied</h1>
<p>Open ISDi with the link printed in the terminal where you started
<code>isdi run</code> (it ends with <code>?token=...</code>).</p>
"""


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

        url_token = request.args.get("token")
        if url_token is not None and _same(url_token, token):
            session["auth"] = token
            session["csrf"] = secrets.token_urlsafe(32)
            args = request.args.to_dict(flat=False)
            args.pop("token")
            query = ("?" + urlencode(args, doseq=True)) if args else ""
            return redirect(request.path + query)

        if not _same(session.get("auth"), token):
            return FORBIDDEN_PAGE, 403

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
