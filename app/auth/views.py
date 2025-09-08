from flask import Blueprint

auth = Blueprint("auth", __name__)


@auth.route("/register")
def register():
    return "Register user"


@auth.route("/login")
def login():
    return "Login user"
