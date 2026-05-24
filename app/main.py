"""WhaleX Prime - Main Application Entry Point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.redis_manager import redis_mgr
from app.routers import auth, users, wallet, signals, trade, admin, referral
from app.websocket.manager import websocket_endpoint, start_ws_relay
from app.services.price_broadcaster import start_price_broadcaster
from app.services.futures_radar import run_futures_radar
from app.services.position_manager import run_position_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("whalex")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    log.info("🚀 WhaleX Prime starting...")

    # Initialize database
    await init_db()

    # Connect to Redis
    await redis_mgr.connect()

    # Start background tasks
    await start_price_broadcaster()
    await start_ws_relay()
    await run_futures_radar()
    await run_position_manager()

    log.info("✅ WhaleX Prime ready!")

    yield

    # Shutdown
    log.info("🛑 WhaleX Prime shutting down...")
    await close_db()
    await redis_mgr.close()


app = FastAPI(
    title="WhaleX Prime API",
    description="AI-Powered Crypto Trading Platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(trade.router, prefix="/api/trade", tags=["Trading"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(referral.router, prefix="/api/referral", tags=["Referral"])

# WebSocket endpoint
app.websocket("/ws/live")(websocket_endpoint)


@app.get("/")
async def root():
    return {"name": "WhaleX Prime", "status": "running", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}