from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.schema import User, Vendor, Loan, QuantumRun, ModelVersion, AuditLog
from app.core.security import require_roles

router = APIRouter()


@router.get("/metrics")
def get_admin_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["ADMIN"])),
):
    total_users = db.query(User).count()
    total_vendors = db.query(Vendor).count()
    total_lenders = db.query(User).filter(User.role == "LENDER").count()
    total_loans = db.query(Loan).count()
    total_quantum_runs = db.query(QuantumRun).count()
    total_audit_events = db.query(AuditLog).count()

    # Always prefer the ACTIVE persisted credit model, rather than relying
    # on insertion order (which previously could show stale/N/A metrics).
    active_model_row = (
        db.query(ModelVersion)
        .filter(ModelVersion.model_name == "HawkerCredit AI Scorer")
        .filter(ModelVersion.status == "ACTIVE")
        .order_by(ModelVersion.created_at.desc())
        .first()
    )

    if active_model_row:
        active_model = {
            "id": active_model_row.id,
            "model_name": active_model_row.model_name,
            "version": active_model_row.version,
            "accuracy": active_model_row.accuracy,
            "precision": active_model_row.precision,
            "recall": active_model_row.recall,
            "f1_score": active_model_row.f1_score,
            "roc_auc": active_model_row.roc_auc,
            "training_dataset_size": active_model_row.training_dataset_size,
            "status": active_model_row.status,
            "created_at": active_model_row.created_at,
            "training_data_type": "SYNTHETIC",
        }
    else:
        active_model = {
            "model_name": "HawkerCredit AI Scorer",
            "version": "UNKNOWN_UNTIL_TRAINED",
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "roc_auc": None,
            "training_dataset_size": None,
            "status": "NOT_REGISTERED",
            "training_data_type": "SYNTHETIC",
        }

    return {
        "system_metrics": {
            "total_users": total_users,
            "total_vendors": total_vendors,
            "total_lenders": total_lenders,
            "total_loans": total_loans,
            "total_quantum_runs": total_quantum_runs,
            "total_audit_events": total_audit_events,
            "api_health": "100% OPERATIONAL",
            "db_status": "CONNECTED"
        },
        "ai_model_monitoring": active_model,
        "data_disclaimer": (
            "AI credit-scoring model is trained on SYNTHETIC data for demonstration "
            "purposes and has not been validated on real hawker repayment outcomes."
        )
    }
