"""Position Manager - WhaleX Prime"""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum

log = logging.getLogger("whalex.pm")


class ExitReason(Enum):
    SL_HIT = "sl_hit"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    EXPLOSION = "explosion"
    TACTICAL = "tactical_exit"


@dataclass
class Position:
    id: str
    user_id: str
    symbol: str
    direction: str
    entry: float
    amount: float
    leverage: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    tier: str = "B"
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    trailing_active: bool = False
    trailing_sl: float = 0.0
    explosion_mode: bool = False
    peak_price: float = 0.0
    status: str = "open"


# Active positions
ACTIVE: Dict[str, Position] = {}
STATS = {
    "total": 0, "wins": 0, "losses": 0, "tactical": 0,
    "tp1_count": 0, "tp2_count": 0, "tp3_count": 0,
}


async def add_position(pos: Position):
    """Add position to active tracking"""
    pos.peak_price = pos.entry
    ACTIVE[pos.id] = pos
    log.info(f"Position added: {pos.symbol} {pos.direction} @{pos.entry}")


async def remove_position(pos_id: str):
    """Remove position from tracking"""
    ACTIVE.pop(pos_id, None)


async def get_current_price(symbol: str) -> Optional[float]:
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
        return None


async def close_position(pos: Position, exit_price: float, reason: ExitReason):
    """Close position and update stats"""
    is_long = pos.direction == "LONG"
    pnl_pct = (exit_price - pos.entry) / pos.entry * 100 * (1 if is_long else -1)
    
    # Update stats
    STATS["total"] += 1
    if pnl_pct > 0:
        STATS["wins"] += 1
    else:
        STATS["losses"] += 1
    
    if reason == ExitReason.TACTICAL:
        STATS["tactical"] += 1
    elif reason == ExitReason.TP1_HIT:
        STATS["tp1_count"] += 1
    elif reason == ExitReason.TP2_HIT:
        STATS["tp2_count"] += 1
    elif reason in (ExitReason.TP3_HIT, ExitReason.EXPLOSION):
        STATS["tp3_count"] += 1
    
    pos.status = "closed"
    await remove_position(pos.id)
    
    log.info(f"Position closed: {pos.symbol} {pos.direction} PnL={pnl_pct:.2f}% Reason={reason.value}")


async def monitor_position(pos: Position):
    """Monitor a single position"""
    price = await get_current_price(pos.symbol)
    if not price:
        return
    
    is_long = pos.direction == "LONG"
    pnl_pct = (price - pos.entry) / pos.entry * 100 * (1 if is_long else -1)
    
    # Update peak
    if is_long:
        if price > pos.peak_price:
            pos.peak_price = price
    else:
        if pos.peak_price == 0 or price < pos.peak_price:
            pos.peak_price = price
    
    # Explosion mode - close at peak
    if pos.explosion_mode:
        if is_long:
            if price < pos.peak_price * 0.97:  # 3% drop from peak
                await close_position(pos, price, ExitReason.EXPLOSION)
        else:
            if price > pos.peak_price * 1.03:  # 3% rise from bottom
                await close_position(pos, price, ExitReason.EXPLOSION)
        return
    
    # Check SL
    current_sl = pos.trailing_sl if pos.trailing_active and pos.trailing_sl > 0 else pos.sl
    sl_hit = (price <= current_sl) if is_long else (price >= current_sl)
    
    if sl_hit:
        await close_position(pos, price, ExitReason.SL_HIT)
        return
    
    # Check TP1
    tp1_hit = (price >= pos.tp1) if is_long else (price <= pos.tp1)
    if tp1_hit and not pos.tp1_hit:
        pos.tp1_hit = True
        pos.trailing_active = True
        pos.trailing_sl = pos.entry
        log.info(f"TP1 hit: {pos.symbol} +{abs(pnl_pct):.2f}%")
        return
    
    # Check TP2
    tp2_hit = (price >= pos.tp2) if is_long else (price <= pos.tp2)
    if tp2_hit and pos.tp1_hit and not pos.tp2_hit:
        pos.tp2_hit = True
        pos.trailing_sl = pos.tp1
        log.info(f"TP2 hit: {pos.symbol} +{abs(pnl_pct):.2f}%")
        return
    
    # Check TP3
    tp3_hit = (price >= pos.tp3) if is_long else (price <= pos.tp3)
    if tp3_hit and pos.tp2_hit and not pos.tp3_hit:
        pos.tp3_hit = True
        
        # Check for explosion (20% beyond TP3)
        tp3_move = abs(pos.tp3 - pos.entry) / pos.entry * 100
        if abs(pnl_pct) > tp3_move * 1.2:
            pos.explosion_mode = True
            log.info(f"Explosion mode activated: {pos.symbol}")
        else:
            await close_position(pos, price, ExitReason.TP3_HIT)
        return
    
    # Update trailing stop
    if pos.trailing_active and pos.trailing_sl > 0:
        if is_long:
            new_sl = price - (pos.tp1 - pos.entry) * 0.5
            if new_sl > pos.trailing_sl:
                pos.trailing_sl = new_sl
        else:
            new_sl = price + (pos.entry - pos.tp1) * 0.5
            if new_sl < pos.trailing_sl:
                pos.trailing_sl = new_sl


async def run_position_manager():
    """Main position manager loop"""
    log.info("Position Manager started")
    
    while True:
        try:
            positions = list(ACTIVE.values())
            for pos in positions:
                if pos.status == "open":
                    await monitor_position(pos)
                    await asyncio.sleep(0.3)
            
            if not positions:
                await asyncio.sleep(10)
        
        except Exception as e:
            log.error(f"Position Manager error: {e}")
        
        await asyncio.sleep(5)