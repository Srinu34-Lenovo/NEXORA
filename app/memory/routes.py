from fastapi import APIRouter

from app.auth.register import register
from app.auth.login import login

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

router.post("/register")(register)
router.post("/login")(login)