import hashlib
import hmac
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import requests
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.models import (
    LoginRequest,
    RegistrationResendRequest,
    RegistrationVerificationRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    create_access_token,
    ensure_auth_signing_configured,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_CODE_PATTERN = re.compile(r"^\d{6}$")
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def _utc_now():

    return datetime.now(timezone.utc)


def _otp_hash(email: str, code: str) -> str:

    secret = os.getenv("NEXORA_OTP_SECRET", "").encode()
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="Registration verification is not configured.",
        )

    return hmac.new(
        secret,
        f"{email}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _send_email_code(email: str, code: str):

    host = os.getenv("NEXORA_SMTP_HOST")
    sender = os.getenv("NEXORA_SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = "Verify your NEXORA account"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Your NEXORA verification code is {code}. "
        f"It expires in {OTP_TTL_MINUTES} minutes."
    )

    port = int(os.getenv("NEXORA_SMTP_PORT", "587"))
    username = os.getenv("NEXORA_SMTP_USERNAME")
    password = os.getenv("NEXORA_SMTP_PASSWORD")
    use_ssl = os.getenv("NEXORA_SMTP_USE_SSL", "false").lower() == "true"

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            if username:
                server.login(username, password or "")
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            if username:
                server.login(username, password or "")
            server.send_message(message)


def _send_sms_code(phone_number: str, code: str):

    account_sid = os.getenv("NEXORA_TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("NEXORA_TWILIO_AUTH_TOKEN")
    sender = os.getenv("NEXORA_TWILIO_FROM")
    if not account_sid or not auth_token or not sender:
        raise RuntimeError("SMS delivery is not configured")

    response = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        auth=(account_sid, auth_token),
        data={
            "To": phone_number,
            "From": sender,
            "Body": (
                f"Your NEXORA verification code is {code}. "
                f"It expires in {OTP_TTL_MINUTES} minutes."
            ),
        },
        timeout=10,
    )
    response.raise_for_status()


def _deliver_code(email: str, phone_number: str, code: str):

    _send_email_code(email, code)
    _send_sms_code(phone_number, code)


def _new_code() -> str:

    return f"{secrets.randbelow(1_000_000):06d}"


def _send_existing_challenge(email: str, phone_number: str):

    code = _new_code()
    now = _utc_now()
    with get_db() as db:
        db.execute(
            """
            UPDATE registration_challenges
            SET code_hash = ?, expires_at = ?, created_at = ?, attempts = 0
            WHERE email = ?
            """,
            (
                _otp_hash(email, code),
                (now + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
                now.isoformat(),
                email,
            ),
        )
        db.commit()

    try:
        _deliver_code(email, phone_number, code)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Verification code delivery failed. Check email and SMS configuration.",
        ) from error


def _issue_access_token(user_id: int) -> str:

    try:
        return create_access_token({"sub": str(user_id)})
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail="Authentication signing is not configured.",
        ) from error


# ==========================================
# REGISTER
# ==========================================

@router.post("/register")
def register(request: RegisterRequest):

    try:
        ensure_auth_signing_configured()
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail="Authentication signing is not configured.",
        ) from error

    username = request.username.strip()
    email = request.email.strip().lower()

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must contain at least 3 characters",
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters",
        )

    phone_number = request.phone_number.strip()
    if not PHONE_PATTERN.fullmatch(phone_number):
        raise HTTPException(
            status_code=400,
            detail="Phone number must use international E.164 format.",
        )

    code = _new_code()
    now = _utc_now()
    code_hash = _otp_hash(email, code)

    with get_db() as db:

        existing_user = db.execute(
            """
            SELECT id
            FROM users
            WHERE email = ? OR username = ?
            """,
            (email, username),
        ).fetchone()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Username or email already exists",
            )

        password_hash = hash_password(request.password)

        pending = db.execute(
            """
            SELECT username, created_at
            FROM registration_challenges
            WHERE email = ? OR username = ?
            """,
            (email, username),
        ).fetchone()

        if pending:
            raise HTTPException(
                status_code=409,
                detail="A registration verification is already pending.",
            )

        db.execute(
            """
            INSERT INTO registration_challenges (
                email,
                username,
                password_hash,
                phone_number,
                code_hash,
                expires_at,
                created_at,
                attempts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                email,
                username,
                password_hash,
                phone_number,
                code_hash,
                (now + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
                now.isoformat(),
            ),
        )
        db.commit()

    try:
        _deliver_code(email, phone_number, code)
    except Exception as error:
        with get_db() as db:
            db.execute(
                "DELETE FROM registration_challenges WHERE email = ?",
                (email,),
            )
            db.commit()
        raise HTTPException(
            status_code=503,
            detail="Verification code delivery failed. Check email and SMS configuration.",
        ) from error

    return {"message": "Verification code sent to your email and phone."}


@router.post("/register/resend")
def resend_registration_code(request: RegistrationResendRequest):

    email = request.email.strip().lower()
    with get_db() as db:
        challenge = db.execute(
            """
            SELECT phone_number, created_at
            FROM registration_challenges
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if challenge is None:
        raise HTTPException(status_code=404, detail="No pending registration.")

    last_sent = datetime.fromisoformat(challenge["created_at"])
    remaining = OTP_RESEND_COOLDOWN_SECONDS - (
        _utc_now() - last_sent
    ).total_seconds()
    if remaining > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {int(remaining) + 1} seconds before requesting another code.",
        )

    _send_existing_challenge(email, challenge["phone_number"])
    return {"message": "A new verification code was sent."}


@router.post("/register/verify", response_model=TokenResponse)
def verify_registration(request: RegistrationVerificationRequest):

    email = request.email.strip().lower()
    if not OTP_CODE_PATTERN.fullmatch(request.code):
        raise HTTPException(status_code=400, detail="Enter the six-digit code.")

    submitted_hash = _otp_hash(email, request.code)
    now = _utc_now()

    with get_db() as db:
        challenge = db.execute(
            """
            SELECT username, email, password_hash, phone_number,
                   code_hash, expires_at, attempts
            FROM registration_challenges
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if challenge is None:
            raise HTTPException(status_code=400, detail="Invalid or expired verification.")

        if datetime.fromisoformat(challenge["expires_at"]) <= now:
            db.execute(
                "DELETE FROM registration_challenges WHERE email = ?",
                (email,),
            )
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid or expired verification.")

        if challenge["attempts"] >= OTP_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail="Too many incorrect codes. Request a new code.",
            )

        if not hmac.compare_digest(submitted_hash, challenge["code_hash"]):
            db.execute(
                "UPDATE registration_challenges SET attempts = attempts + 1 WHERE email = ?",
                (email,),
            )
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid or expired verification.")

        cursor = db.execute(
            """
            INSERT INTO users (username, email, password_hash, phone_number)
            VALUES (?, ?, ?, ?)
            """,
            (
                challenge["username"],
                email,
                challenge["password_hash"],
                challenge["phone_number"],
            ),
        )
        db.execute(
            "DELETE FROM registration_challenges WHERE email = ?",
            (email,),
        )
        user_id = cursor.lastrowid
        access_token = _issue_access_token(user_id)
        db.commit()

    user = UserResponse(
        id=user_id,
        username=challenge["username"],
        email=email,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


# ==========================================
# LOGIN
# ==========================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(request: LoginRequest):

    email = request.email.strip().lower()

    with get_db() as db:

        user = db.execute(
            """
            SELECT
                id,
                username,
                email,
                password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(
        request.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = _issue_access_token(user["id"])

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
        ),
    )