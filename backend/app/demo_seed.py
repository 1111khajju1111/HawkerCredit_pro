"""
Idempotent synthetic demo-data seeder.

Enabled only when DEMO_SEED_ON_STARTUP=true.

The seed is intentionally additive:
- ensures 10 lender accounts;
- ensures 100 vendor profiles when starting below that count;
- gives newly-created/empty demo vendors 60 days of synthetic activity;
- creates consent, loan/repayment, feature and credit-score records;
- never clears existing database rows.

The credit model remains explicitly SYNTHETIC and is not presented as
validated real-world repayment performance.
"""

import os
import random
from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.models.schema import (
    User, Vendor, Transaction, Expense, Inventory, Loan, Repayment,
    CreditFeature, CreditScore, ConsentRecord
)
from app.core.security import get_password_hash
from app.ai.feature_engineering import compute_vendor_features
from app.ai.scoring_model import predict_credit_score
from app.ai.explainability import generate_explainability
from app.ai.data_quality import calculate_data_quality


TARGET_VENDORS = 100
TARGET_LENDERS = 10
DEMO_PASSWORD = "lender123"
VENDOR_PASSWORD = "vendor123"

BUSINESS_TYPES = [
    ("Vegetable Vendor", "Fresh seasonal vegetables, APMC Mandi daily procurement", "Sarojini Nagar Market, Delhi"),
    ("Fruit Stall", "Seasonal & imported fruits, retail street cart", "Dadar Market, Mumbai"),
    ("Chai & Snacks Stall", "Tea, samosas, morning & evening rush stall", "Koramangala, Bengaluru"),
    ("Flower Vendor", "Fresh garlands, temple supplies, daily stock", "Mylapore, Chennai"),
    ("Street Grocery", "Essential spices, dry grains, street kiosk", "Gariahat, Kolkata"),
    ("Clothing Kiosk", "Readymade garments, seasonal apparel", "Commercial Street, Bengaluru"),
    ("Handicraft Vendor", "Handmade souvenirs, artisan items", "Janpath, New Delhi"),
]

NAMES = [
    "Ramesh Kumar", "Suresh Sharma", "Anita Devi", "Sunita Verma",
    "Vikram Singh", "Priya Patel", "Rajesh Gupta", "Meena Kumari",
    "Mohd Imran", "Gurpreet Singh", "Deepak Yadav", "Kavita Rao",
    "Sanjay Joshi", "Pooja Reddy", "Amitabh Das",
]


# Every demo account of a given role shares the SAME known, publicly
# documented throwaway password ("vendor123" / "lender123" / "admin123") -
# there is no per-account secret being protected here. bcrypt is
# deliberately slow (by design, for real password security) - at the
# standard cost factor it takes ~250-300ms PER HASH, which is exactly
# right for a real user password but means hashing the same demo password
# 100+ times serially at cold start turned a few seconds of real seeding
# work into 30+ seconds of pure bcrypt overhead. Since these are demo
# credentials (not protecting anything sensitive), the hash is computed
# ONCE per distinct plaintext password and reused - this has no effect on
# `get_password_hash()` itself, which every REAL signup still goes through
# at full cost and with its own random salt.
_DEMO_PASSWORD_HASH_CACHE: dict = {}


def _demo_password_hash(password: str) -> str:
    if password not in _DEMO_PASSWORD_HASH_CACHE:
        _DEMO_PASSWORD_HASH_CACHE[password] = get_password_hash(password)
    return _DEMO_PASSWORD_HASH_CACHE[password]


