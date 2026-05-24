"""Futures Radar Service - WhaleX Prime"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
from app.core.redis_manager import redis_mgr
from app.models.signal import Signal as DBSignal
from app.core.database import AsyncSessionLocal

log = logging.getLogger("whalex.radar")


@dataclass
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float = 0.0


@dataclass
class MarketTier:
    symbol: str
    volume_24h: float
    tier: str
    max_leverage: float
    min_score: float
    min_confidence: float


@dataclass
class Signal:
    symbol: str
    direction: str
    grade: str
    score: float
    confidence: float
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    leverage: float
    strategies: str
    tier: str = "B"
    radar_type: str = "futures"


CANDLES: Dict[str, list[Candle]] = {}
LAST_SIGNALS: Dict[str, int] = {}
SIGNAL_COOLDOWN = 3600  # 1 hour
ALL_SYMBOLS: List[MarketTier] = []


async def fetch_all_futures_symbols() -> List[MarketTier]:
    """Fetch all futures symbols from Binance"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            # Get exchange info
            r = await c.get("https://fapi.binance.com/fapi/v1/exchangeInfo")
            symbols = [
                s["symbol"] for s in r.json()["symbols"]
                if s["status"] == "TRADING" and s["symbol"].endswith("USDT")
            ]
            
            # Get 24hr ticker
            r2 = await c.get("https://fapi.binance.com/fapi/v1/ticker/24hr")
            vols = {t["symbol"]: float(t["quoteVolume"]) for t in r2.json()}
        
        # Sort by volume
        sym_vols = [(s, vols.get(s, 0)) for s in symbols]
        sym_vols.sort(key=lambda x: x[1], reverse=True)
        
        # Filter minimum volume $5M
        filtered = [(s, v) for s, v in sym_vols if v >= 5_000_000]
        
        # Dynamic tiers based on volume percentiles
        all_vols = [v for _, v in filtered]
        if not all_vols:
            return []
        
        p80 = all_vols[int(len(all_vols) * 0.2)] if len(all_vols) > 5 else all_vols[0]
        p40 = all_vols[int(len(all_vols) * 0.6)] if len(all_vols) > 5 else all_vols[-1]
        
        tiers = []
        for sym, vol in filtered[:100]:  # Limit to top 100
            if vol >= p80:
                t = MarketTier(sym, vol, "S", max_leverage=50, min_score=5.0, min_confidence=70)
            elif vol >= p40:
                t = MarketTier(sym, vol, "A", max_leverage=25, min_score=4.5, min_confidence=65)
            else:
                t = MarketTier(sym, vol, "B", max_leverage=10, min_score=4.0, min_confidence=60)
            tiers.append(t)
        
        log.info(f"Fetched {len(tiers)} symbols — S:{sum(1 for t in tiers if t.tier=='S')} A:{sum(1 for t in tiers if t.tier=='A')} B:{sum(1 for t in tiers if t.tier=='B')}")
        return tiers
    
    except Exception as e:
        log.error(f"fetch_symbols: {e}")
        return []


async def fetch_candles(symbol: str, limit: int = 100) -> List[Candle]:
    """Fetch OHLCV candles from Binance"""
    import httpx
    
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=15m&limit={limit}"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            return [
                Candle(
                    time=int(d[0]),
                    open=float(d[1]),
                    high=float(d[2]),
                    low=float(d[3]),
                    close=float(d[4]),
                    volume=float(d[5]),
                    buy_volume=float(d[9]) if len(d) > 9 else 0
                )
                for d in r.json()
            ]
    except Exception as e:
        log.debug(f"fetch_candles {symbol}: {e}")
        return []


def ema(data: list, p: int) -> list:
    """Calculate Exponential Moving Average"""
    if len(data) < p:
        return [data[-1]] * len(data)
    k = 2 / (p + 1)
    e = sum(data[:p]) / p
    r = [None] * (p - 1) + [e]
    for i in range(p, len(data)):
        e = data[i] * k + e * (1 - k)
        r.append(e)
    return r


