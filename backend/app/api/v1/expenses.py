from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import Expense
from app.schemas.dto import ExpenseCreate, ExpenseResponse
from app.api.v1.transactions import refresh_vendor_credit
from app.core.security import verify_vendor_access

router = APIRouter()


@router.post("", response_model=ExpenseResponse)
def create_expense(
    vendor_id: str,
    exp_in: ExpenseCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    expense = Expense(
        vendor_id=vendor_id,
        category=exp_in.category,
        amount=exp_in.amount,
        description=exp_in.description,
        source=exp_in.source
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    refresh_vendor_credit(vendor_id, db)
    return expense


@router.get("/{vendor_id}", response_model=List[ExpenseResponse])
def get_vendor_expenses(
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    return db.query(Expense).filter(Expense.vendor_id == vendor_id).order_by(Expense.timestamp.desc()).all()
