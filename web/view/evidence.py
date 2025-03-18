import json
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
from evidence_collection import (  # create_account_summary,; create_app_summary,
    CONTEXT_PKL_FNAME,
    FAKE_APP_DATA,
    AccountCompromiseForm,
    AccountInvestigation,
    AppInfo,
    AppInvestigationForm,
    AppSelectPageForm,
    CheckApps,
    ConsultationData,
    ConsultDataTypes,
    ConsultSetupData,
    DualUseForm,
    Pages,
    ScanData,
    ScanForm,
    SetupForm,
    SpywareForm,
    StartForm,
    TAQData,
    TAQForm,
    create_overall_summary,
    create_printout,
    get_scan_by_ser,
    get_scan_data,
    get_screenshots,
    load_json_data,
    reformat_verbose_apps,
    remove_unwanted_data,
    save_data_as_json,
    unpack_evidence_context,
    update_scan_by_ser,
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
        setup_data = ConsultSetupData(**load_json_data(ConsultDataTypes.SETUP.value))

        if setup_data.date.strip() == "":
            setup_data.date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        form.process(data=setup_data.to_dict())

        context = dict(
            task = "evidence-setup",
            title=config.TITLE,
            form = form
        )

        return render_template('main.html', **context)
    
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():
            # clean up and save data
            clean_data = remove_unwanted_data(form.data)
            setup_data = ConsultSetupData(**clean_data)

            # save clean data
            save_data_as_json(setup_data, ConsultDataTypes.SETUP.value)


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
        taq_data = TAQData(**load_json_data(ConsultDataTypes.TAQ.value))
        
        form.process(data=taq_data.to_dict())


        context = dict(
            task = "evidence-taq",
            form = form,
            title=config.TITLE,
            sessiondata = taq_data.to_dict()
        )

        return render_template('main.html', **context)


    # Submit the form
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up data
            clean_data = remove_unwanted_data(form.data)

            # load data as class
            taq_data = TAQData(**clean_data)

            # save clean data
            save_data_as_json(taq_data, ConsultDataTypes.TAQ.value)

            return redirect(url_for('evidence_home'))
        
        elif not form.validate():
            print(traceback.format_exc())
            flash(form.errors, "error")
            return redirect(url_for('evidence_taq'))
        
    return redirect(url_for('evidence_taq'))



@app.route("/evidence/scan", methods={'GET', 'POST'})
def evidence_scan_start():

    # always assume we are starting with a fresh scan
    all_scan_data = [ScanData(**scan) for scan in 
                     load_json_data(ConsultDataTypes.SCANS.value)]
    current_scan = ScanData()
    form = StartForm()

    if request.method == "GET":
        context = dict(
            task = "evidence-scan",
            form = form,
            title=config.TITLE,
            scan_data = current_scan.to_dict(),
            step = 1,
            id = 0,
        )
        pprint(form.data)

        return render_template('main.html', **context)

    if request.method == "POST":
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            # Ensure any previous screenshots have been removed before scan
            print("Removing files:")
            os.system("ls webstatic/images/screenshots/")
            os.system("rm webstatic/images/screenshots/*")

            try:
                # Get app list
                scan_data, suspicious_apps_dict, other_apps_dict = get_scan_data(clean_data["device_type"], clean_data["device_nickname"])

                # fill in the /investigate/ marker for suspicious apps
                for i in range(len(suspicious_apps_dict)):
                    suspicious_apps_dict[i]["investigate"] = True

                all_apps = suspicious_apps_dict + other_apps_dict
                
                # Create current scan object with this info
                current_scan = ScanData(scan_id=len(all_scan_data), 
                                        **clean_data, 
                                        **scan_data,
                                        all_apps=all_apps,
                                        selected_apps=suspicious_apps_dict)
                
                pprint(current_scan.__dict__)
                
                current_scan.id = len(all_scan_data)
                all_scan_data.append(current_scan)


            except Exception as e:
                print(traceback.format_exc())
                flash(e, "error")
                return redirect(url_for('evidence_scan_start', step=2))

            
            save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)
            return redirect(url_for('evidence_scan_select', ser=current_scan.serial))

    return redirect(url_for('evidence_scan_start'))



