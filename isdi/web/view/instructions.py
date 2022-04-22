import isdi.config
from flask import render_template, request, session
from isdi.web import app

@app.route('/instruction', methods=['GET'])
def instruction():
    return render_template('main.html', task="instruction",
                           device_primary_user=isdi.config.DEVICE_PRIMARY_USER,
                           title=isdi.config.TITLE)


