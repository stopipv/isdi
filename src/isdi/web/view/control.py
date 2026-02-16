from isdi.web import app
from flask import request


@app.route("/kill", methods=["POST", "GET"])
def killme():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()
    return "The app has been closed!"
