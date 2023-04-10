
from collections import namedtuple
from pprint import pprint

from flask import redirect, render_template, request, session, url_for
from flask_bootstrap import Bootstrap

import config
from evidence_collection import (
    AccountCompromiseForm,
    AccountsUsedForm,
    DualUseForm,
    ScanForm,
    SpywareForm,
    StartForm,
    get_suspicious_apps,
    reformat_verbose_apps,
    remove_unwanted_data,
)
from web import app

bootstrap = Bootstrap(app)

@app.route("/evidence/", methods={'GET'})
def evidence_default():
    session.clear()
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
    # have to do this step numbering better...
    if 'step5' in session.keys():
        accounts=[{"account_name": x} for x in session['step5']['accounts_used']]

    forms = {
        1: StartForm(),
        2: ScanForm(),
        3: SpywareForm(spyware_apps=spyware),
        4: DualUseForm(dual_use_apps=dualuse),
        5: AccountsUsedForm(),
        6: AccountCompromiseForm(accounts=accounts),
    }

    form = forms.get(step, 1)

    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():
            clean_data = remove_unwanted_data(form.data)

            # for accounts used, have to reformat our data due to limitations with wtforms
            if step == 5:
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
            if step == 2:
                try:
                    verbose_apps = get_suspicious_apps(session['step1']['device_type'], session['step1']['name'])
                    spyware, dualuse = reformat_verbose_apps(verbose_apps)
                    session['apps'] = {"spyware": spyware, "dualuse": dualuse}

                except Exception as e:
                    print(e)
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
        spyware = [],
        dualuse = [],
        accounts = [],
    )

    if "step1" in session.keys():
        context['device_owner'] = session['step1']['name']
        context['device'] = session['step1']['device_type']

    if "step3" in session.keys():
        context['spyware'] = session['step3']['spyware_apps']

    if "step4" in session.keys():
        context['dualuse'] = session['step4']['dual_use_apps']

    if "step6" in session.keys():
        context['accounts'] = session['step6']['accounts']

    return render_template('main.html', **context)

