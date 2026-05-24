"""Authentication Routes"""
from datetime import datetime, timedelta
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.auth.jwt import create_access_token, get_password_hash, verify_password, generate_referral_code
from pydantic import BaseModel

router = APIRouter()


class GuestLoginRequest(BaseModel):
    name: str
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    referral_code: str = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tier: str
    user_id: str


@router.post("/guest")
async def guest_login(data: GuestLoginRequest, db: AsyncSession = Depends(get_db)):
    """Create or login guest user"""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=data.email,
            name=data.name,
            tier="free",
            referral_code=generate_referral_code(user_id),
            demo_balance=10000.0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Create token
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "tier": user.tier},
        expires_delta=timedelta(days=7)
    )
    
    return TokenResponse(
        access_token=token,
        tier=user.tier,
        user_id=user.id
    )


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register new user with email/password"""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=data.email,
        name=data.name,
        tier="free",
        referral_code=generate_referral_code(user_id),
        demo_balance=10000.0,
    )
    
    # Handle referral
    if data.referral_code:
        result = await db.execute(select(User).where(User.referral_code == data.referral_code))
        referrer = result.scalar_one_or_none()
        if referrer:
            user.referred_by = referrer.id
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "tier": user.tier},
        expires_delta=timedelta(days=7)
    )
    
    return TokenResponse(
        access_token=token,
        tier=user.tier,
        user_id=user.id
    )


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email/password"""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # For demo purposes - in production, store password hash
    # This is a simplified version - add password field to User model for production
    
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "tier": user.tier},
        expires_delta=timedelta(days=7)
    )
    
    return TokenResponse(
        access_token=token,
        tier=user.tier,
        user_id=user.id
    )