import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from passlib.context import CryptContext

from app.config import settings
from app.database import get_session
from app.auth_deps import get_current_user
from app.database.auth_models import User, Tenant
from app.email_utils import send_verification_email

import uuid as _uuid
import re as _re

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    company_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(user_id: str) -> str:
    from jose import jwt
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@router.post("/signup")
async def signup(
    req: SignupRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    base_name = req.company_name or (req.email.split("@")[0] + " Workspace")
    slug = _re.sub(r"[^a-z0-9]+", "-", base_name.lower()).strip("-") or "workspace"
    slug = f"{slug}-{_uuid.uuid4().hex[:6]}"

    tenant = Tenant(name=base_name, slug=slug)
    session.add(tenant)
    await session.flush()

    new_user = User(
        email=req.email,
        password_hash=pwd_context.hash(req.password),
        tenant_id=tenant.id,
        email_verified=False,
    )

    verify_token = secrets.token_urlsafe(32)
    new_user.verification_token = verify_token
    new_user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)

    session.add(new_user)
    await session.commit()

    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={verify_token}"

    def _send():
        try:
            send_verification_email(req.email, verify_link)
            print(f"[signup] Verification email sent to {req.email}")
        except Exception as e:
            print(f"[signup] Email send FAILED for {req.email}: {e}")

    background_tasks.add_task(_send)
    return {"message": "Account created. Check your email to verify before logging in."}


@router.get("/verify-email")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token expired")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await session.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Check your inbox.",
        )

    return {"access_token": create_access_token(str(user.id)), "token_type": "bearer"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": getattr(user, "role", "admin"),
        "tenant_id": str(user.tenant_id) if getattr(user, "tenant_id", None) else "",
        "tenant_name": "",
    }