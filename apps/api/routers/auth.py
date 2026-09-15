from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.database import get_db
from apps.api.models import User, Customer, Tenant
from apps.api.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="Password at least 6 characters")
    name: str = Field(min_length=2)
    role: Optional[str] = "customer"  # customer or operator/admin (if first setup)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(min_length=6)

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    # 1. Ensure a default tenant exists
    t_stmt = select(Tenant).limit(1)
    t_res = await db.execute(t_stmt)
    tenant = t_res.scalars().first()
    if not tenant:
        tenant = Tenant(name="Primary E-Commerce Store", status="active", default_currency="USD")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

    # 2. Check if email exists
    u_stmt = select(User).where(User.email == req.email)
    u_res = await db.execute(u_stmt)
    if u_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    # 3. Create User & Customer record
    pwd_hash = hash_password(req.password)
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        tenant_id=tenant.id,
        email=req.email,
        name=req.name,
        password_hash=pwd_hash,
        role=req.role or "customer"
    )
    db.add(user)

    # Also register customer record if role is customer
    if req.role == "customer":
        cust = Customer(
            id=user_id,
            tenant_id=tenant.id,
            external_id=f"CUST-{req.email.split('@')[0].upper()}",
            name=req.name,
            email=req.email,
            password_hash=pwd_hash,
            attributes={"signup_method": "direct"}
        )
        db.add(cust)

    await db.commit()

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "tenant_id": tenant.id
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": tenant.id
        }
    }

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalars().first()

    # If user doesn't exist, check default admin fallback or seed
    if not user:
        if req.email == "admin@autonomous.store" and req.password == "admin123":
            t_stmt = select(Tenant).limit(1)
            t_res = await db.execute(t_stmt)
            tenant = t_res.scalars().first()
            if not tenant:
                tenant = Tenant(name="Primary E-Commerce Store", status="active", default_currency="USD")
                db.add(tenant)
                await db.commit()
                await db.refresh(tenant)
            user = User(
                email="admin@autonomous.store",
                name="Head of Autonomous Ops",
                password_hash=hash_password("admin123"),
                role="admin",
                tenant_id=tenant.id
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

    if not verify_password(req.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "tenant_id": user.tenant_id
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": user.tenant_id
        }
    }

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_access_token(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")
    
    token_payload = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role"),
        "name": payload.get("name"),
        "tenant_id": payload.get("tenant_id")
    }
    new_access_token = create_access_token(token_payload)
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalars().first()
    # In real world, send email with reset link. For demo/prototype, return simulated reset token.
    reset_token = f"reset-{uuid.uuid4().hex[:8]}"
    return {
        "message": "Password reset instructions sent to your email.",
        "simulated_reset_token": reset_token,
        "exists": bool(user)
    }

@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.password_hash = hash_password(req.new_password)
    await db.commit()
    return {"message": "Password has been successfully reset. Please log in with your new password."}

@router.get("/me")
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "user": current_user,
        "authenticated": True
    }
