from fastapi import APIRouter, Depends, HTTPException

from typing import List
import uuid

from beanie import PydanticObjectId
from beanie.operators import In

import models
import schemas
from core.dependencies import get_current_user

router = APIRouter(prefix="/contracts", tags=["contracts"])

@router.get("/", response_model=List[schemas.ContractOut])
async def get_my_contracts(
    current_user: models.User = Depends(get_current_user)
):
    """Return only contracts where the current user is buyer or seller."""
    contracts = await models.Contract.find(
        {"$or": [{"buyer_id": str(current_user.id)}, {"seller_id": str(current_user.id)}]}
    ).sort("-created_at").to_list()

    # Batch-load all buyers and sellers to avoid N+1 queries
    user_ids = set()
    for c in contracts:
        if PydanticObjectId.is_valid(c.buyer_id):
            user_ids.add(c.buyer_id)
        if PydanticObjectId.is_valid(c.seller_id):
            user_ids.add(c.seller_id)
    users_list = await models.User.find(
        In(models.User.id, [PydanticObjectId(uid) for uid in user_ids])
    ).to_list()
    users_map = {str(u.id): u for u in users_list}

    result = []
    for c in contracts:
        buyer = users_map.get(str(c.buyer_id))
        seller = users_map.get(str(c.seller_id))
        result.append(schemas.ContractOut(
            id=c.id,
            buyer_id=c.buyer_id,
            seller_id=c.seller_id,
            title=c.title,
            description=c.description,
            amount=c.amount,
            status=c.status,
            created_at=c.created_at,
            buyer_name=buyer.name if buyer else None,
            seller_name=seller.name if seller else None,
        ))
    return result

@router.post("/", response_model=schemas.ContractOut)
async def create_contract(
    contract: schemas.ContractCreate,
    current_user: models.User = Depends(get_current_user)
):
    """Create a new contract. The current user is the seller."""
    from core.errors import E
    buyer = await models.User.get(contract.buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail=E.BUYER_NOT_FOUND)

    new_contract = models.Contract(
        buyer_id=contract.buyer_id,
        seller_id=str(current_user.id),
        title=contract.title,
        description=contract.description,
        amount=contract.amount,
        status=models.ContractStatus.pending,
    )
    await new_contract.insert()

    return schemas.ContractOut(
        id=str(new_contract.id),
        buyer_id=new_contract.buyer_id,
        seller_id=str(new_contract.seller_id),
        title=new_contract.title,
        description=new_contract.description,
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
    current_user: models.User = Depends(get_current_user)
):
    """Update contract status — only accessible to buyer or seller."""
    contract = await models.Contract.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=E.CONTRACT_NOT_FOUND)

    if contract.buyer_id != str(current_user.id) and contract.seller_id != str(current_user.id):
        raise HTTPException(status_code=403, detail=E.ACCESS_DENIED)

    contract.status = status
    await contract.save()
    return {"message": "Status updated", "status": status}
