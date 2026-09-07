from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.schema import AuditLog
from app.core.security import require_roles

router = APIRouter()


@router.get("")
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["ADMIN"])),
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs
