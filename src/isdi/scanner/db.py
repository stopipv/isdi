import sqlite3
from flask_sqlalchemy import SQLAlchemy
from isdi.config import get_config
from flask import g
from datetime import datetime as dt
import os
import csv
import threading

config = get_config()
DATABASE = config.SQL_DB_PATH.replace("sqlite:///", "").strip()
# CONSULTS_DATABASE = config.SQL_DB_CONSULT_PATH.replace('sqlite:///', '')
_thread_local = threading.local()

# Database schema embedded as string for .pyz compatibility
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients_notes (
	id INTEGER NOT NULL,
	created_at DATETIME,
	clientid VARCHAR(100) DEFAULT '' NOT NULL,
	consultant_initials VARCHAR(100) DEFAULT '' NOT NULL,
	fjc VARCHAR(13) DEFAULT '' NOT NULL,
	preferred_language VARCHAR(100) DEFAULT 'English' NOT NULL,
	referring_professional VARCHAR(100) DEFAULT '' NOT NULL,
	referring_professional_email VARCHAR(255),
	referring_professional_phone VARCHAR(50),
	caseworker_present VARCHAR(23) DEFAULT '' NOT NULL,
	caseworker_present_safety_planning VARCHAR(3) DEFAULT '' NOT NULL,
	caseworker_recorded VARCHAR(3) DEFAULT '' NOT NULL,
	recorded VARCHAR(3) DEFAULT '' NOT NULL,
	chief_concerns VARCHAR(400) DEFAULT '' NOT NULL,
	chief_concerns_other TEXT DEFAULT '' NOT NULL,
	android_phones INTEGER DEFAULT '0' NOT NULL,
	android_tablets INTEGER DEFAULT '0' NOT NULL,
	iphone_devices INTEGER DEFAULT '0' NOT NULL,
	ipad_devices INTEGER DEFAULT '0' NOT NULL,
	macbook_devices INTEGER DEFAULT '0' NOT NULL,
	windows_devices INTEGER DEFAULT '0' NOT NULL,
	echo_devices INTEGER DEFAULT '0' NOT NULL,
	other_devices VARCHAR(400) DEFAULT '',
	checkups VARCHAR(400) DEFAULT '',
	checkups_other VARCHAR(400) DEFAULT '',
	vulnerabilities VARCHAR(600) DEFAULT '' NOT NULL,
	vulnerabilities_trusted_devices TEXT DEFAULT '',
	vulnerabilities_other TEXT DEFAULT '',
	safety_planning_onsite VARCHAR(14) DEFAULT '' NOT NULL,
	changes_made_onsite TEXT DEFAULT '',
	unresolved_issues TEXT DEFAULT '',
	follow_ups_todo TEXT DEFAULT '',
	general_notes TEXT DEFAULT '',
	case_summary TEXT DEFAULT '',
	PRIMARY KEY (id),
	CHECK (fjc IN ('', 'Brooklyn', 'Queens', 'The Bronx', 'Manhattan', 'Staten Island')),
	CHECK (caseworker_present IN ('', 'For entire consult', 'For part of the consult', 'No')),
	CHECK (caseworker_present_safety_planning IN ('', 'Yes', 'No')),
	CHECK (caseworker_recorded IN ('', 'Yes', 'No')),
	CHECK (recorded IN ('', 'Yes', 'No')),
	CHECK (safety_planning_onsite IN ('', 'Yes', 'No', 'Not applicable'))
);

CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clientid TEXT,
  location TEXT,
  issues TEXT,
  assessment TEXT,
  plan TEXT,
  the_rest TEXT,
  time DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS scan_res (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clientid TEXT,
  serial TEXT,
  note TEXT,
  device TEXT,
  device_model TEXT,
  device_manufacturer TEXT,
  device_version TEXT,
  is_rooted INTEGER,
  rooted_reasons TEXT,
  last_full_charge DATETIME,
  device_primary_user TEXT,
  device_access TEXT,
  how_obtained TEXT,
  time DATETIME DEFAULT (datetime('now', 'localtime')),
  FOREIGN KEY(clientid) REFERENCES clients_notes(clientid)
);

CREATE TABLE IF NOT EXISTS app_info (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scanid INTEGER,
  appid TEXT,
  flags TEXT,
  remark TEXT,
  action_taken TEXT,
  apk_path TEXT,
  install_date DATETIME,
  last_updated DATETIME,
  app_version TEXT,
  permissions TEXT,
  permissions_reason TEXT,
  permissions_used DATETIME,
  data_usage INTEGER,
  battery_usage INTEGER,
  time DATETIME DEFAULT (datetime('now', 'localtime')),
  FOREIGN KEY(scanid) REFERENCES scan_res(id)
);

CREATE INDEX IF NOT EXISTS idx_clients_notes_clientid on clients_notes (clientid);
CREATE INDEX IF NOT EXISTS idx_scan_res_clientid on scan_res (clientid);
CREATE INDEX IF NOT EXISTS idx_app_info_scanid on app_info (scanid);
"""


def _schema_needs_init(db) -> bool:
    cur = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='clients_notes'"
    )
    return cur.fetchone() is None


def _load_schema_sql() -> str:
    """Return embedded schema SQL for .pyz compatibility."""
    return SCHEMA_SQL


def _init_schema(db) -> None:
    try:
        schema_sql = _load_schema_sql()
    except Exception as exc:
        raise RuntimeError(f"Failed to load schema.sql: {exc}") from exc
    db.executescript(schema_sql)
    db.commit()


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
    try:
        db = getattr(g, "_database", None)
        if db is None:
            print("Creating new db connection {}".format(DATABASE))
            db = g._database = sqlite3.connect(DATABASE)
            db.row_factory = make_dicts
            if _schema_needs_init(db):
                _init_schema(db)
        return db
    except RuntimeError:
        if not hasattr(_thread_local, 'db') or _thread_local.db is None:
            print("Creating fallback db connection {}".format(DATABASE))
            _thread_local.db = sqlite3.connect(DATABASE)
            _thread_local.db.row_factory = make_dicts
            if _schema_needs_init(_thread_local.db):
                _init_schema(_thread_local.db)
        return _thread_local.db


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
    rows = query_db(
        "select * from scan_res inner join app_info on "
        "scan_res.id=app_info.scanid where scan_res.clientid=?",
        args=(clientid,),
    )
    if not rows:
        with open(reportf, "w", encoding="utf-8") as fh:
            fh.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(reportf, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return d
