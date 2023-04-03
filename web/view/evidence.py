
from collections import namedtuple
from pprint import pprint

from flask import redirect, render_template, request, session, url_for
from flask_bootstrap import Bootstrap

import config
from evidence_collection import (
    AccountCompromiseForm,
    AccountsUsedForm,
    DualUseForm,
    SpywareForm,
    StartForm,
    remove_unwanted_data,
)
from web import app

bootstrap = Bootstrap(app)

@app.route("/evidence/<int:step>", methods=['GET', 'POST'])
def evidence(step):
    """
    TODO: Evidence stuff!
    """ 
    spyware = []
    dualuse = []
    if 'apps' in session.keys():
        spyware = session['apps']['spyware']
        dualuse = session['apps']['dualuse']

    accounts=[]
    if 'step4' in session.keys():
        accounts=[{"account_name": x} for x in session['step4']['accounts_used']]

    forms = {
        1: StartForm(),
        2: SpywareForm(spyware_apps=spyware),
        3: DualUseForm(dual_use_apps=dualuse),
        4: AccountsUsedForm(),
        5: AccountCompromiseForm(accounts=accounts),
    }

    form = forms.get(step, 1)

    if request.method == 'POST':
        if form.is_submitted() and form.validate():
            clean_data = remove_unwanted_data(form.data)
            session['step{}'.format(step)] = clean_data

            # collect apps if we need to
            if step == 1:
                session['apps'] = {
                    "spyware": [{"app_name": "MSpy"}],
                    "dualuse": [{"app_name": "Snapchat", 
                                "permissions": [
                                    {"permission_name": "Location"},
                                    {"permission_name": "Camera"},
                                ]}, 
                                {"app_name": "FindMy", 
                                "permissions": [
                                    {"permission_name": "Location"},
                                ]}]
                }

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

