import sqlite3
import os
from contextlib import contextmanager
from app.config import DB_PATH

from pydantic import BaseModel
from typing import Optional

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext


def init_db():
    with get_db() as db:

        db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        db.commit()


@contextmanager
def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    try:
        yield db
    finally:
        db.close()




class MemoryCreate(BaseModel):
    content: str
    category: str = "general"



class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""


class ChatRequest(BaseModel):
    message: str


class MemoryResponse(BaseModel):
    id: int
    content: str
    category: str
    created_at: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# =========================
# SECURITY CONFIGURATION
# =========================

SECRET_KEY = os.getenv("NEXORA_SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


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

def _secret_key() -> str:

    secret_key = os.getenv("NEXORA_SECRET_KEY", "")
    if len(secret_key) < 32:
        raise RuntimeError(
            "NEXORA_SECRET_KEY must contain at least 32 characters"
        )
    return secret_key

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