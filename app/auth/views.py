import datetime
import traceback

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

        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            return render_template(
                "auth/_partials/user_creation_form.html",
                error="That username or email address is already in use. "
                "Please enter a different one.",
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
            print(f"Full traceback: {traceback.format_exc()}")

            # Clean up user if WebAuthn setup fails
            try:
                db.session.delete(user)
                db.session.commit()
                print(f"Cleaned up user {user.username} due to WebAuthn setup failure")
            except Exception as cleanup_error:
                print(f"Error cleaning up user: {cleanup_error}")
                db.session.rollback()

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
        print(f"Full traceback: {traceback.format_exc()}")
        return render_template(
            "auth/_partials/user_creation_form.html",
            error="An unexpected error occurred. Please try again."
        )


def parse_registration_credential(credential_data):
    """Parse WebAuthn registration credential, handling browser compatibility issues"""
    try:
        print(f"Raw credential data received: {credential_data}")

        # Handle different WebAuthn response formats
        if not isinstance(credential_data, dict):
            raise ValueError("Credential data must be a dictionary")

        # The browser sends 'rawId' but Python webauthn library expects 'raw_id'
        # Map rawId to both id and raw_id
        if 'rawId' in credential_data:
            if 'id' not in credential_data:
                credential_data['id'] = credential_data['rawId']
            # Map rawId to raw_id for the webauthn library - convert base64url to bytes
            import base64
            # Add padding if needed for base64url decoding
            raw_id_str = credential_data['rawId']
            # Add padding to make length multiple of 4
            raw_id_str += '=' * (4 - len(raw_id_str) % 4) if len(raw_id_str) % 4 else ''
            credential_data['raw_id'] = base64.urlsafe_b64decode(raw_id_str)
            # Remove rawId to avoid conflicts
            del credential_data['rawId']

        # Ensure required fields are present
        required_fields = ['id', 'response', 'type']
        missing_fields = [field for field in required_fields if field not in credential_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Ensure raw_id is present
        if 'raw_id' not in credential_data:
            raise ValueError("Missing raw_id field after mapping from rawId")

        # Clean up the data - only keep fields the library expects
        # Based on webauthn library version 2.7.0, RegistrationCredential expects:
        expected_fields = {
            'id', 'raw_id', 'response', 'type'
        }

        cleaned_data = {k: v for k, v in credential_data.items() if k in expected_fields}

        print(f"Cleaned credential data: {cleaned_data}")

        # Create the RegistrationCredential object
        # The webauthn library expects specific field names and structure
        if 'response' in cleaned_data and isinstance(cleaned_data['response'], dict):
            response_dict = cleaned_data['response'].copy()

            # Create a proper response object structure
            from webauthn.helpers.structs import AuthenticatorAttestationResponse
            import base64

            # Map the browser field names to what the library expects and decode base64 data
            response_data = {}
            if 'clientDataJSON' in response_dict:
                # Decode base64 clientDataJSON to bytes
                client_data_b64 = response_dict['clientDataJSON']
                # Add padding if needed
                client_data_b64 += '=' * (4 - len(client_data_b64) % 4) if len(client_data_b64) % 4 else ''
                response_data['client_data_json'] = base64.urlsafe_b64decode(client_data_b64)
            if 'attestationObject' in response_dict:
                # Decode base64 attestationObject to bytes
                attestation_b64 = response_dict['attestationObject']
                # Add padding if needed
                attestation_b64 += '=' * (4 - len(attestation_b64) % 4) if len(attestation_b64) % 4 else ''
                response_data['attestation_object'] = base64.urlsafe_b64decode(attestation_b64)

            # Create the AuthenticatorAttestationResponse object
            cleaned_data['response'] = AuthenticatorAttestationResponse(**response_data)

        print(f"Final credential data structure: {type(cleaned_data['response'])}")
        registration_credential = RegistrationCredential(**cleaned_data)

        return registration_credential

    except Exception as e:
        print(f"Error parsing registration credential: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        raise


@auth.route("/add-credential", methods=["POST"])
def add_credential():
    """Receive a newly registered credentials to validate and save."""
    try:
        user_uid = session.get("registration_user_uid")
        if not user_uid:
            print("No user UID found in session")
            return make_response('{"verified": false, "error": "User not found in session"}', 400)

        user = User.query.filter_by(uid=user_uid).first()
        if user is None:
            print(f"No user found with UID: {user_uid}")
            return make_response('{"verified": false, "error": "User not found"}', 400)

        try:
            credential_data = request.get_json()
            if not credential_data:
                print("No JSON data received")
                return make_response('{"verified": false, "error": "No credential data received"}', 400)

            registration_credential = parse_registration_credential(credential_data)

        except Exception as e:
            print(f"Error parsing credential data: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

            # Clean up user if credential parsing fails
            try:
                print(f"Cleaning up user {user.username} due to credential parsing failure")
                session.pop("registration_user_uid", None)
                db.session.delete(user)
                db.session.commit()
                print(f"Successfully cleaned up user {user.username}")
            except Exception as cleanup_error:
                print(f"Error cleaning up user: {cleanup_error}")
                db.session.rollback()

            return make_response(f'{{"verified": false, "error": "Invalid credential data: {str(e)}"}}', 400)

        try:
            print(f"Attempting to verify and save credential for user: {user.username}")
            security.verify_and_save_credential(user, registration_credential)

            # Clear session only after successful verification
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
            print(f"✅ WebAuthn credential successfully registered for user: {user.username}")
            return res

        except InvalidRegistrationResponse as e:
            print(f"Registration verification failed: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

            # Clean up user if verification fails
            try:
                print(f"Cleaning up user {user.username} due to verification failure")
                session.pop("registration_user_uid", None)
                db.session.delete(user)
                db.session.commit()
                print(f"Successfully cleaned up user {user.username}")
            except Exception as cleanup_error:
                print(f"Error cleaning up user: {cleanup_error}")
                db.session.rollback()

            return make_response(f'{{"verified": false, "error": "Registration verification failed"}}', 400)

        except Exception as e:
            print(f"Unexpected error during verification: {e}")
            print(f"Full traceback: {traceback.format_exc()}")

            # Clean up user if unexpected error occurs
            try:
                print(f"Cleaning up user {user.username} due to unexpected error")
                session.pop("registration_user_uid", None)
                db.session.delete(user)
                db.session.commit()
                print(f"Successfully cleaned up user {user.username}")
            except Exception as cleanup_error:
                print(f"Error cleaning up user: {cleanup_error}")
                db.session.rollback()

            return make_response(f'{{"verified": false, "error": "Verification failed"}}', 500)

    except Exception as e:
        print(f"Unexpected error in add_credential: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        return make_response('{"verified": false, "error": "Internal server error"}', 500)


@auth.route("/cleanup-failed-registration", methods=["POST"])
def cleanup_failed_registration():
    """Clean up failed registration attempts"""
    try:
        user_uid = session.get("registration_user_uid")
        if user_uid:
            user = User.query.filter_by(uid=user_uid).first()
            if user:
                db.session.delete(user)
                db.session.commit()
                session.pop("registration_user_uid", None)
                print(f"Cleaned up failed registration for user: {user.username}")

        return make_response('{"cleaned": true}', 200)
    except Exception as e:
        print(f"Error in cleanup: {e}")
        return make_response('{"cleaned": false}', 500)


@auth.route("/login")
def login():
    return "Login user"