def _ensure_user(db, email, phone, password, role):
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user, False
    user = User(
        email=email,
        phone=phone,
        password_hash=_demo_password_hash(password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user, True


def _ensure_lenders(db):
    for i in range(1, TARGET_LENDERS + 1):
        email = "lender@hawkercredit.com" if i == 1 else f"lender{i}@hawkercredit.com"
        phone = "9999911111" if i == 1 else f"99999{i:05d}"
        _ensure_user(db, email, phone, DEMO_PASSWORD, "LENDER")


def _ensure_admin(db):
    _ensure_user(db, "admin@hawkercredit.com", "9999900000", "admin123", "ADMIN")


def _ensure_vendor_users_and_profiles(db):
    """Return all vendors, creating enough to reach TARGET_VENDORS."""
    vendors = db.query(Vendor).order_by(Vendor.created_at.asc()).all()

    # Keep an existing vendor account/profile untouched.
    if len(vendors) >= TARGET_VENDORS:
        return vendors

    # Ensure the canonical demo vendor exists.
    demo_user, _ = _ensure_user(
        db, "vendor@hawkercredit.com", "9876543210", VENDOR_PASSWORD, "VENDOR"
    )
    demo_vendor = db.query(Vendor).filter(Vendor.user_id == demo_user.id).first()
    if demo_vendor is None:
        demo_vendor = Vendor(
            user_id=demo_user.id,
            name="Ramesh Kumar (Demo Vendor)",
            phone="9876543210",
            business_type="Vegetable Vendor",
            business_description="Fresh organic vegetables, APMC Mandi daily procurement",
            location="Sarojini Nagar Market, New Delhi",
            operating_since="2021",
            operating_days=6,
        )
        db.add(demo_vendor)
        db.flush()

    vendors = db.query(Vendor).order_by(Vendor.created_at.asc()).all()

    next_index = 2
    while len(vendors) < TARGET_VENDORS:
        email = f"vendor{next_index}@hawkercredit.com"
        phone = f"98765{next_index:05d}"
        user, _ = _ensure_user(db, email, phone, VENDOR_PASSWORD, "VENDOR")

        existing = db.query(Vendor).filter(Vendor.user_id == user.id).first()
        if existing is None:
            b_type, b_desc, b_loc = random.choice(BUSINESS_TYPES)
            vendor = Vendor(
                user_id=user.id,
                name=f"{random.choice(NAMES)} ({b_type} #{next_index})",
                phone=phone,
                business_type=b_type,
                business_description=b_desc,
                location=b_loc,
                operating_since=str(random.randint(2018, 2023)),
                operating_days=random.choice([5, 6, 7]),
            )
            db.add(vendor)
            db.flush()
            vendors.append(vendor)

        next_index += 1

    return db.query(Vendor).order_by(Vendor.created_at.asc()).all()


def _seed_vendor_financials(db, vendor, idx, now):
    """Populate an empty vendor with deterministic synthetic demo activity."""
    existing_tx_count = db.query(Transaction).filter(
        Transaction.vendor_id == vendor.vendor_id
    ).count()

    # Existing vendors with activity are not duplicated.
    if existing_tx_count > 0:
        return False

    avg_daily_sales = 4800.0 if idx == 0 else (
        2600.0 if idx % 4 == 0 else 3400.0 + (idx * 25.0)
    )
    loan_req = 30000.0 if idx == 0 else (20000.0 if idx % 4 == 0 else 25000.0)

    txs_raw = []
    exs_raw = []

    for d in range(60, 0, -1):
        date_time = now - timedelta(days=d)
        if d % 7 != 0:
            sale_amount = max(600.0, avg_daily_sales + ((d % 5) * 150.0))
            payment_method = "CASH" if d % 2 == 0 else "UPI"
            db.add(Transaction(
                vendor_id=vendor.vendor_id,
                amount=round(sale_amount, 2),
                transaction_type="SALE",
                payment_method=payment_method,
                timestamp=date_time,
                source="MANUAL" if d > 5 else "VOICE",
                confidence_score=0.98,
            ))
            txs_raw.append({"amount": sale_amount, "timestamp": date_time})

            if d % 2 == 0:
                exp_amt = round(sale_amount * 0.45, 2)
                db.add(Expense(
                    vendor_id=vendor.vendor_id,
                    category="STOCK",
                    amount=exp_amt,
                    description="Daily wholesale Mandi stock procurement",
                    timestamp=date_time,
                    source="MANUAL",
                ))
                exs_raw.append({"amount": exp_amt, "timestamp": date_time})

    db.add(Inventory(
        vendor_id=vendor.vendor_id,
        item_name="Primary Stock A",
        category="PRODUCE",
        quantity=50,
        unit_cost=30,
        selling_price=50,
    ))

    loan = Loan(
        vendor_id=vendor.vendor_id,
        principal=loan_req,
        interest_rate=12.0,
        due_date=now + timedelta(days=120),
        repayment_status="ACTIVE" if idx < 30 else "REQUESTED",
    )
    db.add(loan)
    db.flush()

    reps_raw = []
    if idx < 30:
        for r_i in range(1, 4):
            r_date = now - timedelta(days=r_i * 30)
            db.add(Repayment(
                loan_id=loan.loan_id,
                amount=round(loan_req / 4, 2),
                due_date=r_date,
                paid_date=r_date,
                status="PAID",
                days_delayed=0,
            ))
            reps_raw.append({"days_delayed": 0})

    # Synthetic demo consent is explicitly granted BEFORE feature
    # computation because compute_vendor_features fails closed when consent
    # is absent.
    for data_type, purpose in [
        ("TRANSACTIONS", "Credit intelligence profiling"),
        ("EXPENSES", "Liquidity assessment"),
        ("PORTFOLIO_MATCHING", "Lender portfolio allocation"),
    ]:
        consent = db.query(ConsentRecord).filter(
            ConsentRecord.vendor_id == vendor.vendor_id,
            ConsentRecord.data_type == data_type,
        ).first()
        if consent is None:
            db.add(ConsentRecord(
                vendor_id=vendor.vendor_id,
                data_type=data_type,
                purpose=purpose,
                granted=True,
            ))

    # Flush transaction/expense/consent rows so feature computation sees them.
    db.flush()

    feats = compute_vendor_features(
        txs_raw, exs_raw, reps_raw, vendor_id=vendor.vendor_id, db=db
    )
    score_res = predict_credit_score(feats)
    explain_res = generate_explainability(feats)
    dq_res = calculate_data_quality(txs_raw, exs_raw, vendor.__dict__)

    existing_feature = db.query(CreditFeature).filter(
        CreditFeature.vendor_id == vendor.vendor_id
    ).first()
    if existing_feature is None:
        db.add(CreditFeature(
            vendor_id=vendor.vendor_id,
            revenue_stability=feats["revenue_stability"],
            revenue_trend=feats["revenue_trend"],
            transaction_frequency=feats["transaction_frequency"],
            average_transaction=feats["average_transaction"],
            expense_ratio=feats["expense_ratio"],
            cashflow_score=feats["cashflow_score"],
            operating_day_consistency=feats["operating_day_consistency"],
            repayment_score=feats["repayment_score"],
            business_stability=feats["business_stability"],
            seasonal_volatility=feats["seasonal_volatility"],
            anomaly_score=feats["anomaly_score"],
            data_quality_score=dq_res["data_quality_score"],
        ))

    existing_score = db.query(CreditScore).filter(
        CreditScore.vendor_id == vendor.vendor_id
    ).first()
    if existing_score is None:
        db.add(CreditScore(
            vendor_id=vendor.vendor_id,
            score=score_res["score"],
            risk_category=score_res["risk_category"],
            repayment_probability=score_res["repayment_probability"],
            confidence_level=dq_res["confidence_level"],
            positive_factors=explain_res["positive_factors"],
            watch_factors=explain_res["watch_factors"],
            sustainable_credit_min=score_res["sustainable_credit_min"],
            sustainable_credit_max=score_res["sustainable_credit_max"],
            model_version=score_res["model_version"],
        ))

    return True


def ensure_demo_dataset():
    # Stable synthetic dataset generation for reproducible hackathon demos.
    random.seed(20260907)
    db = SessionLocal()
    try:
        _ensure_admin(db)
        _ensure_lenders(db)
        vendors = _ensure_vendor_users_and_profiles(db)
        db.commit()

        now = datetime.utcnow()
        seeded = 0
        for idx, vendor in enumerate(vendors):
            if _seed_vendor_financials(db, vendor, idx, now):
                seeded += 1

        db.commit()
        lender_count = db.query(User).filter(User.role == "LENDER").count()
        vendor_count = db.query(Vendor).count()
        print(
            f"Synthetic demo dataset ready: vendors={vendor_count}, "
            f"lenders={lender_count}, newly_seeded_vendor_profiles={seeded}"
        )
        return {"vendors": vendor_count, "lenders": lender_count, "newly_seeded": seeded}
    except Exception as exc:
        db.rollback()
        print(f"Demo data seeding failed: {exc}")
        raise
    finally:
        db.close()
