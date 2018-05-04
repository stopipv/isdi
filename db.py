import sqlite3
import config

DATABASE = config.SQL_DB_PATH
db = None


def get_db():
    global db
    if db is None:
        db = sqlite3.connect(config.SQL_DB_PATH)
    return db


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()