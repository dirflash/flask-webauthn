import datetime

from auth import security
from flask import Blueprint, abort, make_response, render_template, request, session
from models import User, db
from sqlalchemy.exc import IntegrityError
from webauthn.helpers.exceptions import InvalidRegistrationResponse
from webauthn.helpers.structs import RegistrationCredential

auth = Blueprint("auth", __name__, template_folder="templates")


@auth.route("/register")
def register():
    """Show the form to register a new user"""
    return render_template("auth/register.html")


@auth.route("/register-credential", methods=["POST"])
def register_credential():
    """Receive a newly registered credentials to validate and save."""
    user_uid = session.get("registration_user_uid")
    if not user_uid:
        abort(make_response("Error user not found", 400))

    registration_credential = RegistrationCredential.parse_raw(request.get_data())

    return "Register credential"


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

    pcco_json = security.prepare_credential_creation(user)
    res = make_response(
        render_template(
            "auth/_partials/register_credential.html",
            public_credential_creation_options=pcco_json,
        )
    )
    session["registration_user_uid"] = user.uid

    return res


@auth.route("/add-credential", methods=["POST"])
def add_credential():
    """Receive a newly registered credentials to validate and save."""
    user_uid = session.get("registration_user_uid")
    if not user_uid:
        abort(make_response("Error user not found", 400))

    try:
        registration_credential = RegistrationCredential(**request.get_json())
    except Exception as e:
        return make_response(f'{{"verified": false, "error": "Invalid credential data: {str(e)}"}}', 400)

    user = User.query.filter_by(uid=user_uid).first()
    if user is None:
        return make_response('{"verified": false, "error": "User not found"}', 400)

    try:
        security.verify_and_save_credential(user, registration_credential)
        session["registration_user_uid"] = None
        res = make_response('{"verified": true}', 201)
        res.set_cookie(
            "user_uid",
            str(user.uid),
            httponly=True,
            secure=request.is_secure,  # Only secure in HTTPS
            samesite="strict",
            max_age=int(datetime.timedelta(days=30).total_seconds()),
        )
        return res
    except InvalidRegistrationResponse:
        abort(make_response('{"verified": false}', 400))
    except Exception as e:
        return make_response(f'{{"verified": false, "error": "Unexpected error: {str(e)}"}}', 500)


@auth.route("/login")
def login():
    return "Login user"
