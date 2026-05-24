"""Telegram Bot Service - WhaleX Prime"""
import asyncio
import logging
from typing import Optional
from app.core.config import get_settings

log = logging.getLogger("whalex.telegram")
settings = get_settings()


class TelegramService:
    """Telegram bot for notifications"""
    
    def __init__(self):
        self._bot = None
        self._initialized = False
    
    async def _get_bot(self):
        """Initialize bot lazily"""
        if self._initialized:
            return self._bot
        
        if not settings.TELEGRAM_BOT_TOKEN:
            log.warning("Telegram bot token not configured")
            return None
        
        try:
            from telegram import Bot
            self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            self._initialized = True
            log.info("Telegram bot initialized")
        except Exception as e:
            log.error(f"Failed to initialize Telegram bot: {e}")
        
        return self._bot
    
    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML"):
        """Send message to a chat"""
        bot = await self._get_bot()
        if not bot:
            return
        
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        except Exception as e:
            log.error(f"Failed to send Telegram message: {e}")
    
    async def broadcast_signal(self, signal: dict):
        """Broadcast signal to admin chat"""
        if not settings.TELEGRAM_ADMIN_CHAT_ID:
            return
        
        direction_emoji = "🟢 LONG" if signal.get("direction") == "LONG" else "🔴 SHORT"
        grade_emoji = {
            "S": "🔥🔥🔥",
            "A": "🔥🔥",
            "B": "🔥",
            "C": "⚡"
        }.get(signal.get("grade", "C"), "⚡")
        
        msg = (
            f"📡 <b>WhaleX Prime Signal</b>\n"
            f"{'─' * 30}\n"
            f"<b>{signal.get('symbol')}</b> {direction_emoji}\n"
            f"Grade: <b>{grade_emoji} {signal.get('grade')}</b> | Conf: <b>{signal.get('confidence')}%</b>\n"
            f"Leverage: <b>{signal.get('leverage')}x</b>\n"
            f"{'─' * 30}\n"
            f"🎯 Entry: <code>{signal.get('entry')}</code>\n"
            f"🛡 SL: <code>{signal.get('sl')}</code>\n"
            f"🎯 TP1: <code>{signal.get('tp1')}</code>\n"
            f"🎯 TP2: <code>{signal.get('tp2')}</code>\n"
            f"🎯 TP3: <code>{signal.get('tp3')}</code>\n"
            f"{'─' * 30}\n"
            f"💡 <i>{signal.get('strategies', 'No additional info')}</i>"
        )
        
        await self.send_message(settings.TELEGRAM_ADMIN_CHAT_ID, msg)
    
    async def send_trade_notification(self, user, symbol: str, direction: str, price: float, leverage: float, account_type: str):
        """Send trade execution notification"""
        if not settings.TELEGRAM_ADMIN_CHAT_ID:
            return
        
        direction_emoji = "🟢 LONG" if direction == "LONG" else "🔴 SHORT"
        account_emoji = "🎮 DEMO" if account_type == "demo" else "💰 LIVE"
        
        msg = (
            f"💹 <b>Trade Executed</b>\n"
            f"{'─' * 30}\n"
            f"User: <b>{user.name}</b> ({user.email})\n"
            f"Symbol: <b>{symbol}</b> {direction_emoji}\n"
            f"Entry: <code>{price}</code>\n"
            f"Leverage: <b>{leverage}x</b>\n"
            f"Account: {account_emoji}\n"
            f"{'─' * 30}"
        )
        
        await self.send_message(settings.TELEGRAM_ADMIN_CHAT_ID, msg)


# Singleton
TG = TelegramService()