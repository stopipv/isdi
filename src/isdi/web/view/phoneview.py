"""PhoneView button: start the screen viewer and send the consultant to it."""

from html import escape

from flask import redirect, request

from isdi.config import get_config
from isdi.phoneview import PhoneViewError, get_launcher, public_url_for
from isdi.web import app

config = get_config()


@app.context_processor
def _phoneview_button():
    return {"phoneview_available": get_launcher(config).available()}


@app.route("/phoneview", methods=["POST"])
def open_phoneview():
    # Reached only by a signed-in session with a valid CSRF token (isdi.app).
    launcher = get_launcher(config)
    # tailscale serve keeps the browser's Host header (and adds X-Forwarded-Host).
    host = request.headers.get("X-Forwarded-Host") or request.host
    public = public_url_for(host, config.PHONEVIEW_PUBLIC_URL)
    try:
        launcher.start(public)
    except PhoneViewError as exc:
        return (
            "<!doctype html><title>PhoneView unavailable</title><h1>PhoneView unavailable</h1>"
            f"<p>{escape(str(exc))}</p>",
            503,
        )
    return redirect(launcher.link(public or launcher.local_url()), code=303)
