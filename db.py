import sqlite3
import config
from flask import g
from datetime import datetime as dt
import config
import os
import pandas as pd

DATABASE = config.SQL_DB_PATH.replace('sqlite:///', '')


def today():
    db = get_db()
    t = dt.now()
    today = t.strftime('%Y%m%d:%H')
    return today


def new_client_id():
    last_client_id = query_db(
        'select max(clientid) as cid from scan_res '\
        'where time > datetime("now", "localtime", "-1 day")',
        one=True
    )['cid']
    d, t = today(), 0
    print("new_client_id >>>> {}".format(last_client_id))
    if last_client_id:
        d, t = last_client_id.split('_')
    return '{}_{:03d}'.format(d, int(t)+1)


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))



def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        print("Creating new db connection {}".format(DATABASE))
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = make_dicts
    return db

def init_db(app, force=False):
    with app.app_context():
        db = get_db()
        if force or not os.path.exists(DATABASE):
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()


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
    lrowid =  cur.lastrowid
    cur.close()
    return (rv[0] if rv else None) if one else rv


def save_note(scanid, note):
    insert("update scan_res set note=? where id=?",
           args=(note, scanid))
    return True


def create_scan(clientid, serial, device):
    """
    @scanr must have following fields.
    
    """
    return insert(
        "insert into scan_res "\
        "(clientid, serial, device) "\
        "values (?, ?, ?)",
        args=(clientid, serial, device),
    )


def update_appinfo(scanid, appid, remark, action):
    return insert("update app_info set "\
                    "remark=?, action=? where scanid=? and appid=?",
                    args=(remark, action, scanid, appid),
    )


def update_app_deleteinfo(scanid, appid, remark):
    return insert("update app_info set "\
                    "remark=? here scanid=? and appid=?",
                    args=(remark, action, scanid, appid),
    )


def update_mul_appinfo(args):
    return insert_many("update app_info set "\
                    "remark=? where scanid=? and appid=?",
                    args
    )


def create_appinfo(scanid, appid, flags, remark='', action='<new>'):
    """
    @scanr must have following fields.
    
    """
    return insert(
        "insert into app_info (scanid, appid, flags, remark, action_taken) "
        "values (?,?,?,?,?)",
        args=(scanid, appid, flags, remark, action)
    )

def create_mult_appinfo(args):
    """
    """
    return insert_many("insert into app_info (scanid, appid, flags, remark, action_taken) values (?,?,?,?,?)",
                       args)
    
    

def get_device_from_db(scanid):
    d = query_db('select device from scan_res where id=?', args=(scanid,), one=True)
    if d:
        return d['device']
    else:
        return ''

def get_serial_from_db(scanid):
    d = query_db('select serial from scan_res where id=?', args=(scanid,), one=True)
    if d:
        return d['serial']
    else:
        return ''

def create_report(clientid):
    """
    Creates a report for a clientid
    """
    reportf = os.path.join(config.REPORT_PATH, clientid + '.csv')
    d = pd.DataFrame(query_db("select * from scan_res inner join app_info on "
                             "scan_res.id=app_info.scanid where scan_res.clientid=?",
                             args=(clientid,)))
    d.to_csv(reportf,  index=None)
    return d

