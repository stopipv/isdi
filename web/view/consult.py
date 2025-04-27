import config
import json
from web import app, sa
from web.model import Client
from web.forms import ClientForm
from flask import render_template, request, session, redirect, url_for
from phone_scanner.db import get_client_devices_from_db, new_client_id


@app.route("/form/", methods=["GET", "POST"])
def client_forms():
    if "clientid" not in session:
        return redirect(url_for("index"))

    prev_submitted = Client.query.filter_by(clientid=session["clientid"]).first()
    if prev_submitted:
        return redirect(url_for("edit_forms"))

    # retrieve form defaults from db schema
    client = Client()
    form = ClientForm(request.form)

    if request.method == "POST":
        try:
            if form.validate():
                print("VALIDATED")
                # convert checkbox lists to json-friendly strings
                for field in form:
                    if field.type == "SelectMultipleField":
                        field.data = json.dumps(field.data)
                form.populate_obj(client)
                client.clientid = session["clientid"]
                sa.session.add(client)
                sa.session.commit()
                return render_template(
                    "main.html", task="form", formdone="yes", title=config.TITLE
                )
        except Exception as e:
            print("NOT VALIDATED")
            print(e)
            sa.session.rollback()

    # clients_list = Client.query.all()
    return render_template(
        "main.html",
        task="form",
        form=form,
        title=config.TITLE,
        clientid=session["clientid"],
    )


@app.route("/form/edit/", methods=["GET", "POST"])
def edit_forms():
    if request.method == "POST":
        clientnote = request.form.get("clientnote", request.args.get("clientnote"))

        if clientnote:  # if requesting a form to edit
            session["form_edit_pk"] = clientnote  # set session cookie
            form_obj = Client.query.get(clientnote)
            form = ClientForm(obj=form_obj)
            for field in form:
                if field.type == "SelectMultipleField":
                    field.data = json.loads("".join(field.data))
            return render_template(
                "main.html",
                task="form",
                form=form,
                title=config.TITLE,
                clientid=form_obj.clientid,
            )
        else:  # if edits were submitted
            form_obj = Client.query.get(session["form_edit_pk"])
            cid = form_obj.clientid  # preserve before populate_obj
            form = ClientForm(request.form)
            if form.validate():
                print("VALIDATED")
                # convert checkbox lists to json-friendly strings
                for field in form:
                    if field.type == "SelectMultipleField":
                        field.data = json.dumps(field.data)
            form.populate_obj(form_obj)
            form_obj.clientid = cid
            sa.session.commit()
            return render_template(
                "main.html", task="form", formdone="yes", title=config.TITLE
            )

    clients = Client.query.all()
    return render_template(
        "main.html", clients=clients, task="formedit", title=config.TITLE
    )
