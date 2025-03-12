import os
import pickle
import traceback
from datetime import datetime
from enum import Enum
from operator import itemgetter
from pprint import pprint

from flask import (
    flash,
    jsonify,
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
    CONTEXT_PKL_FNAME,
    FAKE_APP_DATA,
    AccountCompromiseForm,
    AccountsUsedForm,
    AppInvestigationForm,
    AppSelectPageForm,
    ConsultDataTypes,
    DualUseForm,
    Pages,
    ScanForm,
    SetupForm,
    SpywareForm,
    StartForm,
    TAQForm,
    create_account_summary,
    create_app_summary,
    create_overall_summary,
    create_printout,
    get_screenshots,
    get_suspicious_apps,
    get_scan_data,
    load_json_data,
    reformat_verbose_apps,
    remove_unwanted_data,
    save_data_as_json,
    unpack_evidence_context,
)
from web import app

bootstrap = Bootstrap(app)

USE_PICKLE_FOR_SUMMARY = False
USE_FAKE_DATA = True

@app.route("/evidence/setup", methods={'GET', 'POST'})
def evidence_setup():

    form = SetupForm()

    if request.method == 'GET':

        # Load any data we already have
        setup_data = load_json_data(ConsultDataTypes.SETUP.value)
        if 'date' not in list(setup_data.keys()):
            setup_data['date'] = datetime.now()
        form.process(data=setup_data)

        context = dict(
            task = "evidence-setup",
            title=config.TITLE,
            form = form
        )

        return render_template('main.html', **context)
    
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            # save clean data
            save_data_as_json(clean_data, ConsultDataTypes.SETUP.value)

            return redirect(url_for('evidence_home'))
        

    return redirect(url_for('evidence_setup'))



@app.route("/evidence/home", methods={'GET'})
def evidence_home():

    consult_data = {
        "setup": load_json_data(ConsultDataTypes.SETUP.value),
        "taq": load_json_data(ConsultDataTypes.TAQ.value),
        "scans": load_json_data(ConsultDataTypes.SCANS.value),
        "accounts": load_json_data(ConsultDataTypes.ACCOUNTS.value)
    }

    context = dict(
        task = "evidence-home",
        title=config.TITLE,
        consultdata=consult_data,
    )

    return render_template('main.html', **context)


@app.route("/evidence/taq", methods={'GET', 'POST'})
def evidence_taq():

    form = TAQForm()

    # Load the form including any existing data
    if request.method == 'GET':

        # Load any data we already have
        taq_data = load_json_data(ConsultDataTypes.TAQ.value)
        form.process(data=taq_data)

        context = dict(
            task = "evidence-taq",
            form = form,
            title=config.TITLE,
            sessiondata = taq_data
        )

        return render_template('main.html', **context)


    # Submit the form
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            # save clean data
            save_data_as_json(clean_data, ConsultDataTypes.TAQ.value)

            return redirect(url_for('evidence_home'))
        
        elif not form.validate():
            print(traceback.format_exc())
            flash(form.errors, "error")
            return redirect(url_for('evidence_taq'))
        
    return redirect(url_for('evidence_taq'))



@app.route("/evidence/scan", methods={'GET'})
def evidence_scan_default():

    # place to save the num scans later if it becomes a pain to load it
    scans = load_json_data(ConsultDataTypes.SCANS.value)
    new_id = len(scans)

    return redirect(url_for('evidence_scan', id=new_id, step=1))

