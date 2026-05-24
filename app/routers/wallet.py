"""Wallet Routes"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.wallet import Wallet, Transaction
from app.models.user import User
from app.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class GenerateWalletRequest(BaseModel):
    chain: str


class DepositAddressResponse(BaseModel):
    address: str
    chain: str


class WithdrawRequest(BaseModel):
    chain: str
    address: str
    amount: float
    asset: str = "USDT"


@router.get("/{chain}/address")
async def get_address(
    chain: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get wallet address for specific chain"""
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id, Wallet.chain == chain)
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        # Generate new wallet for this chain
        # In production, call actual blockchain API to create wallet
        wallet_id = str(uuid.uuid4())
        mock_address = f"{chain}_{current_user.id[:8]}_{uuid.uuid4().hex[:16]}"
        
        wallet = Wallet(
            id=wallet_id,
            user_id=current_user.id,
            chain=chain,
            address=mock_address,
            is_default=chain == "sol",
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    
    return DepositAddressResponse(address=wallet.address, chain=chain)


@router.post("/generate")
async def generate_wallet(
    data: GenerateWalletRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate new wallet for a chain"""
    # Check if wallet already exists
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id, Wallet.chain == data.chain)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Wallet for {data.chain} already exists")
    
    wallet_id = str(uuid.uuid4())
    # In production, generate real wallet
    mock_address = f"{data.chain}_{current_user.id[:8]}_{uuid.uuid4().hex[:16]}"
    mock_seed = " ".join([uuid.uuid4().hex[:4] for _ in range(12)])
    
    wallet = Wallet(
        id=wallet_id,
        user_id=current_user.id,
        chain=data.chain,
        address=mock_address,
        encrypted_private_key="encrypted_" + mock_seed[:20],
    )
    db.add(wallet)
    await db.commit()
    
    return {
        "address": mock_address,
        "seed_phrase": mock_seed,  # In production, never return seed phrase after creation
    }


@router.post("/withdraw")
async def withdraw(
    data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Withdraw funds (simulated)"""
    # Check balance
    if current_user.demo_balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    fee = data.amount * 0.01  # 1% fee
    net_amount = data.amount - fee
    
    # Update balance
    current_user.demo_balance -= data.amount
    await db.commit()
    
    return {
        "status": "pending",
        "amount": data.amount,
        "fee": fee,
        "net_amount": net_amount,
    }