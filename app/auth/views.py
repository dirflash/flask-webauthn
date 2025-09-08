from flask import Blueprint, make_response, render_template, request
from models import User, db
from sqlalchemy.exc import IntegrityError

auth = Blueprint("auth", __name__, template_folder="templates")


@auth.route("/register")
def register():
    """Show the form to register a new user"""
    return render_template("auth/register.html")


@auth.route("/create-user", methods=["POST"])
def create_user():
    """Create a new user"""
    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")

    user = User(name=name, username=username, email=email)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        return render_template(
            "auth/_partials/user_creation_form.html",
            error="That username or email address is already in use. "
            "Please enter a different one.",
        )

    return make_response("User created", 201)


@auth.route("/login")
def login():
    return "Login user"
