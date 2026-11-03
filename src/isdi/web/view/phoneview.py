"""PhoneView button: start the screen viewer and send the consultant to it."""

from html import escape

from flask import redirect, request

from isdi.app import content_security_policy
from isdi.config import get_config
from isdi.phoneview import PhoneViewError, get_launcher, public_url_for, tailscale_serve_problem
from isdi.web import app

config = get_config()


@app.context_processor
def _phoneview_button():
    return {"phoneview_available": get_launcher(config).available()}


def _public_url():
    """PhoneView's address for this browser, or None for a browser on this machine."""
    # tailscale serve keeps the browser's Host header (and adds X-Forwarded-Host).
    host = request.headers.get("X-Forwarded-Host") or request.host
    return public_url_for(host, config.PHONEVIEW_PUBLIC_URL)


@app.after_request
def _allow_phoneview_redirect(resp):
    # Runs before isdi.app's header hook, which only fills in a missing CSP.
    if resp.mimetype == "text/html" and "Content-Security-Policy" not in resp.headers:
        launcher = get_launcher(config)
        if launcher.available():
            target = _public_url() or launcher.local_url()
            resp.headers["Content-Security-Policy"] = content_security_policy([target])
    return resp


@app.route("/phoneview", methods=["POST"])
def open_phoneview():
    # Reached only by a signed-in session with a valid CSRF token (isdi.app).
    launcher = get_launcher(config)
    public = _public_url()
    try:
        launcher.start(public)
    except PhoneViewError as exc:
        return _unavailable(str(exc))
    if public:
        problem = tailscale_serve_problem(public, launcher.port)
        if problem:
            return _unavailable(
                problem,
                "The tailnet access rule must also allow this port "
                "(see remote.md). Then press the PhoneView button again.",
            )
    return redirect(launcher.link(public or launcher.local_url()), code=303)


def _unavailable(message, hint=""):
    body = "<br>".join(escape(line) for line in message.splitlines())
    extra = f"<p>{escape(hint)}</p>" if hint else ""
    return (
        "<!doctype html><title>PhoneView unavailable</title><h1>PhoneView unavailable</h1>"
        f"<p style='font-family:monospace'>{body}</p>{extra}",
        503,
    )
