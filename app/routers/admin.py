"""Admin Routes - WhaleX Prime"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.trade import Trade
from app.models.signal import Signal
from app.models.referral import Referral
from app.core.config import get_settings
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter()
settings = get_settings()


class AdminPasswordRequest(BaseModel):
    password: str


class AdminStatsResponse(BaseModel):
    total_users: int
    pro_users: int
    revenue: float
    signals_today: int
    scan_count: int
    symbols: int
    total_referrals: int


def verify_admin(password: str) -> bool:
    """Verify admin password"""
    return password == settings.ADMIN_PASSWORD


@router.post("/verify")
async def verify_admin_access(data: AdminPasswordRequest):
    """Verify admin password"""
    if verify_admin(data.password):
        return {"status": "verified"}
    raise HTTPException(status_code=401, detail="Invalid admin password")


@router.get("/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get admin statistics (no auth for demo)"""
    # In production, add admin authentication
    
    # Total users
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0
    
    # Pro users
    pro_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.tier == "pro")
    )
    pro_users = pro_users_result.scalar() or 0
    
    # Revenue (simplified - $50 per pro user)
    revenue = pro_users * 50
    
    # Signals today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    signals_today_result = await db.execute(
        select(func.count()).select_from(Signal).where(Signal.created_at >= today_start)
    )
    signals_today = signals_today_result.scalar() or 0
    
    # Total referrals
    referrals_result = await db.execute(
        select(func.count()).select_from(Referral).where(Referral.status == "completed")
    )
    total_referrals = referrals_result.scalar() or 0
    
    return AdminStatsResponse(
        total_users=total_users,
        pro_users=pro_users,
        revenue=revenue,
        signals_today=signals_today,
        scan_count=signals_today,
        symbols=256,  # Number of tracked symbols
        total_referrals=total_referrals,
    )


@router.post("/kill-switch")
async def kill_switch(
    db: AsyncSession = Depends(get_db)
):
    """Emergency kill switch - close all open trades"""
    # Find all open trades
    result = await db.execute(
        select(Trade).where(Trade.status == "open")
    )
    open_trades = result.scalars().all()
    
    # Close all trades
    for trade in open_trades:
        trade.status = "closed"
        trade.closed_at = datetime.utcnow()
        trade.exit_reason = "kill_switch"
    
    await db.commit()
    
    return {
        "status": "activated",
        "trades_closed": len(open_trades),
        "message": f"Kill switch activated - closed {len(open_trades)} trades"
    }