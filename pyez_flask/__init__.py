from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap


app = Flask(__name__)
app.config.from_object('pyez_flask.config')
Bootstrap(app)

db = SQLAlchemy(app)

import pyez_flask.views

