# https://rickhenry.dev/blog/posts/2022-06-19-flask-webauthn-demo-1/


import os

from flask import Flask
from flask_migrate import Migrate
from models import db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///site.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


db.init_app(app)
Migrate(app, db)


@app.route("/")
def index():
    return "Hello, world!"
