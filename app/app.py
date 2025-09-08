"""
Flask WebAuthn Demo Application

Implementation of passkeys with Flask and SQLAlchemy

This module initializes the Flask app, configures the database and migration,
and defines the main route.

Based on the tutorial at:
https://rickhenry.dev/blog/posts/2022-06-19-flask-webauthn-demo-1/
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_migrate import Migrate  # type: ignore
from models import db

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///site.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


db.init_app(app)
Migrate(app, db)


@app.route("/")
def index():
    """
    Main route for the Flask application.
    Returns index.html template.
    """
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
