from fastapi import APIRouter, Depends, HTTPException

from typing import List
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from db import get_db
from core.dependencies import get_current_user
from core.errors import E

router = APIRouter(prefix="/contracts", tags=["contracts"])

@router.get("/", response_model=List[schemas.ContractOut])
async def get_my_contracts(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return only contracts where the current user is buyer or seller."""
    result = await db.execute(
        select(models.Contract)
        .where(or_(models.Contract.buyer_id == current_user.id, models.Contract.seller_id == current_user.id))
        .order_by(models.Contract.created_at.desc())
    )
    contracts = result.scalars().all()

    # Batch-load all buyers and sellers to avoid N+1 queries
    user_ids = set()
    for c in contracts:
        user_ids.add(c.buyer_id)
        user_ids.add(c.seller_id)
    users_map: dict = {}
    if user_ids:
        users_result = await db.execute(select(models.User).where(models.User.id.in_(user_ids)))
        users_map = {u.id: u for u in users_result.scalars().all()}

    result_list = []
    for c in contracts:
        buyer = users_map.get(c.buyer_id)
        seller = users_map.get(c.seller_id)
        result_list.append(schemas.ContractOut(
            id=str(c.id),
            buyer_id=str(c.buyer_id),
            seller_id=str(c.seller_id),
            title=c.title,
            terms=c.terms,
            amount=c.amount,
            status=c.status,
            created_at=c.created_at,
            buyer_name=buyer.name if buyer else None,
            seller_name=seller.name if seller else None,
        ))
    return result_list

@router.post("/", response_model=schemas.ContractOut)
async def create_contract(
    contract: schemas.ContractCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new contract. The current user is the seller."""
    try:
        buyer_uuid = uuid.UUID(contract.buyer_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=E.BUYER_NOT_FOUND)

    buyer = await db.get(models.User, buyer_uuid)
    if not buyer:
        raise HTTPException(status_code=404, detail=E.BUYER_NOT_FOUND)

    new_contract = models.Contract(
        buyer_id=buyer_uuid,
        seller_id=current_user.id,
        title=contract.title,
        terms=contract.terms,
        amount=contract.amount,
        status=models.ContractStatus.pending,
    )
    db.add(new_contract)
    await db.commit()
    await db.refresh(new_contract)

    return schemas.ContractOut(
        id=str(new_contract.id),
        buyer_id=str(new_contract.buyer_id),
        seller_id=str(new_contract.seller_id),
        title=new_contract.title,
        terms=new_contract.terms,
        amount=new_contract.amount,
        status=new_contract.status,
        created_at=new_contract.created_at,
        buyer_name=buyer.name,
        seller_name=current_user.name,
    )

@router.put("/{contract_id}/status")
async def update_contract_status(
    contract_id: str,
    status: schemas.ContractStatus,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update contract status — only accessible to buyer or seller."""
    try:
        cid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=E.CONTRACT_NOT_FOUND)

    contract = await db.get(models.Contract, cid)
    if not contract:
        raise HTTPException(status_code=404, detail=E.CONTRACT_NOT_FOUND)

    if contract.buyer_id != current_user.id and contract.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail=E.ACCESS_DENIED)

    contract.status = models.ContractStatus(status.value)
    await db.commit()
    return {"message": "Status updated", "status": status}