@app.route("/evidence/scan/<int:id>/<int:step>", methods={'GET', 'POST'})
def evidence_scan(id,step):

    ## TODO: Save, and load by, device ID

    class ScanSteps(Enum):
        DEVICEINFO = 1
        APPLIST = 2
        APPCHECKS = 3

    # load current scan data if there is any; otherwise create a fresh dict
    current_scan = dict()
    all_scan_data = load_json_data(ConsultDataTypes.SCANS.value)
    if len(all_scan_data) > id:
        current_scan = all_scan_data[id]

    if step == ScanSteps.DEVICEINFO.value:
        form = StartForm()

    if step == ScanSteps.APPLIST.value:
        form = AppSelectPageForm(apps=current_scan['all_apps'])

    if step == ScanSteps.APPCHECKS.value:
        check_apps = current_scan['check_apps']
        form = AppInvestigationForm(spyware=check_apps['spyware'],
                                    dualuse=check_apps['dualuse'],
                                    other=check_apps['other'])

    ### IF IT'S A GET:
    if request.method == 'GET':
        #if step == ScanSteps.APPLIST.value:
            #form.process(data=current_scan) # TODO fix??
        if step == ScanSteps.APPCHECKS.value:
            form.process(data=current_scan['check_apps'])

        context = dict(
            task = "evidence-scan",
            form = form,
            title=config.TITLE,
            scan_data = current_scan,
            step = step,
            id = id,
        )

        pprint(form.data)

        return render_template('main.html', **context)


    # Submit the form if it's a POST
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            ### STEP 1: Save device info, perform scan, and add list of apps
            if step == ScanSteps.DEVICEINFO.value:

                # create a new scan
                current_scan['device_type'] = clean_data["device_type"]
                current_scan['device_nickname'] = clean_data["device_nickname"]

                 # Ensure any previous screenshots have been removed before scan
                print("Removing files:")
                os.system("ls webstatic/images/screenshots/")
                os.system("rm webstatic/images/screenshots/*")

                try:
                    # Get app list
                    scan_data, suspicious_apps, other_apps = get_scan_data(clean_data["device_type"], clean_data["device_nickname"])

                    for i in range(len(suspicious_apps)):
                        suspicious_apps[i]["selected"] = True
                    for i in range(len(other_apps)): 
                        other_apps[i]["selected"] = False

                    # add scan data
                    current_scan['serial'] = scan_data['serial']
                    current_scan['model'] = scan_data['device_model']
                    current_scan['version'] = scan_data['device_version']
                    current_scan['manufacturer'] = scan_data['device_manufacturer']
                    current_scan['is_rooted'] = scan_data['is_rooted']
                    current_scan['rooted_reasons'] = scan_data['rooted_reasons']

                    # create app list 
                    current_scan['all_apps'] = suspicious_apps + other_apps
                    
                    # Create pre-filled check app list
                    spyware, dualuse = reformat_verbose_apps(suspicious_apps)
                    current_scan['check_apps'] = []
                    for app in spyware:
                        app["type"] = "spyware"
                        current_scan['check_apps'].append(app)
                    for app in dualuse:
                        app["type"] = "dualuse"
                        current_scan['check_apps'].append(app)

                    # add this scan to the scan data
                    if len(all_scan_data) == id:
                        all_scan_data.append(current_scan)
                    else:
                        # I don't think it'll get here but might as well
                        all_scan_data[id] = current_scan

                    save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)


                except Exception as e:
                    print(traceback.format_exc())
                    flash(e, "error")
                    return redirect(url_for('evidence_scan', id=id, step=step))

                return redirect(url_for('evidence_scan', id=id, step=step+1))
            
            


            ### STEP 2: Create the list of apps we want to investigate in phase 2
            if step == ScanSteps.APPLIST.value:

                selected_apps = [app for app in clean_data['apps'] if app['selected']]

                spyware = []
                dualuse = []
                other = []
                for app in selected_apps:
                    if 'spyware' in app['flags']:
                        spyware.append(app)
                    elif 'dual-use' in app['flags']:
                        dualuse.append(app)
                    else:
                        other.append(app)

                current_scan['check_apps'] = {"spyware": spyware, "dualuse": dualuse, "other": other}
                all_scan_data[id] = current_scan
                save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)
            
                return redirect(url_for('evidence_scan', id=id, step=step+1))

            ### STEP 3: Add investigation data for all of these apps, update session data
            if step == ScanSteps.APPCHECKS.value:
                
                current_scan['check_apps'] = clean_data
                all_scan_data[id] = current_scan
                save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)

                return redirect(url_for('evidence_home'))



@app.route("/evidence/account", methods={'GET'})
def evidence_account_default():

    # place to save the num scans later if it becomes a pain to load it
    accounts = load_json_data(ConsultDataTypes.ACCOUNTS.value)
    new_id = len(accounts)

    return redirect(url_for('evidence_account', id=new_id))

@app.route("/evidence/account/<int:id>", methods={'GET', 'POST'})
def evidence_account(id):

    current_account = dict()
    all_account_data = load_json_data(ConsultDataTypes.ACCOUNTS.value)
    if len(all_account_data) > id:
        current_account = all_account_data[id]
    
    form = AccountCompromiseForm()

    if request.method == 'GET':
        form.process(data=current_account)

        context = dict(
            task = "evidence-account",
            form = form,
            title=config.TITLE,
            sessiondata = current_account, # for now, don't load anything
        )

        return render_template('main.html', **context)

    # Submit the form if it's a POST
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_account_data = remove_unwanted_data(form.data)
            if clean_account_data['account_nickname'].strip() == '':
                clean_account_data['account_nickname'] = clean_account_data['platform']

            if len(all_account_data) <= id:
                all_account_data.append(clean_account_data)
            else:
                all_account_data[id] = clean_account_data

            save_data_as_json(all_account_data, ConsultDataTypes.ACCOUNTS.value)

            return redirect(url_for('evidence_home'))
        
        return redirect(url_for('evidence_account', id=id))
        





############################################
############################################
############################################


