
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
    android_instructions,
    get_suspicious_apps,
    ios_instructions,
    remove_unwanted_data,
)
from web import app

bootstrap = Bootstrap(app)

@app.route("/evidence/", methods={'GET'})
def evidence_default():
    return redirect(url_for('evidence', step=1))


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

            if step == 4:
                # have to reformat our data due to limitations with wtforms
                accounts_used = []
                accounts_unused = []
                for k, v in clean_data.items():
                    if k != "submit" and v == True:
                        accounts_used.append(k)
                    elif k != "submit" :
                        accounts_unused.append(k)

                for k in accounts_unused:
                    clean_data.pop(k)

                clean_data['accounts_used'] = accounts_used
            
            session['step{}'.format(step)] = clean_data
            pprint(session)

            # collect apps if we need to
            if step == 1:
                try:
                    verbose_apps = get_suspicious_apps(clean_data['device_type'], clean_data['name'])
                    pprint(verbose_apps)
                    
                    session['apps'] = {"spyware": [], "dualuse": []}
                    for verbose_app in verbose_apps:
                        minimal_app = dict()

                        # the way ISDi does permissions is messed up rn, have to fix on the backend
                        minimal_app['permissions'] = [{"permission_name": x.capitalize()} for x in verbose_app['permissions']]

                        minimal_app['app_name'] = verbose_app['title']
                        if "dual-use" in verbose_app["flags"]:
                            session['apps']['dualuse'].append(minimal_app)
                        if "spyware" in verbose_app["flags"]:
                            session['apps']['spyware'].append(minimal_app)

                except Exception as e:
                    # for now, just do this
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
                    #print("ERROR: Please try again")
                    #return redirect(url_for('evidence', step=step))

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
        scanned=False,
        spyware=spyware,
        dualuse=dualuse,
        accounts=accounts
    )

    if "step1" in session.keys():
        context["device_owner"] = session["step1"]["name"]
        context["device"] = session["step1"]["device_type"]
    
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

