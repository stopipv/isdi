import sqlite3
from flask_sqlalchemy import SQLAlchemy
from isdi.config import get_config
from flask import g
from datetime import datetime as dt
import os
import pandas as pd

config = get_config()
DATABASE = config.SQL_DB_PATH.replace("sqlite:///", "").strip()
# CONSULTS_DATABASE = config.SQL_DB_CONSULT_PATH.replace('sqlite:///', '')


def today():
    db = get_db()
    t = dt.now()
    today = t.strftime("%Y%m%d")
    return today


def new_client_id():
    last_client_id = query_db(
        "select max(clientid) as cid from clients_notes "
        'where created_at > datetime("now", "localtime", "start of day")',
        one=True,
    )["cid"]
    d, t = today(), 0
    # FIXME: won't parse if different ClientID.
    if last_client_id:
        d, t = last_client_id.rsplit("_", 1)
    cid = "{}_{:03d}".format(d, int(t) + 1)
    print("new_client_id >>>> {}".format(cid))
    return cid


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        print("Creating new db connection {}".format(DATABASE))
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = make_dicts
    return db


def init_db(app, sa, force=False):
    with app.app_context():
        if force or not os.path.exists(DATABASE):
            db = get_db()
            with app.open_resource("web/schema.sql", mode="r") as f:
                db.cursor().executescript(f.read())
            db.commit()
            # sa.create_all() # TODO replace in schema.sql
            # TODO how to repopulate?
        # if not os.path.exists(CONSULTS_DATABASE):
        #    sa.create_all()
        # add with sqlachemy the new models stuff
        # can it get the schema sql // make a table
        else:
            db = get_db()


def insert(query, args):
    db = get_db()
    cur = db.execute(query, args)
    lrowid = cur.lastrowid
    cur.close()
    db.commit()
    return lrowid


def insert_many(query, argss):
    db = get_db()
    cur = db.executemany(query, argss)
    lrowid = cur.lastrowid
    cur.close()
    db.commit()
    return lrowid


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    lrowid = cur.lastrowid
    cur.close()
    return (rv[0] if rv else None) if one else rv


def save_note(scanid, note):
    insert("update scan_res set note=? where id=?", args=(note, scanid))
    return True


def create_scan(scan_d):
    """
    @scanr must have following fields.
    """
    print(scan_d)
    return insert(
        "insert into scan_res "
        "(clientid, serial, device, device_model, device_version, device_manufacturer, last_full_charge, device_primary_user, is_rooted, rooted_reasons) "
        "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        args=(
            scan_d["clientid"],
            scan_d["serial"],
            scan_d["device"],
            scan_d["device_model"],
            scan_d["device_version"],
            scan_d["device_manufacturer"],
            scan_d["last_full_charge"],
            scan_d["device_primary_user"],
            scan_d["is_rooted"],
            scan_d["rooted_reasons"],
        ),
    )


def update_appinfo(scanid, appid, remark, action):
    return (
        insert(
            "update app_info set "
            "remark=?, action_taken=? where scanid=? and appid=?",
            args=(remark, action, scanid, appid),
        )
        == 0
    )


def update_app_deleteinfo(scanid, appid, remark):
    return insert(
        "update app_info set " "remark=? here scanid=? and appid=?",
        args=(remark, action, scanid, appid),
    )


def update_mul_appinfo(args):
    return insert_many(
        "update app_info set " "remark=? where scanid=? and appid=?", args
    )


def create_appinfo(scanid, appid, flags, remark="", action="<new>"):
    """
    @scanr must have following fields.

    """
    return insert(
        "insert into app_info (scanid, appid, flags, remark, action_taken) "
        "values (?,?,?,?,?)",
        args=(scanid, appid, flags, remark, action),
    )


def create_mult_appinfo(args):
    """ """
    return insert_many(
        "insert into app_info (scanid, appid, flags, remark, action_taken) values (?,?,?,?,?)",
        args,
    )


def get_is_rooted(serial):
    try:
        d = query_db(
            "select id, is_rooted, rooted_reasons from scan_res where serial=?",
            args=(serial),
            one=False,
        )
        if d:
            d = d[0]
        return d["is_rooted"], d["rooted_reasons"]
    except Exception as e:
        return "<ROOTED_ERR>", "<ROOTED_ERR>"


def get_device_info(ser: str) -> dict:
    d = query_db(
        "select id,device,device_model,serial,device_primary_user from scan_res where serial=?",
        args=(ser,),
        one=True,
    )
    if d:
        return d
    else:
        return {}


def get_client_devices_from_db(clientid: str) -> list:
    # TODO: change 'select serial ...' to 'select device_model ...' (setup
    # first)
    d = query_db(
        'select id,device,device_model,serial,device_primary_user from scan_res where serial like "HSN_%" group by serial',
        # args=(clientid,),
        one=False,
    )
    print("<>get_client_devices_from_db<>", d)
    if d:
        return d
    else:
        return [{}]


def get_most_recent_scan_id(ser: str) -> int:
    d = query_db(
        "select max(id) as scanid from scan_res where serial=?", args=(ser,), one=True
    )
    print(f"Get_most_recent_scanid: {d}")
    return d["scanid"]


def get_scan_res_from_db(scanid):
    d = query_db("select * from scan_res where id=?", args=(scanid,), one=True)
    return d


def get_app_info_from_db(scanid):
    d = query_db("select * from app_info where scanid=?", args=(scanid,), one=False)
    if d:
        return d
    else:
        return []


def get_device_from_db(scanid):
    d = query_db("select device from scan_res where id=?", args=(scanid,), one=True)
    if d:
        return d["device"]
    else:
        return ""


def get_serial_from_db(scanid):
    d = query_db("select serial from scan_res where id=?", args=(scanid,), one=True)
    if d:
        return d["serial"]
    else:
        return ""


def first_element_or_none(l):
    if l and len(l) > 0:
        return l[0]


def create_report(clientid):
    """
    Creates a report for a clientid
    """
    reportf = os.path.join(config.REPORT_PATH, clientid + ".csv")
    d = pd.DataFrame(
        query_db(
            "select * from scan_res inner join app_info on "
            "scan_res.id=app_info.scanid where scan_res.clientid=?",
            args=(clientid,),
        )
    )
    d.to_csv(reportf, index=None)
    return d
