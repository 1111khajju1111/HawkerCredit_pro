from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import Inventory
from app.schemas.dto import InventoryCreate, InventoryResponse
from app.core.security import verify_vendor_access

router = APIRouter()


@router.post("", response_model=InventoryResponse)
def create_inventory(
    vendor_id: str,
    inv_in: InventoryCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    inv = Inventory(
        vendor_id=vendor_id,
        item_name=inv_in.item_name,
        category=inv_in.category,
        quantity=inv_in.quantity,
        unit_cost=inv_in.unit_cost,
        selling_price=inv_in.selling_price
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/{vendor_id}", response_model=List[InventoryResponse])
def get_vendor_inventory(
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    return db.query(Inventory).filter(Inventory.vendor_id == vendor_id).all()