def rsi(closes: list, p: int = 14) -> float:
    """Calculate RSI"""
    if len(closes) < p + 1:
        return 50.0
    gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains[-p:]) / p
    avg_loss = sum(losses[-p:]) / p
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(closes: list) -> tuple:
    """Calculate MACD"""
    if len(closes) < 26:
        return 0, 0, 0
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    macd_line = [a - b for a, b in zip(e12[25:], e26[25:]) if a and b]
    if len(macd_line) < 9:
        return 0, 0, 0
    signal = ema(macd_line, 9)
    m = macd_line[-1]
    s = signal[-1] or 0
    return m, s, m - s


def bollinger(closes: list, p: int = 20) -> tuple:
    """Calculate Bollinger Bands"""
    import statistics
    if len(closes) < p:
        return closes[-1], closes[-1], closes[-1], 0
    window = closes[-p:]
    mid = sum(window) / p
    std = statistics.stdev(window)
    return mid + 2 * std, mid, mid - 2 * std, std


def calc_grade(score: float, conf: float) -> str:
    """Calculate signal grade"""
    if score >= 9 and conf >= 85:
        return "S"
    if score >= 7 and conf >= 75:
        return "A"
    if score >= 5 and conf >= 65:
        return "B"
    return "C"


def dynamic_params(candles: list, direction: str, score: float, tier: MarketTier) -> tuple:
    """Calculate dynamic SL/TP based on ATR"""
    price = candles[-1].close
    
    # Simple ATR approximation
    if len(candles) < 15:
        atr = price * 0.02
    else:
        trs = [
            max(candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i-1].close),
                abs(candles[i].low - candles[i-1].close))
            for i in range(1, len(candles))
        ]
        atr = sum(trs[-14:]) / 14
    
    pct = atr / price
    if pct > 0.05:
        lev = 2.0
    elif pct > 0.03:
        lev = 4.0
    elif pct > 0.02:
        lev = 6.0
    elif pct > 0.01:
        lev = 10.0
    elif pct > 0.005:
        lev = 15.0
    else:
        lev = 20.0
    
    lev = min(lev * (1 + score / 20), tier.max_leverage)
    
    if direction == "LONG":
        sl = round(price - atr * 1.5, 6)
        tp1 = round(price + atr * 1.8, 6)
        tp2 = round(price + atr * 3.0, 6)
        tp3 = round(price + atr * 5.0, 6)
    else:
        sl = round(price + atr * 1.5, 6)
        tp1 = round(price - atr * 1.8, 6)
        tp2 = round(price - atr * 3.0, 6)
        tp3 = round(price - atr * 5.0, 6)
    
    return sl, tp1, tp2, tp3, round(min(lev, tier.max_leverage), 1)


def analyze(candles: list, symbol: str, tier: MarketTier) -> Optional[Signal]:
    """Analyze candles and generate signal"""
    if len(candles) < 60:
        return None
    
    closes = [c.close for c in candles]
    price = closes[-1]
    
    # Technical indicators
    rsi_val = rsi(closes)
    macd_line, signal_line, hist = macd(closes)
    bb_upper, bb_mid, bb_lower, bb_std = bollinger(closes)
    
    # Score calculation
    long_score = 0.0
    short_score = 0.0
    long_strats = []
    short_strats = []
    
    # RSI
    if rsi_val < 28:
        long_score += 2.5
        long_strats.append(f"RSI Oversold {rsi_val:.0f}")
    elif rsi_val < 38:
        long_score += 1.5
        long_strats.append(f"RSI Low {rsi_val:.0f}")
    elif rsi_val > 72:
        short_score += 2.5
        short_strats.append(f"RSI Overbought {rsi_val:.0f}")
    elif rsi_val > 62:
        short_score += 1.5
        short_strats.append(f"RSI High {rsi_val:.0f}")
    
    # MACD
    if macd_line > signal_line and hist > 0:
        long_score += 1.5
        long_strats.append("MACD Bullish")
    elif macd_line < signal_line and hist < 0:
        short_score += 1.5
        short_strats.append("MACD Bearish")
    
    # Bollinger Bands
    if price <= bb_lower:
        long_score += 2
        long_strats.append("BB Lower Touch")
    elif price >= bb_upper:
        short_score += 2
        short_strats.append("BB Upper Touch")
    
    # EMA trend
    e20 = ema(closes, 20)[-1] or price
    e50 = ema(closes, 50)[-1] or price
    if price > e20 > e50:
        long_score += 0.5
        long_strats.append("Uptrend EMA")
    elif price < e20 < e50:
        short_score += 0.5
        short_strats.append("Downtrend EMA")
    
    # Determine direction
    if long_score >= tier.min_score and long_score > short_score:
        direction = "LONG"
        score = long_score
        strats = long_strats
    elif short_score >= tier.min_score and short_score > long_score:
        direction = "SHORT"
        score = short_score
        strats = short_strats
    else:
        return None
    
    # Calculate confidence
    confidence = min(score / 16 * 100, 99)
    if confidence < tier.min_confidence:
        return None
    
    grade = calc_grade(score, confidence)
    sl, tp1, tp2, tp3, lev = dynamic_params(candles, direction, score, tier)
    
    return Signal(
        symbol=symbol,
        direction=direction,
        grade=grade,
        score=round(score, 1),
        confidence=round(confidence, 1),
        entry=price,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        leverage=lev,
        strategies="\n".join(strats[:6]),
        tier=tier.tier,
        radar_type="futures"
    )


