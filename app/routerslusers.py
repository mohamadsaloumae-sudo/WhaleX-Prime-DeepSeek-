"""User Routes"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.trade import Trade
from app.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    trading_type: Optional[str] = None
    auto_mode: Optional[str] = None
    selected_platform: Optional[str] = None


class TradeStatsResponse(BaseModel):
    total_trades: int
    total_pnl: float
    win_rate: float
    demo_balance: float


@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "tier": current_user.tier,
        "referral_code": current_user.referral_code,
        "trading_type": current_user.trading_type,
        "auto_mode": current_user.auto_mode,
        "selected_platform": current_user.selected_platform,
        "created_at": current_user.created_at.isoformat(),
    }


@router.put("/me")
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    if data.name:
        current_user.name = data.name
    if data.phone:
        current_user.phone = data.phone
    if data.trading_type:
        current_user.trading_type = data.trading_type
    if data.auto_mode:
        current_user.auto_mode = data.auto_mode
    if data.selected_platform:
        current_user.selected_platform = data.selected_platform
    
    await db.commit()
    return {"status": "updated"}


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user trading statistics"""
    result = await db.execute(
        select(Trade).where(Trade.user_id == current_user.id, Trade.status == "closed")
    )
    trades = result.scalars().all()
    
    total_trades = len(trades)
    total_pnl = sum(t.pnl or 0 for t in trades)
    winning_trades = sum(1 for t in trades if (t.pnl or 0) > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return TradeStatsResponse(
        total_trades=total_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        demo_balance=current_user.demo_balance,
    )