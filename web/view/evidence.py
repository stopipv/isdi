import json
import os
import pickle
import traceback
from datetime import datetime
from enum import Enum
from operator import itemgetter
from pprint import pprint
from time import sleep

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
from wtforms import ValidationError

import config
from evidence_collection import (  # create_account_summary,; create_app_summary,
    CONTEXT_PKL_FNAME,
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
    ManualAddPageForm,
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
    load_object_from_json,
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
        setup_data = load_object_from_json(ConsultDataTypes.SETUP.value)
        pprint(setup_data)

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
        
        elif not form.validate():
            flash("Missing required fields")
            return redirect(url_for('evidence_setup'))
        

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
        taq_data = load_object_from_json(ConsultDataTypes.TAQ.value)
    
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
        pprint("FORM DATA START")
        pprint(form.data)
        pprint("FORM DATA END")
        if form.is_submitted() and form.validate():

            # clean up data
            clean_data = remove_unwanted_data(form.data)

            # load data as class
            taq_data = TAQData(**clean_data)

            # save clean data
            save_data_as_json(taq_data, ConsultDataTypes.TAQ.value)

            return redirect(url_for('evidence_home'))
        
        elif not form.validate():
            flash("Form validation error - are you missing required fields?", 'error')
            return redirect(url_for('evidence_taq'))
        
    return redirect(url_for('evidence_taq'))



@app.route("/evidence/scan", methods={'GET', 'POST'})
def evidence_scan_start():

    # always assume we are starting with a fresh scan
    all_scan_data = load_object_from_json(ConsultDataTypes.SCANS.value)
    current_scan = ScanData()
    form = StartForm()

    context = dict(
        task = "evidence-scan",
        form = form,
        title=config.TITLE,
        scan_data = current_scan.to_dict(),
        step = 1,
        id = 0,
    )

    if request.method == "GET":
        pprint(form.data)
        return render_template('main.html', **context)

    if request.method == "POST":
        pprint(form.data)
        if form.is_submitted() and form.validate():

            if form.manualadd.data:
                return redirect(url_for('evidence_scan_manualadd', 
                                        device_nickname=form.data["device_nickname"]))

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
                                        all_apps=all_apps)
                
                pprint(current_scan.__dict__)
                for app in current_scan.all_apps:
                    pprint(app.permission_info.__dict__)
                
                current_scan.id = len(all_scan_data)
                all_scan_data.append(current_scan)
            
                save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)
                return redirect(url_for('evidence_scan_select', ser=current_scan.serial))

            except Exception as e:
                print(traceback.format_exc())
                flash("Scan error: " + str(e))
                return redirect(url_for('evidence_scan_start'))
            
        elif not form.validate():
            flash("Form validation error - are you missing required fields?", 'error')

    return redirect(url_for('evidence_scan_start'))



@app.route("/evidence/scan/select/<string:ser>", methods={'GET', 'POST'})
def evidence_scan_select(ser):

    # load all scans
    all_scan_data = load_object_from_json(ConsultDataTypes.SCANS.value)

    # get the right scan by serial number
    current_scan = get_scan_by_ser(ser, all_scan_data)
    assert current_scan.serial == ser

    pprint(current_scan.all_apps[0].permission_info.__dict__)

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
            #clean_data = remove_unwanted_data(form.data)

            # get selected apps from the form data
            to_investigate_titles = [app["title"] for app in form.data['apps'] if app['investigate']]
            
            selected_apps = []
            for app in current_scan.all_apps:
                if app.title in to_investigate_titles:
                    selected_apps.append(app)

            pprint(selected_apps)
            pprint("SELECTED APPS")

            current_scan.selected_apps = selected_apps

            # update the current scan data and save it as the most recent scan
            #current_scan.selected_apps = [AppInfo(**app) for app in selected_apps]
            all_scan_data = update_scan_by_ser(current_scan, all_scan_data)

            # save this updated data
            save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)
        
            return redirect(url_for('evidence_scan_investigate', ser=ser))
        
        if not form.validate():
            flash("Form validation error - are you missing required fields?", 'error')

        return redirect(url_for('evidence_scan_select'), ser=ser)
        
@app.route("/evidence/scan/manualadd/<string:device_nickname>", methods={'GET', 'POST'})
def evidence_scan_manualadd(device_nickname):

    form = ManualAddPageForm(apps = [""], device_nickname=device_nickname)

    ### IF IT'S A GET:
    if request.method == 'GET':

        context = dict(
            task = "evidence-scan-manualadd",
            title = config.TITLE,
            form = form
        )

        return render_template('main.html', **context)
    
    ### IF IT'S A POST:
    if request.method == 'POST':

        if form.is_submitted():

            # if it's an addline request, do that and reload
            if form.addline.data:
                form.update_self()
                context = dict(
                    task = "evidence-scan-manualadd",
                    title = config.TITLE,
                    form = form
                )
                return render_template('main.html', **context)

            elif form.validate():
                # TODO take data and do something with it

                pprint(form.data)

                selected_apps = []
                for app in form.data['apps']:
                    flags = []
                    if app['spyware']:
                        flags = ['spyware']
                    if app['app_name'].strip() != "":
                        selected_apps.append({
                            "title": app['app_name'],
                            "investigate": True,
                            "flags": flags
                        })


                manual_scan = ScanData(
                    manual=True,
                    device_nickname=device_nickname,
                    serial=device_nickname,
                    all_apps=[],
                    selected_apps=selected_apps
                )


                # load all scans
                all_scan_data = load_object_from_json(ConsultDataTypes.SCANS.value)
                
                # add manual scan
                all_scan_data = update_scan_by_ser(manual_scan, all_scan_data)

                # save
                save_data_as_json(all_scan_data, ConsultDataTypes.SCANS.value)

                pprint(manual_scan.__dict__)

                for app in manual_scan.selected_apps:
                    pprint(app.__dict__)

                return redirect(url_for('evidence_scan_investigate', ser=manual_scan.serial))
            
            if not form.validate():
                flash("Form validation error - are you missing required fields?", 'error')
                
            return redirect(url_for('evidence_scan_manualadd', device_nickname=device_nickname))





@app.route("/evidence/scan/investigate/<string:ser>", methods={'GET', 'POST'})
def evidence_scan_investigate(ser):

    # load all scans
    all_scan_data = load_object_from_json(ConsultDataTypes.SCANS.value)

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
    
        elif not form.validate():
            flash("Form validation error - are you missing required fields?", 'error')
            return redirect(url_for('evidence_scan_investigate', ser=ser))

    return redirect(url_for('evidence_scan_investigate', ser=ser))



@app.route("/evidence/account", methods={'GET'})
def evidence_account_default():

    # place to save the num scans later if it becomes a pain to load it
    accounts = load_json_data(ConsultDataTypes.ACCOUNTS.value)
    new_id = len(accounts)

    return redirect(url_for('evidence_account', id=new_id))

@app.route("/evidence/account/<int:id>", methods={'GET', 'POST'})
def evidence_account(id):

    all_account_data = load_object_from_json(ConsultDataTypes.ACCOUNTS.value)
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
        pprint("FORM DATA START")
        pprint(form.data)
        pprint("FORM DATA END")
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
        
        if not form.validate():
            flash("Form validation error - are you missing required fields?", 'error')
            pprint(form.errors)


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

    # create the printout document
    filename = create_printout(consult_data.to_dict())
    workingdir = os.path.abspath(os.getcwd())
    return send_from_directory(workingdir, filename)