async def save_and_broadcast(sig: Signal):
    """Save signal to database and broadcast via Redis"""
    # Save to database
    async with AsyncSessionLocal() as db:
        db_sig = DBSignal(
            radar_type=sig.radar_type,
            symbol=sig.symbol,
            direction=sig.direction,
            grade=sig.grade,
            score=sig.score,
            confidence=sig.confidence,
            entry=sig.entry,
            sl=sig.sl,
            tp1=sig.tp1,
            tp2=sig.tp2,
            tp3=sig.tp3,
            leverage=sig.leverage,
            strategies=sig.strategies,
            tier=sig.tier,
        )
        db.add(db_sig)
        await db.commit()
    
    # Broadcast via Redis
    payload = {
        "event": "signal",
        "data": {
            "symbol": sig.symbol,
            "direction": sig.direction,
            "grade": sig.grade,
            "confidence": sig.confidence,
            "entry": sig.entry,
            "sl": sig.sl,
            "tp1": sig.tp1,
            "tp2": sig.tp2,
            "tp3": sig.tp3,
            "leverage": sig.leverage,
            "strategies": sig.strategies,
            "tier": sig.tier,
        }
    }
    await redis_mgr.publish(redis_mgr.SIGNALS_CHANNEL, payload)
    
    log.info(f"Signal: {sig.symbol} {sig.direction} {sig.grade} conf={sig.confidence:.0f}% tier={sig.tier}")


async def analyze_symbol(tier: MarketTier):
    """Analyze a single symbol"""
    candles = await fetch_candles(tier.symbol)
    if not candles:
        return
    
    CANDLES[tier.symbol] = candles
    
    sig = analyze(candles, tier.symbol, tier)
    if not sig:
        return
    
    last = LAST_SIGNALS.get(tier.symbol, 0)
    if time.time() - last < SIGNAL_COOLDOWN:
        return
    
    LAST_SIGNALS[tier.symbol] = int(time.time())
    await save_and_broadcast(sig)


async def run_futures_radar():
    """Main futures radar loop"""
    global ALL_SYMBOLS
    
    log.info("Futures Radar starting...")
    
    # Fetch symbols first time
    ALL_SYMBOLS = await fetch_all_futures_symbols()
    if not ALL_SYMBOLS:
        log.error("No symbols fetched — retrying in 60s")
        await asyncio.sleep(60)
        ALL_SYMBOLS = await fetch_all_futures_symbols()
    
    scan_count = 0
    
    while True:
        try:
            # Update symbols every 6 hours
            if scan_count % 72 == 0 and scan_count > 0:
                ALL_SYMBOLS = await fetch_all_futures_symbols()
            
            log.info(f"Scanning {len(ALL_SYMBOLS)} symbols...")
            
            for tier in ALL_SYMBOLS:
                await analyze_symbol(tier)
                await asyncio.sleep(0.3)  # Rate limiting
            
            scan_count += 1
            log.info(f"Scan #{scan_count} complete — next in 5 min")
        
        except Exception as e:
            log.error(f"Radar loop error: {e}")
        
        await asyncio.sleep(300)  # 5 minutes