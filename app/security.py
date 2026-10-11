import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext


# =========================
# SECURITY CONFIGURATION
# =========================

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def _secret_key() -> str:

    secret_key = os.getenv("NEXORA_SECRET_KEY", "")
    if len(secret_key) < 32:
        raise RuntimeError(
            "NEXORA_SECRET_KEY must contain at least 32 characters"
        )
    return secret_key


def ensure_auth_signing_configured() -> None:

    _secret_key()


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================
# PASSWORD FUNCTIONS
# =========================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# =========================
# JWT FUNCTIONS
# =========================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:

    payload = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload.update({
        "exp": expire
    })

    return jwt.encode(
        payload,
        _secret_key(),
        algorithm=ALGORITHM
    )


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            _secret_key(),
            algorithms=[ALGORITHM]
        )

        return payload

    except (JWTError, RuntimeError):
        return None


# =========================
# EXISTING MEMORY SECURITY
# =========================

def sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    return text.strip()


def is_safe_command(command: str) -> bool:

    dangerous = [
        "rm -rf",
        "format c:",
        "del /f",
        "shutdown",
        "powershell -enc"
    ]

    command_lower = command.lower()

    return not any(
        item in command_lower
        for item in dangerous
    )


def validate_memory(text: str):

    text = sanitize_text(text)

    if not text:
        raise ValueError(
            "Memory cannot be empty"
        )

    return text