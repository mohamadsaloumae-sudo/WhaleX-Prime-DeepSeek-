"""Trading Routes - WhaleX Prime"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.trade import Trade
from app.models.signal import Signal
from app.dependencies import get_current_user, get_current_pro_user
from app.core.config import get_settings
from app.services.position_manager import add_position, Position
from app.services.telegram import TG
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
settings = get_settings()


class ExecuteTradeRequest(BaseModel):
    symbol: str
    direction: str  # LONG or SHORT
    amount: float
    leverage: float
    account_type: str = "demo"  # demo or live


class ForceStopRequest(BaseModel):
    symbol: str


class TradeStatsResponse(BaseModel):
    total_trades: int
    total_pnl: float
    win_rate: float
    demo_balance: float


async def get_current_price(symbol: str) -> float:
    """Get current price from Binance"""
    import httpx
    try:
        sym = symbol.replace("/", "").replace("-", "")
        if not sym.endswith("USDT"):
            sym += "USDT"
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={sym}")
            return float(r.json()["price"])
    except Exception:
        return 0.0


@router.post("/execute")
async def execute_trade(
    data: ExecuteTradeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a trade (demo or live)"""
    
    # Get current price
    price = await get_current_price(data.symbol)
    if price == 0:
        raise HTTPException(status_code=400, detail="Cannot get current price")
    
    # Check balance for demo
    if data.account_type == "demo":
        required_margin = data.amount * data.leverage
        if current_user.demo_balance < required_margin:
            raise HTTPException(status_code=400, detail="Insufficient demo balance")
        
        # Deduct balance
        current_user.demo_balance -= required_margin
    
    # Calculate SL and TP based on leverage
    atr_pct = 0.02  # 2% ATR assumption
    if data.direction == "LONG":
        sl = round(price * (1 - atr_pct * data.leverage / 10), 6)
        tp1 = round(price * (1 + atr_pct * data.leverage / 6), 6)
        tp2 = round(price * (1 + atr_pct * data.leverage / 4), 6)
        tp3 = round(price * (1 + atr_pct * data.leverage / 3), 6)
    else:
        sl = round(price * (1 + atr_pct * data.leverage / 10), 6)
        tp1 = round(price * (1 - atr_pct * data.leverage / 6), 6)
        tp2 = round(price * (1 - atr_pct * data.leverage / 4), 6)
        tp3 = round(price * (1 - atr_pct * data.leverage / 3), 6)
    
    # Create trade record
    trade_id = str(uuid.uuid4())
    trade = Trade(
        id=trade_id,
        user_id=current_user.id,
        symbol=data.symbol,
        direction=data.direction,
        entry_price=price,
        amount=data.amount,
        leverage=data.leverage,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        status="open",
    )
    db.add(trade)
    
    # Update user stats
    current_user.total_trades += 1
    await db.commit()
    
    # Add to position manager (if live mode)
    if data.account_type == "live":
        position = Position(
            id=trade_id,
            user_id=current_user.id,
            symbol=data.symbol,
            direction=data.direction,
            entry=price,
            amount=data.amount,
            leverage=data.leverage,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
        )
        await add_position(position)
    
    # Send Telegram notification
    background_tasks.add_task(
        TG.send_trade_notification,
        current_user,
        data.symbol,
        data.direction,
        price,
        data.leverage,
        data.account_type
    )
    
    return {
        "status": "executed",
        "trade_id": trade_id,
        "entry_price": price,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
    }


@router.post("/force-stop")
async def force_stop_trade(
    data: ForceStopRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Force stop auto trading for a symbol"""
    # Get open trades for this symbol
    result = await db.execute(
        select(Trade).where(
            Trade.user_id == current_user.id,
            Trade.symbol == data.symbol,
            Trade.status == "open"
        )
    )
    trades = result.scalars().all()
    
    for trade in trades:
        trade.status = "cancelled"
        trade.closed_at = datetime.utcnow()
    
    await db.commit()
    
    return {"status": "stopped", "trades_closed": len(trades)}


@router.get("/stats")
async def get_trade_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user trading statistics"""
    result = await db.execute(
        select(Trade).where(
            Trade.user_id == current_user.id,
            Trade.status == "closed"
        )
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


@router.get("/history")
async def get_trade_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """Get user trade history"""
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == current_user.id)
        .order_by(Trade.opened_at.desc())
        .limit(limit)
    )
    trades = result.scalars().all()
    
    return {
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "amount": t.amount,
                "leverage": t.leverage,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "status": t.status,
                "opened_at": t.opened_at.isoformat(),
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in trades
        ]
    }