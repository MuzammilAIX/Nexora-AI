from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.auth_models import Tenant, User
from ..security import hash_password, verify_password, create_access_token
from ..auth_deps import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=2, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    email = req.email.lower()

    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    slug_check = await session.execute(select(Tenant).where(Tenant.slug == req.tenant_slug))
    if slug_check.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Tenant slug already taken")

    tenant = Tenant(name=req.tenant_name, slug=req.tenant_slug)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(req.password),
        role="admin",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(str(user.id), {"tenant_id": str(tenant.id), "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(user.id), "email": user.email, "role": user.role},
        "tenant": {"id": str(tenant.id), "name": tenant.name, "slug": tenant.slug},
    }


@router.post("/login")
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    email = req.email.lower()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        str(user.id),
        {"tenant_id": str(user.tenant_id), "role": user.role},
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(user.id), "email": user.email, "role": user.role},
    }


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
    }
