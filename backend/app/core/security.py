# import hashlib
# import secrets
# from datetime import datetime, timedelta, timezone

# import jwt
# from pwdlib import PasswordHash

# from app.core.config import settings


# password_hash = PasswordHash.recommended()


# def hash_password(password: str) -> str:
#     return password_hash.hash(password)


# def verify_password(password: str, hashed_password: str) -> bool:
#     return password_hash.verify(password, hashed_password)


# def create_access_token(
#     user_id: int,
#     organization_id: int | None = None,
#     role: str | None = None,
# ) -> str:
#     expires_at = datetime.now(timezone.utc) + timedelta(
#         minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
#     )

#     payload = {
#         "sub": str(user_id),
#         "type": "access",
#         "exp": expires_at,
#     }

#     if organization_id is not None:
#         payload["organization_id"] = organization_id

#     if role is not None:
#         payload["role"] = role

#     return jwt.encode(
#         payload,
#         settings.JWT_SECRET_KEY,
#         algorithm=settings.JWT_ALGORITHM,
#     )


# def decode_access_token(token: str) -> dict:
#     payload = jwt.decode(
#         token,
#         settings.JWT_SECRET_KEY,
#         algorithms=[settings.JWT_ALGORITHM],
#     )

#     if payload.get("type") != "access":
#         raise jwt.InvalidTokenError("Invalid token type")

#     return payload


# def create_refresh_token() -> str:
#     return secrets.token_urlsafe(64)


# def hash_refresh_token(token: str) -> str:
#     return hashlib.sha256(
#         token.encode("utf-8")
#     ).hexdigest()


# def get_refresh_token_expiry() -> datetime:
#     return datetime.now(timezone.utc) + timedelta(
#         days=settings.REFRESH_TOKEN_EXPIRE_DAYS
#     )
    

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import hmac

from app.core.config import settings


_PASSWORD_HASH_ITERATIONS = 600_000
_PASSWORD_HASH_PREFIX = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_HASH_ITERATIONS,
    )
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_digest = base64.b64encode(digest).decode("ascii")
    return f"{_PASSWORD_HASH_PREFIX}${_PASSWORD_HASH_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        prefix, iterations, encoded_salt, encoded_digest = hashed_password.split("$")
        if prefix != _PASSWORD_HASH_PREFIX:
            return False

        iterations_value = int(iterations)
        salt = base64.b64decode(encoded_salt, validate=True)
        expected_digest = base64.b64decode(encoded_digest, validate=True)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations_value,
        )
        # return hashlib.compare_digest(actual_digest, expected_digest)
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError, base64.binascii.Error):
        return False


def create_access_token(
    user_id: int,
    organization_id: int | None = None,
    role: str | None = None,
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expires_at,
    }

    if organization_id is not None:
        payload["organization_id"] = organization_id

    if role is not None:
        payload["role"] = role

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def get_refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    
    
    