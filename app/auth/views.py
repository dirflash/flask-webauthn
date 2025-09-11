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


@auth.route("/create-user", methods=["POST"])
def create_user():
    """Create a new user"""
    try:
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()

        # Validation
        if not username:
            return render_template(
                "auth/_partials/user_creation_form.html",
                error="Username is required."
            )

        if not email:
            return render_template(
                "auth/_partials/user_creation_form.html",
                error="Email is required."
            )

        # Create user
        user = User(name=name or username, username=username, email=email)

        try:
            db.session.add(user)
            db.session.commit()
            print(f"User created successfully: {user.username}")
        except IntegrityError as e:
            db.session.rollback()
            print(f"IntegrityError creating user: {e}")
            return render_template(
                "auth/_partials/user_creation_form.html",
                error="That username or email address is already in use. "
                "Please enter a different one.",
            )

        # Generate WebAuthn credential creation options
        try:
            pcco_json = security.prepare_credential_creation(user)
            print(f"WebAuthn options generated for user: {user.username}")
        except Exception as e:
            print(f"Error generating WebAuthn options: {e}")
            db.session.delete(user)
            db.session.commit()
            return render_template(
                "auth/_partials/user_creation_form.html",
                error="Failed to set up authentication. Please try again."
            )

        # Set session and return credential setup template
        session["registration_user_uid"] = user.uid

        res = make_response(
            render_template(
                "auth/_partials/register_credential.html",
                public_credential_creation_options=pcco_json,
            )
        )

        return res

    except Exception as e:
        print(f"Unexpected error in create_user: {e}")
        return render_template(
            "auth/_partials/user_creation_form.html",
            error="An unexpected error occurred. Please try again."
        )


@auth.route("/add-credential", methods=["POST"])
def add_credential():
    """Receive a newly registered credentials to validate and save."""
    try:
        user_uid = session.get("registration_user_uid")
        if not user_uid:
            return make_response('{"verified": false, "error": "User not found in session"}', 400)

        try:
            registration_credential = RegistrationCredential(**request.get_json())
        except Exception as e:
            print(f"Error parsing credential data: {e}")
            return make_response(f'{{"verified": false, "error": "Invalid credential data"}}', 400)

        user = User.query.filter_by(uid=user_uid).first()
        if user is None:
            return make_response('{"verified": false, "error": "User not found"}', 400)

        try:
            security.verify_and_save_credential(user, registration_credential)
            session.pop("registration_user_uid", None)

            res = make_response('{"verified": true}', 201)
            res.set_cookie(
                "user_uid",
                str(user.uid),
                httponly=True,
                secure=request.is_secure,
                samesite="strict",
                max_age=int(datetime.timedelta(days=30).total_seconds()),
            )
            return res

        except InvalidRegistrationResponse as e:
            print(f"Registration verification failed: {e}")
            return make_response(f'{{"verified": false, "error": "Registration verification failed"}}', 400)
        except Exception as e:
            print(f"Unexpected error during verification: {e}")
            return make_response(f'{{"verified": false, "error": "Verification failed"}}', 500)

    except Exception as e:
        print(f"Unexpected error in add_credential: {e}")
        return make_response('{"verified": false, "error": "Internal server error"}', 500)


@auth.route("/login")
def login():
    return "Login user"
