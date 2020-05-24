from datetime import datetime, timedelta
from time import strftime

import config
from flask import Flask, g, session, request
from flask_sqlalchemy import Model, SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__, static_folder='../webstatic',
        template_folder='../templates/')
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQL_DB_PATH
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = config.FLASK_SECRET # doesn't seem to be necessary
app.config['SECRET_KEY'] = config.FLASK_SECRET # doesn't seem to be necessary
app.config['SESSION_TYPE'] = 'filesystem'
sa=SQLAlchemy(app)
Migrate(app, sa)
# sa.create_all() # run in init_db()

@app.before_request
def make_session_permanent():
    session.permanent = True
    # expires at midnight of new day
    app.permanent_session_lifetime = \
            (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0,
                                                         second=0) - \
                                                                 datetime.now()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.after_request
def after_request(response):
    """ Logging after every request. """
    # This avoids the duplication of registry in the log,
    # since that 500 is already logged via @app.errorhandler.
    if response.status_code != 500:
        ts = strftime('[%Y-%b-%d %H:%M]')
        logger.error('%s %s %s %s %s %s',
                     ts,
                     request.remote_addr,
                     request.method,
                     request.scheme,
                     request.full_path,
                     response.status)
    return response


