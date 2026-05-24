"""User Model"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Telegram
    tg_chat_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tier (free / pro)
    tier: Mapped[str] = mapped_column(String(20), default="free")
    pro_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Referral
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    referred_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Settings
    trading_type: Mapped[str] = mapped_column(String(50), default='["futures","spot"]')
    auto_mode: Mapped[str] = mapped_column(String(20), default="manual")
    selected_platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Statistics
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    # Demo balance
    demo_balance: Mapped[float] = mapped_column(Float, default=10000.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    wallets: Mapped[list["Wallet"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship(back_populates="user")
    referrals_sent: Mapped[list["Referral"]] = relationship(foreign_keys="Referral.referrer_id")
    referrals_received: Mapped[list["Referral"]] = relationship(foreign_keys="Referral.referred_id")