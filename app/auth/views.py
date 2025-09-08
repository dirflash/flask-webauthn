from flask import Blueprint, render_template

auth = Blueprint("auth", __name__)


@auth.route("/register")
def register():
    """Show the form to register a new user"""
    return render_template("auth/register.html")


@auth.route("/login")
def login():
    return "Login user"
