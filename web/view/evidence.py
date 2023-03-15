from flask import render_template, request

import config
from web import app


@app.route("/evidence", methods=['GET'])
def evidence():
    """
    TODO: Evidence stuff!
    """
    return render_template(
        'main.html', task="evidence",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE
    )
