import datetime
import os
import json
import base64
from urllib.parse import urlparse

import webauthn
from flask import request
from models import WebAuthnCredential, db

# Redis configuration with error handling
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Initialize Redis with error handling
REGISTRATION_CHALLENGES = None
try:
    from redis import Redis
    REGISTRATION_CHALLENGES = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=0,
        decode_responses=True,  # Keep as True, we'll handle binary data differently
    )
    # Test connection
    REGISTRATION_CHALLENGES.ping()
    print("Redis connection successful")
except Exception as e:
    print(f"Redis connection failed: {e}")
    print("Falling back to in-memory storage (not recommended for production)")
    # Fallback to in-memory storage
    REGISTRATION_CHALLENGES = {}


def _hostname():
    return str(urlparse(request.base_url).hostname)


def _origin():
    """Get the origin for WebAuthn, handling both HTTP (dev) and HTTPS (prod)"""
    parsed = urlparse(request.base_url)
    # For development, allow HTTP. For production, use HTTPS
    if parsed.hostname in ['localhost', '127.0.0.1'] or os.getenv('FLASK_ENV') == 'development':
        return f"{parsed.scheme}://{parsed.netloc}"
    else:
        # Force HTTPS for production
        return f"https://{parsed.netloc}"


def _store_challenge(user_uid, challenge):
    """Store challenge with fallback to in-memory storage"""
    try:
        if hasattr(REGISTRATION_CHALLENGES, 'set'):
            # Redis storage - convert bytes challenge to base64 string
            if isinstance(challenge, bytes):
                challenge_str = base64.b64encode(challenge).decode('utf-8')
            else:
                challenge_str = str(challenge)

            # Store as JSON to preserve type information
            challenge_data = {
                'challenge': challenge_str,
                'is_bytes': isinstance(challenge, bytes),
                'timestamp': datetime.datetime.now().isoformat()
            }

            REGISTRATION_CHALLENGES.set(
                f"webauthn_challenge:{user_uid}", 
                json.dumps(challenge_data),
                ex=600  # 10 minutes expiration
            )
            print(f"Challenge stored for user {user_uid}")
        else:
            # In-memory fallback
            REGISTRATION_CHALLENGES[user_uid] = {
                'challenge': challenge,
                'expires': datetime.datetime.now() + datetime.timedelta(minutes=10)
            }
    except Exception as e:
        print(f"Error storing challenge: {e}")
        raise


def _get_challenge(user_uid):
    """Get challenge with fallback to in-memory storage"""
    try:
        if hasattr(REGISTRATION_CHALLENGES, 'get'):
            # Redis storage
            challenge_json = REGISTRATION_CHALLENGES.get(f"webauthn_challenge:{user_uid}")
            if challenge_json:
                try:
                    challenge_data = json.loads(challenge_json)
                    challenge_str = challenge_data['challenge']

                    # Convert back to bytes if it was originally bytes
                    if challenge_data.get('is_bytes', False):
                        return base64.b64decode(challenge_str)
                    else:
                        return challenge_str
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing challenge data: {e}")
                    return None
            return None
        else:
            # In-memory fallback
            stored = REGISTRATION_CHALLENGES.get(user_uid)
            if stored and stored['expires'] > datetime.datetime.now():
                return stored['challenge']
            elif stored:
                # Expired
                del REGISTRATION_CHALLENGES[user_uid]
            return None
    except Exception as e:
        print(f"Error retrieving challenge: {e}")
        return None


def _delete_challenge(user_uid):
    """Delete challenge with fallback to in-memory storage"""
    try:
        if hasattr(REGISTRATION_CHALLENGES, 'delete'):
            # Redis storage
            REGISTRATION_CHALLENGES.delete(f"webauthn_challenge:{user_uid}")
            print(f"Challenge deleted for user {user_uid}")
        else:
            # In-memory fallback
            REGISTRATION_CHALLENGES.pop(user_uid, None)
    except Exception as e:
        print(f"Error deleting challenge: {e}")


def prepare_credential_creation(user):
    """
    Generate the configuration needed by the client to start registering a new
    WebAuthn credential.
    """
    try:
        user_id_bytes = str(user.id).encode("utf-8")

        public_credential_creation_options = webauthn.generate_registration_options(
            rp_id=_hostname(),
            rp_name="Flask WebAuthn Demo",
            user_id=user_id_bytes,
            user_name=user.username,
            user_display_name=user.name or user.username,  # Ensure display name exists
        )

        # Store challenge
        _store_challenge(user.uid, public_credential_creation_options.challenge)
        print(f"Challenge generated and stored for user: {user.username}")

        return webauthn.options_to_json(public_credential_creation_options)

    except Exception as e:
        print(f"Error preparing credential creation: {e}")
        raise


def verify_and_save_credential(user, registration_credential):
    """Verify that a new credential is valid"""
    try:
        expected_challenge = _get_challenge(user.uid)
        print(f"Retrieved challenge for user {user.username}: {expected_challenge is not None}")

        if not expected_challenge:
            raise ValueError("No challenge found for user. Please try registration again.")

        print(f"Verifying credential with challenge for user: {user.username}")

        # Verify the registration response
        auth_verification = webauthn.verify_registration_response(
            credential=registration_credential,
            expected_challenge=expected_challenge,
            expected_origin=_origin(),
            expected_rp_id=_hostname(),
        )

        print(f"Credential verification successful for user: {user.username}")

        # Save the credential
        credential = WebAuthnCredential(
            user=user,
            credential_public_key=auth_verification.credential_public_key,
            credential_id=auth_verification.credential_id,
        )

        db.session.add(credential)
        db.session.commit()
        print(f"Credential saved to database for user: {user.username}")

        # Clean up the challenge
        _delete_challenge(user.uid)

        return auth_verification

    except Exception as e:
        print(f"Error verifying credential: {e}")
        raise
