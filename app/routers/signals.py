"""Signals Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.signal import Signal
from app.dependencies import get_current_user, get_current_pro_user
from app.models.user import User
from typing import Optional

router = APIRouter()


@router.get("/futures")
async def get_futures_signals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Get futures signals"""
    signals = await db.execute(
        select(Signal)
        .where(Signal.radar_type == "futures")
        .order_by(desc(Signal.created_at))
        .limit(limit)
    )
    return {"signals": [s.__dict__ for s in signals.scalars().all()]}


@router.get("/spot")
async def get_spot_signals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Get spot signals"""
    signals = await db.execute(
        select(Signal)
        .where(Signal.radar_type == "spot")
        .order_by(desc(Signal.created_at))
        .limit(limit)
    )
    return {"signals": [s.__dict__ for s in signals.scalars().all()]}


@router.get("/meme")
async def get_meme_signals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Get meme coin signals"""
    signals = await db.execute(
        select(Signal)
        .where(Signal.radar_type == "meme")
        .order_by(desc(Signal.created_at))
        .limit(limit)
    )
    return {"signals": [s.__dict__ for s in signals.scalars().all()]}


@router.get("/latest")
async def get_latest_signals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 5
):
    """Get latest signals from all radars"""
    signals = await db.execute(
        select(Signal)
        .order_by(desc(Signal.created_at))
        .limit(limit)
    )
    return {"signals": [s.__dict__ for s in signals.scalars().all()]}