@app.route("/evidence/scan/select/<string:ser>", methods={'GET', 'POST'})
def evidence_scan_select(ser):

    # load all scans
    all_scan_data = [ScanData(**scan) for scan in 
                     load_json_data(ConsultDataTypes.SCANS.value)]
    # get the right scan by serial number
    current_scan = get_scan_by_ser(ser, all_scan_data)
    assert current_scan.serial == ser

    # fill form
    form = AppSelectPageForm(apps=[app.to_dict() for app in current_scan.all_apps])

     ### IF IT'S A GET:
    if request.method == 'GET':
        #form.process(data=current_scan.to_dict())

        context = dict(
            task = "evidence-scan",
            form = form,
            title=config.TITLE,
            all_apps = [app.to_dict() for app in current_scan.all_apps],
            step = 2
        )

        return render_template('main.html', **context)

    # Submit the form if it's a POST
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            # get selected apps from the form data
            selected_apps = [app for app in clean_data['apps'] if app['investigate']]
            pprint(selected_apps)
            pprint("SELECTED APPS")

            # update the current scan data and save it as the most recent scan
            current_scan.selected_apps = [AppInfo(**app) for app in selected_apps]
            all_scan_data = update_scan_by_ser(current_scan, all_scan_data)

            # save this updated data
            save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)
        
            return redirect(url_for('evidence_scan_investigate', ser=ser))
        


@app.route("/evidence/scan/investigate/<string:ser>", methods={'GET', 'POST'})
def evidence_scan_investigate(ser):

    # load all scans
    all_scan_data = [ScanData(**scan) for scan in 
                     load_json_data(ConsultDataTypes.SCANS.value)]

    # get the right scan by serial number
    current_scan = get_scan_by_ser(ser, all_scan_data)
    assert current_scan.serial == ser

    pprint([app.to_dict() for app in current_scan.selected_apps])
    pprint("INPUTTED INTO THE INVESTIGATION FORM")

    # get apps to investigate from the scan data
    form = AppInvestigationForm(selected_apps=[app.to_dict() for app in current_scan.selected_apps])

    ### IF IT'S A GET:
    if request.method == 'GET':

        context = dict(
            task = "evidence-scan",
            form = form,
            title=config.TITLE,
            scan_data = current_scan.to_dict(),
            step = 3
        )

        return render_template('main.html', **context)


    # Submit the form if it's a POST
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # clean up the submitted data
            clean_data = remove_unwanted_data(form.data)

            # update the current scan data and save it
            current_scan.selected_apps = [AppInfo(**app) for app in clean_data["selected_apps"]]
            all_scan_data = update_scan_by_ser(current_scan, all_scan_data)

            #  save this updated data
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

    all_account_data_json = load_json_data(ConsultDataTypes.ACCOUNTS.value)
    all_account_data = [AccountInvestigation(**account) for account in all_account_data_json]

    current_account = AccountInvestigation(account_id=id)

    if len(all_account_data) > id:
        current_account = all_account_data[id]
    
    form = AccountCompromiseForm()

    if request.method == 'GET':
        form.process(data=current_account.to_dict())

        context = dict(
            task = "evidence-account",
            form = form,
            title=config.TITLE,
            sessiondata = current_account.to_dict()
            # for now, don't load anything
        )

        return render_template('main.html', **context)

    # Submit the form if it's a POST
    if request.method == 'POST':
        pprint(form.data)
        if form.is_submitted() and form.validate():

            # save data in class
            account_investigation = AccountInvestigation(**form.data, account_id=id)

            # add it to the account data
            if len(all_account_data) <= id:
                all_account_data.append(account_investigation)
            else:
                all_account_data[id] = account_investigation

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

    consult_data = ConsultationData(
        setup=load_json_data(ConsultDataTypes.SETUP.value),
        taq=load_json_data(ConsultDataTypes.TAQ.value),
        accounts=load_json_data(ConsultDataTypes.ACCOUNTS.value),
        scans=load_json_data(ConsultDataTypes.SCANS.value),
        screenshot_dir = config.SCREENSHOT_LOCATION
    )

    pprint([account.to_dict() for account in consult_data.accounts])

    # TODO: Handle multiple scans
    # TODO: Generate text of the document

    '''
    for app in consult_data.scans[1].check_apps.spyware:
         summary, concerning = create_app_summary(app, spyware=True)
         app['summary'] = summary
         app['concerning'] = concerning
         app['screenshots'] = get_screenshots('spyware', app['app_name'], context["screenshot_dir"])

    for app in consult_data.scans[1].check_apps.dualuse:
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
    '''

    # create the printout document
    filename = create_printout(consult_data.to_dict())
    workingdir = os.path.abspath(os.getcwd())
    return send_from_directory(workingdir, filename)
