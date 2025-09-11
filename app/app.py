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

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Database configuration - Use environment variable or default to SQLite
database_url = os.getenv("DATABASE_URL", "sqlite:///site.db")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session configuration - provide fallback for SECRET_KEY
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

if not os.getenv("SECRET_KEY"):
    print("WARNING: Using default SECRET_KEY. Set SECRET_KEY environment variable for production!")

# Import models after app configuration but before db.init_app
from models import db, User, WebAuthnCredential
from auth.views import auth
from admin.dbm import dbm

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Register blueprints - Remove conflicting URL prefixes
app.register_blueprint(auth)  # auth blueprint has no prefix
app.register_blueprint(dbm)   # dbm blueprint already has /dbm prefix


@app.route("/")
def index():
    """
    Main route for the Flask application.
    Returns index.html template.
    """
    return render_template("index.html")


def create_tables_if_needed():
    """Create database tables only for SQLite/development"""
    try:
        database_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")

        # Only create tables manually for SQLite (development)
        if "sqlite" in database_url.lower():
            with app.app_context():
                db.create_all()
                print("✅ SQLite database tables created successfully")
        else:
            print("ℹ️  Using PostgreSQL - tables managed by migrations")

    except Exception as e:
        print(f"❌ Error in table creation: {e}")


# Initialize database tables for development only
if __name__ == "__main__":
    create_tables_if_needed()
    app.run(host="0.0.0.0", port=5000, debug=True)
