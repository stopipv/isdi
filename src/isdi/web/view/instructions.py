from isdi.config import get_config
from flask import render_template, request, session
from isdi.web import app
import os

config = get_config()


@app.route("/instruction", methods=["GET"])
def instruction():
    return render_template(
        "main.html",
        task="instruction",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
        is_termux=bool(os.environ.get("PREFIX")),
        is_debug=config.DEBUG,
    )
