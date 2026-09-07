import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'credit_rf_model.joblib')


def train_and_save_model():
    """
    Trains a Scikit-Learn RandomForestClassifier on SYNTHETIC training
    profiles and persists the model file to
    backend/app/ai/models/credit_rf_model.joblib.

    *** IMPORTANT - SYNTHETIC TRAINING DATA DISCLOSURE ***
    Every row used to train this model is procedurally generated (see
    below) from a hand-authored linear formula plus injected label noise.
    NONE of it comes from real hawker-vendor repayment outcomes. This
    model is a demonstration / prototype scoring mechanism only and has
    NOT been validated against real-world repayment data. This is
    reflected in `model_metadata["training_data_type"] == "SYNTHETIC"`
    and surfaced to end users via the credit-profile API disclaimer and
    the admin monitoring dashboard - it should never be presented as a
    production-grade, empirically-validated credit model.

    We use a CLASSIFIER (predicting P(repaid) via `predict_proba`) rather
    than a regressor predicting a continuous "probability" target
    directly, because repayment is fundamentally a binary outcome
    (repaid vs. defaulted/delinquent) - a classifier trained on binary
    labels and read via `predict_proba` is the methodologically correct
    way to estimate that probability, rather than regressing directly
    onto a synthetic continuous proxy value.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    rng = np.random.default_rng(42)  # Fixed seed for reproducible model training
    N = 2000

    # Generate feature dataset
    rev_stab = rng.uniform(20.0, 95.0, N)
    cash_score = rng.uniform(20.0, 95.0, N)
    op_cons = rng.uniform(30.0, 100.0, N)
    rep_score = rng.uniform(40.0, 100.0, N)
    bus_stab = rng.uniform(25.0, 95.0, N)
    exp_ratio = rng.uniform(0.2, 0.8, N)

    # Underlying (synthetic, hand-authored) true repayment probability
    composite = (
        (rev_stab * 0.25) +
        (cash_score * 0.25) +
        (op_cons * 0.20) +
        (rep_score * 0.25) +
        (bus_stab * 0.15) -
        (exp_ratio * 30.0)
    )
    # Logistic reshaping widens separation between "good" and "weak"
    # synthetic profiles so the resulting Bernoulli-sampled labels carry a
    # genuinely learnable signal, rather than being dominated by coin-flip
    # noise near a flat 50/50 midpoint.
    true_prob = 1.0 / (1.0 + np.exp(-0.09 * (composite - 55.0)))
    true_prob = np.clip(true_prob, 0.02, 0.98)

    # Draw BINARY repaid/defaulted labels from that probability (Bernoulli
    # trial per synthetic vendor) - this is what makes classification the
    # methodologically appropriate framing, rather than regressing onto
    # `true_prob` itself (which would let the model "cheat" by learning
    # the generating formula exactly instead of learning from outcomes).
    y = rng.binomial(1, true_prob)

    X = pd.DataFrame({
        "revenue_stability": rev_stab,
        "cashflow_score": cash_score,
        "operating_day_consistency": op_cons,
        "repayment_score": rep_score,
        "business_stability": bus_stab,
        "expense_ratio": exp_ratio
    })

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    rf_model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42, class_weight="balanced")
    rf_model.fit(X_train, y_train)

    proba_test = rf_model.predict_proba(X_test)[:, 1]
    preds_test = rf_model.predict(X_test)

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, proba_test)),
        "accuracy": float(accuracy_score(y_test, preds_test)),
        "precision": float(precision_score(y_test, preds_test, zero_division=0)),
        "recall": float(recall_score(y_test, preds_test, zero_division=0)),
        "f1_score": float(f1_score(y_test, preds_test, zero_division=0)),
        "feature_importances": dict(zip(X.columns, rf_model.feature_importances_.tolist()))
    }

    model_metadata = {
        "model": rf_model,
        "model_type": "RandomForestClassifier",
        "version": "v3.0.0-RF-Classifier-Persisted",
        "training_samples": len(X_train),
        "dataset_size": len(X),
        "test_samples": len(X_test),
        "features": list(X.columns),
        "training_data_type": "SYNTHETIC",
        "training_data_disclosure": (
            "Trained entirely on procedurally generated synthetic vendor profiles "
            "with Bernoulli-sampled repay/default labels; not derived from real "
            "hawker vendor repayment history."
        ),
        "metrics": metrics
    }

    joblib.dump(model_metadata, MODEL_PATH)
    print(f"RandomForestClassifier Credit Model trained and saved to {MODEL_PATH}")
    print(f"Evaluation Metrics - ROC AUC: {metrics['roc_auc']:.4f}, F1: {metrics['f1_score']:.4f}")
    return model_metadata


if __name__ == "__main__":
    train_and_save_model()
