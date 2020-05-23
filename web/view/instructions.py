import config
from flask import render_template, request, session
from web import app

@app.route('/instruction', methods=['GET'])
def instruction():
    return render_template('main.html', task="instruction",
                           device_primary_user=config.DEVICE_PRIMARY_USER,
                           title=config.TITLE)


