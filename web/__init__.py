import config
from flask import Flask
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