@app.route("/evidence/", methods={'GET'})
def evidence_default():
    session.clear()
    return redirect(url_for('evidence', step=1))

@app.route("/evidence/<int:step>", methods=['GET', 'POST'])
def evidence(step):

    # SAVE SESSION DATA INTO LOCAL VARIABLES

    spyware = []
    dualuse = []
    if 'apps' in session.keys():
        spyware = session['apps']['spyware']
        dualuse = session['apps']['dualuse']

    accounts=[]
    # have to do this step numbering better...
    if 'step{}'.format(Pages.ACCOUNTS_USED.value) in session.keys():
        accounts=[{"account_name": x} for x in session['step{}'.format(Pages.ACCOUNTS_USED.value)]['accounts_used']]

    pprint(session)

    # FORMS

    forms = {
        Pages.START.value: StartForm(),
        Pages.SCAN.value: ScanForm(),
        Pages.SPYWARE.value: SpywareForm(spyware_apps=spyware),
        Pages.DUALUSE.value: DualUseForm(dual_use_apps=dualuse),
        Pages.ACCOUNTS_USED.value: AccountsUsedForm(),
        Pages.ACCOUNT_COMP.value: AccountCompromiseForm(accounts=accounts),
    }

    form = forms.get(step, 1)

    # Submit the form if it's a POST
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            # for accounts used, have to reformat our data due to limitations with wtforms
            if step == Pages.ACCOUNTS_USED.value:
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

            # add clean data to the session data
            session['step{}'.format(step)] = clean_data

            # collect apps if we're on the scan step
            if step == Pages.SCAN.value:
                # Ensure any previous screenshots have been removed before scan
                print("Removing files:")
                os.system("ls webstatic/images/screenshots/")
                os.system("rm webstatic/images/screenshots/*")

                try:
                    verbose_apps = get_scan_data(session['step{}'.format(Pages.START.value)]['device_type'],
                                                       session['step{}'.format(Pages.START.value)]['name'])
                    spyware, dualuse = reformat_verbose_apps(verbose_apps)
                    session['apps'] = {"spyware": spyware, "dualuse": dualuse}

                except Exception as e:
                    if not USE_FAKE_DATA:
                        print(traceback.format_exc())
                        flash(str(e), "error")
                        return redirect(url_for('evidence', step=step))

                    # use fake data
                    session['apps'] = FAKE_APP_DATA

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

    if 'step{}'.format(Pages.START.value) in session.keys():
        context["device_owner"] = session['step{}'.format(Pages.START.value)]["name"]
        context["device"] = session['step{}'.format(Pages.START.value)]["device_type"]

    return render_template('main.html', **context)

@app.route('/evidence/summary', methods=['GET'])
def evidence_summary():
    
    context = unpack_evidence_context(session, task="evidencesummary")
    context["concerns"] = create_overall_summary(context, second_person=True)

    # TODO: load data into context


    return render_template('main.html', **context)

@app.route("/evidence/printout", methods=["GET"])
def evidence_printout():
    if USE_PICKLE_FOR_SUMMARY and os.path.isfile(CONTEXT_PKL_FNAME):
        context = pickle.load(open(CONTEXT_PKL_FNAME, 'rb'))
    else:
        context = unpack_evidence_context(session, task="evidencesummary")
        pickle.dump(context, open(CONTEXT_PKL_FNAME, 'wb'))

    # add datetime
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    context["current_time"] = dt_string

    # add screenshot directory
    context["screenshot_dir"] = config.SCREENSHOT_LOCATION

    # add fake screenshots
    # context["spyware"][0]['screenshots'] = ['step3-1.png']
    # context["dualuse"][1]['screenshots'] = ['step4-1.png']
    # context["accounts"][0]['screenshots'] = ['step6-1.png', 'step6-2.png']

    for app in context["spyware"]:
         summary, concerning = create_app_summary(app, spyware=True)
         app['summary'] = summary
         app['concerning'] = concerning
         app['screenshots'] = get_screenshots('spyware', app['app_name'], context["screenshot_dir"])

    for app in context["dualuse"]:
         summary, concerning = create_app_summary(app, spyware=False)
         app['summary'] = summary
         app['concerning'] = concerning
         app['screenshots'] = get_screenshots('dualuse', app['app_name'], context["screenshot_dir"])

    for account in context["accounts"]:
        access, ability, access_concern, ability_concern = create_account_summary(account)
        account["access_summary"] = access
        account["ability_summary"] = ability
        account["concerning"] = access_concern or ability_concern
        account['screenshots'] = get_screenshots('accounts', account['account_name'], context["screenshot_dir"])

    context["concerns"] = create_overall_summary(context)

    pprint(context)

    filename = create_printout(context)
    workingdir = os.path.abspath(os.getcwd())
    return send_from_directory(workingdir, filename)
