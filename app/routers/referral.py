"""Referral Routes - WhaleX Prime"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.referral import Referral, ReferralEarning
from app.dependencies import get_current_user
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/stats")
async def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get referral statistics for current user"""
    
    # Count referrals
    referrals_result = await db.execute(
        select(func.count()).select_from(Referral).where(
            Referral.referrer_id == current_user.id,
            Referral.status == "completed"
        )
    )
    referrals_count = referrals_result.scalar() or 0
    
    # Calculate PRO points (7 days per referral)
    pro_points = referrals_count * 7
    
    # Calculate free days remaining
    free_days = 0
    if current_user.pro_expires_at and current_user.pro_expires_at > datetime.utcnow():
        free_days = (current_user.pro_expires_at - datetime.utcnow()).days
    
    # Get earnings
    earnings_result = await db.execute(
        select(func.sum(ReferralEarning.amount)).where(ReferralEarning.user_id == current_user.id)
    )
    total_earnings = earnings_result.scalar() or 0.0
    
    return {
        "referrals": referrals_count,
        "pro_points": pro_points,
        "free_days": free_days,
        "total_earnings": total_earnings,
    }


@router.get("/code")
async def get_referral_code(
    current_user: User = Depends(get_current_user)
):
    """Get user's referral code"""
    return {"code": current_user.referral_code, "url": f"{settings.REFERRAL_BASE_URL}{current_user.referral_code}"}


@router.post("/redeem")
async def redeem_referral(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Redeem a referral code"""
    
    # Find referrer
    result = await db.execute(select(User).where(User.referral_code == code))
    referrer = result.scalar_one_or_none()
    
    if not referrer:
        return {"status": "error", "message": "Invalid referral code"}
    
    if referrer.id == current_user.id:
        return {"status": "error", "message": "Cannot refer yourself"}
    
    # Check if already referred
    existing = await db.execute(
        select(Referral).where(Referral.referred_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        return {"status": "error", "message": "Already referred"}
    
    # Create referral record
    referral = Referral(
        referrer_id=referrer.id,
        referred_id=current_user.id,
        status="completed",
        completed_at=datetime.utcnow(),
    )
    db.add(referral)
    
    # Give 7 days PRO to referrer
    if referrer.pro_expires_at and referrer.pro_expires_at > datetime.utcnow():
        referrer.pro_expires_at += timedelta(days=7)
    else:
        referrer.pro_expires_at = datetime.utcnow() + timedelta(days=7)
    
    # Upgrade referrer to PRO
    referrer.tier = "pro"
    
    # Create earning record
    earning = ReferralEarning(
        user_id=referrer.id,
        referral_id=referral.id,
        amount=7,
        type="pro_days",
    )
    db.add(earning)
    
    await db.commit()
    
    return {"status": "success", "message": "Referral code redeemed! You got 7 days PRO"}