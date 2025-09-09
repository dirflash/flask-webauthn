"""flake8: noqa: F401, E261, E302, E305"""
import datetime
import os
from urllib.parse import urlparse

import webauthn
from flask import request
from redis import Redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

REGISTRATION_CHALLENGES = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
)


def _hostname():
    return str(urlparse(request.base_url).hostname)


def prepare_credential_creation(user):
    """
    Generate the configuration needed by the client to start registering a new
    WebAuthn credential.
    """
    public_credential_creation_options = webauthn.generate_registration_options(
        rp_id=_hostname(),
        rp_name="Flask WebAuthn Demo",
        user_id=user.uid,
        user_name=user.username,
    )

    # Redis is perfectly happy to store the binary challenge value.
    REGISTRATION_CHALLENGES.set(user.uid, public_credential_creation_options.challenge)
    REGISTRATION_CHALLENGES.expire(user.uid, datetime.timedelta(minutes=10))

    return webauthn.options_to_json(public_credential_creation_options)
