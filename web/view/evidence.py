import json
import os
from pprint import pprint

from flask import Flask, redirect, render_template, request, session, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired

import config
from web import app

bootstrap = Bootstrap(app)

yes_no_choices = [('y', 'Yes'), ('n', 'No'), ('u', 'Unsure')]
device_type_choices=[('android', 'Android'), ('ios', 'iOS')]

class StartForm(FlaskForm):
    title = "Welcome to <Name of tool>"
    name = StringField('Name', validators=[InputRequired()])
    device_type = SelectField('Device type:', choices=device_type_choices, validators=[InputRequired()])
    submit = SubmitField("Continue")

class SpywareForm(FlaskForm):
    title = "Spyware Check"
    knew_installed = SelectField('Did you know this app was installed?', choices=yes_no_choices, validators=[InputRequired()])
    installed = SelectField('Did install this app?', choices=yes_no_choices, validators=[InputRequired()])
    coerced = SelectField('Were you coerced into installing this app?', choices=yes_no_choices, validators=[InputRequired()])
    submit = SubmitField("Continue")

@app.route("/evidence/<int:step>", methods=['GET', 'POST'])
def evidence(step):
    """
    TODO: Evidence stuff!
    """

    forms = {
        1: StartForm(),
        2: SpywareForm(),
    }

    form = forms.get(step, 1)

    if request.method == 'POST':
        if form.is_submitted() and form.validate():
            session['step{}'.format(step)] = form.data
            if step < len(forms):
                # Redirect to next step
                return redirect(url_for('evidence', step=step+1))
            else:
                # Redirect to finish
                return redirect(url_for('evidence_summary'))
            
    # If form data for this step is already in the session, populate the form with it
    if 'step{}'.format(step) in session:
        form.process(data=session['step{}'.format(step)])

    context = dict(
        task = "evidence",
        progress =  int(step / len(forms) * 100),
        step = step,
        form = form,
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
        device_owner = "",
        device = "",
        scanned=False
    )
    
    return render_template('main.html', **context)

@app.route("/evidence/summary", methods=['GET'])
def evidence_summary():

    context = dict(
        task = "evidencesummary",
        device_primary_user=config.DEVICE_PRIMARY_USER,
        title=config.TITLE,
        device_owner = "",
        device = "",
        scanned=False,
        data = {},
    )

    for key in session.keys():
        if key.startswith('step'):
            context['data'].update(session[key])
    session.clear()

    return render_template('main.html', **context)

