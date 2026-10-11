from pydantic import BaseModel
from typing import Optional


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
    phone_number: str


class RegistrationVerificationRequest(BaseModel):
    email: str
    code: str


class RegistrationResendRequest(BaseModel):
    email: str


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