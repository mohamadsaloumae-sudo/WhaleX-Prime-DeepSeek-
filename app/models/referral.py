"""Referral Models"""
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    referred_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ReferralEarning(Base):
    __tablename__ = "referral_earnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    referral_id: Mapped[int] = mapped_column(Integer, ForeignKey("referrals.id"))
    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(20), default="pro_days")  # pro_days, commission
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)