"""Persisted credit-model registration for Admin Portal monitoring."""

import os
import joblib
from sqlalchemy.orm import Session

from app.models.schema import ModelVersion

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "models", "credit_rf_model.joblib"
)

MODEL_NAME = "HawkerCredit AI Scorer"
MODEL_VERSION = "v3.0.0-RF-Classifier-Persisted"


def register_persisted_model(db: Session) -> bool:
    """
    Register the metrics embedded in the persisted RandomForest model.

    Idempotent: repeated application startups update the existing version
    instead of inserting duplicate ModelVersion rows.
    """
    if not os.path.exists(MODEL_PATH):
        print(f"Model registration skipped: {MODEL_PATH} not found")
        return False

    try:
        metadata = joblib.load(MODEL_PATH)
        metrics = metadata.get("metrics", {})
        version = metadata.get("version", MODEL_VERSION)

        required = ("accuracy", "precision", "recall", "f1_score", "roc_auc")
        if not all(key in metrics for key in required):
            print("Model registration skipped: persisted model has incomplete metrics")
            return False

        training_samples = int(metadata.get("training_samples", 0))
        # train_model.py uses an 80/20 split from N=2000, so training_samples
        # is 1600 and the complete synthetic evaluation dataset is 2000.
        dataset_size = int(metadata.get("dataset_size", training_samples + 400))

        row = (
            db.query(ModelVersion)
            .filter(ModelVersion.model_name == MODEL_NAME)
            .filter(ModelVersion.version == version)
            .first()
        )

        if row is None:
            row = ModelVersion(
                model_name=MODEL_NAME,
                version=version,
                accuracy=float(metrics["accuracy"]),
                precision=float(metrics["precision"]),
                recall=float(metrics["recall"]),
                f1_score=float(metrics["f1_score"]),
                roc_auc=float(metrics["roc_auc"]),
                training_dataset_size=dataset_size,
                status="ACTIVE",
            )
            db.add(row)
        else:
            row.accuracy = float(metrics["accuracy"])
            row.precision = float(metrics["precision"])
            row.recall = float(metrics["recall"])
            row.f1_score = float(metrics["f1_score"])
            row.roc_auc = float(metrics["roc_auc"])
            row.training_dataset_size = dataset_size
            row.status = "ACTIVE"

        # Only one HawkerCredit scorer version is active at a time.
        (
            db.query(ModelVersion)
            .filter(ModelVersion.model_name == MODEL_NAME)
            .filter(ModelVersion.version != version)
            .update({"status": "INACTIVE"}, synchronize_session=False)
        )

        db.commit()
        print(
            f"Registered persisted model {MODEL_NAME} {version} "
            f"(accuracy={metrics['accuracy']:.4f}, "
            f"precision={metrics['precision']:.4f}, "
            f"recall={metrics['recall']:.4f}, "
            f"f1={metrics['f1_score']:.4f}, "
            f"roc_auc={metrics['roc_auc']:.4f})"
        )
        return True

    except Exception as exc:
        db.rollback()
        print(f"Model registration failed: {exc}")
        return False
