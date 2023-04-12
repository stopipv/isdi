
import os
from datetime import datetime
from pprint import pprint

from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_bootstrap import Bootstrap

import config
from evidence_collection import (
    AccountCompromiseForm,
    AccountsUsedForm,
    DualUseForm,
    ScanForm,
    SpywareForm,
    StartForm,
    create_printout,
    get_suspicious_apps,
    reformat_verbose_apps,
    remove_unwanted_data,
    unpack_evidence_context,
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

    
    pprint(session)

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

            # collect apps if we need to
            if step == 2:
                try:
                    verbose_apps = get_suspicious_apps(session['step1']['device_type'], session['step1']['name'])
                    spyware, dualuse = reformat_verbose_apps(verbose_apps)
                    session['apps'] = {"spyware": spyware, "dualuse": dualuse}

                except Exception as e:
                    #print(traceback.format_exc())
                    #flash(str(e), "error")
                    #return redirect(url_for('evidence', step=step))
                    # for now, just do this
                    session['apps'] = {
                    "spyware": [{"app_name": "MSpy", 
                                 "description": "mSpy is a computer security for parental control. Helps parents to give attention to their children online activities. It checks WhatsApp, Facebook, massage and snapchat messages. mSpy is a computer security for parental control.",
                                 }],
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
        scanned=False,
        spyware=spyware,
        dualuse=dualuse,
        accounts=accounts
    )

    if "step1" in session.keys():
        context["device_owner"] = session["step1"]["name"]
        context["device"] = session["step1"]["device_type"]
    
    return render_template('main.html', **context)

@app.route('/evidence/summary', methods=['GET'])
def evidence_summary():
    context = unpack_evidence_context(session, task="evidencesummary")
    return render_template('main.html', **context)

@app.route("/evidence/printout", methods=["GET"])
def evidence_printout():
    context = unpack_evidence_context(session)

    # add datetime
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    context["current_time"] = dt_string

    context["screenshot_dir"] = config.SCREENSHOT_LOCATION

    pprint(context)

    filename = create_printout(context)
    workingdir = os.path.abspath(os.getcwd())
    return send_from_directory(workingdir, filename)