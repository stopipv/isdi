import json
from isdi.config import get_config
from isdi.web import app, sa
from isdi.web.model import Client
from isdi.web.forms import ClientForm
from flask import render_template, request, session, redirect, url_for
from isdi.scanner.db import get_client_devices_from_db, new_client_id

config = get_config()


@app.route("/form/", methods=["GET", "POST"])
def client_forms():
    if "clientid" not in session:
        return redirect(url_for("index"))

    prev_submitted = Client.query.filter_by(clientid=session["clientid"]).first()
    if prev_submitted:
        return render_template(
            "main.html", task="form", formdone="already", title=config.TITLE
        )

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
