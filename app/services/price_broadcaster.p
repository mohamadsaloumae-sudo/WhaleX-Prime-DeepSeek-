"""Price Broadcaster - WhaleX Prime"""
import asyncio
import logging
import time
from app.core.redis_manager import redis_mgr

log = logging.getLogger("whalex.prices")


async def get_all_prices() -> dict:
    """Fetch all prices from Binance"""
    import httpx
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT"]
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get 24hr ticker for all symbols
            r = await client.get("https://fapi.binance.com/fapi/v1/ticker/24hr")
            data = r.json()
            
            prices = {}
            for item in data:
                sym = item.get("symbol", "")
                if sym in symbols or sym.endswith("USDT"):
                    prices[sym] = {
                        "price": float(item.get("lastPrice", 0)),
                        "change": float(item.get("priceChangePercent", 0)),
                        "volume": float(item.get("quoteVolume", 0)),
                        "high": float(item.get("highPrice", 0)),
                        "low": float(item.get("lowPrice", 0)),
                    }
            
            return prices
    
    except Exception as e:
        log.error(f"Error fetching prices: {e}")
        return {}


_broadcaster_started = False


async def start_price_broadcaster():
    """Start the centralized price broadcaster"""
    global _broadcaster_started
    
    if _broadcaster_started:
        return
    
    _broadcaster_started = True
    log.info("Price Broadcaster started — fetching every 3 seconds")
    
    while True:
        try:
            prices = await get_all_prices()
            
            if prices:
                payload = {
                    "event": "prices",
                    "data": prices,
                    "ts": int(time.time())
                }
                await redis_mgr.publish(redis_mgr.PRICES_CHANNEL, payload)
        
        except Exception as e:
            log.error(f"Price broadcaster error: {e}")
        
        await asyncio.sleep(3)