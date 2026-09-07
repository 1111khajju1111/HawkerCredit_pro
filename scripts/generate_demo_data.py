import sys
import os
from datetime import datetime, timedelta
import random

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.db.database import SessionLocal, engine, Base
from app.models.schema import User, Vendor, Transaction, Expense, Inventory, Loan, Repayment, CreditFeature, CreditScore, ConsentRecord, AuditLog
from app.core.security import get_password_hash
from app.ai.feature_engineering import compute_vendor_features
from app.ai.scoring_model import predict_credit_score
from app.ai.explainability import generate_explainability
from app.ai.data_quality import calculate_data_quality

def generate_synthetic_dataset():
    print("Initializing Database Schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear previous records
    db.query(AuditLog).delete()
    db.query(ConsentRecord).delete()
    db.query(CreditScore).delete()
    db.query(CreditFeature).delete()
    db.query(Repayment).delete()
    db.query(Loan).delete()
    db.query(Inventory).delete()
    db.query(Expense).delete()
    db.query(Transaction).delete()
    db.query(Vendor).delete()
    db.query(User).delete()
    db.commit()

    print("Generating Seed Users & Roles...")
    # 1. Admin Demo Account
    admin_user = User(
        email="admin@hawkercredit.com",
        phone="9999900000",
        password_hash=get_password_hash("admin123"),
        role="ADMIN"
    )
    db.add(admin_user)

    # 2. Exactly 10 synthetic/demo lender accounts.
    lender_users = []
    for i in range(1, 11):
        email = "lender@hawkercredit.com" if i == 1 else f"lender{i}@hawkercredit.com"
        phone = "9999911111" if i == 1 else f"99999{i:05d}"
        lender_user = User(
            email=email,
            phone=phone,
            password_hash=get_password_hash("lender123"),
            role="LENDER"
        )
        db.add(lender_user)
        lender_users.append(lender_user)

    # 3. Vendor Primary Demo Account
    demo_vendor_user = User(
        email="vendor@hawkercredit.com",
        phone="9876543210",
        password_hash=get_password_hash("vendor123"),
        role="VENDOR"
    )
    db.add(demo_vendor_user)
    db.commit()

    business_types = [
        ("Vegetable Vendor", "Fresh seasonal vegetables, APMC Mandi daily procurement", "Sarojini Nagar Market, Delhi"),
        ("Fruit Stall", "Seasonal & imported fruits, retail street cart", "Dadar Market, Mumbai"),
        ("Chai & Snacks Stall", "Tea, samosas, morning & evening rush stall", "Koramangala, Bengaluru"),
        ("Flower Vendor", "Fresh garlands, temple supplies, daily stock", "Mylapore, Chennai"),
        ("Street Grocery", "Essential spices, dry grains, street kiosk", "Gariahat, Kolkata"),
        ("Clothing Kiosk", "Readymade garments, seasonal apparel", "Commercial Street, Bengaluru"),
        ("Handicraft Vendor", "Handmade souvenirs, artisan items", "Janpath, New Delhi")
    ]

    names = [
        "Ramesh Kumar", "Suresh Sharma", "Anita Devi", "Sunita Verma", "Vikram Singh",
        "Priya Patel", "Rajesh Gupta", "Meena Kumari", "Mohd Imran", "Gurpreet Singh",
        "Deepak Yadav", "Kavita Rao", "Sanjay Joshi", "Pooja Reddy", "Amitabh Das"
    ]

    print("Creating exactly 100 Synthetic Street Vendor Profiles...")
    vendors_list = []

    # Primary Vendor Demo
    v_demo = Vendor(
        user_id=demo_vendor_user.id,
        name="Ramesh Kumar (Demo Vendor)",
        phone="9876543210",
        business_type="Vegetable Vendor",
        business_description="Fresh organic vegetables, APMC Mandi daily procurement",
        location="Sarojini Nagar Market, New Delhi",
        operating_since="2021",
        operating_days=6
    )
    db.add(v_demo)
    db.commit()
    db.refresh(v_demo)
    vendors_list.append(v_demo)

    # 99 Additional Synthetic Vendors
    for i in range(1, 100):
        b_type, b_desc, b_loc = random.choice(business_types)
        v_name = f"{random.choice(names)} ({b_type} #{i+1})"
        v_user = User(
            email=f"vendor{i+1}@hawkercredit.com",
            phone=f"98765{i:05d}",
            password_hash=get_password_hash("vendor123"),
            role="VENDOR"
        )
        db.add(v_user)
        db.commit()

        v = Vendor(
            user_id=v_user.id,
            name=v_name,
            phone=v_user.phone,
            business_type=b_type,
            business_description=b_desc,
            location=b_loc,
            operating_since=str(random.randint(2018, 2023)),
            operating_days=random.choice([5, 6, 7])
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        vendors_list.append(v)

    print("Simulating 60 Days Daily Financial History...")
    now = datetime.utcnow()

    for idx, v in enumerate(vendors_list):
        if idx == 0:
            avg_daily_sales = 4800.0
            loan_req = 30000.0
        elif idx % 4 == 0:
            avg_daily_sales = 2600.0
            loan_req = 20000.0
        else:
            avg_daily_sales = 3400.0 + (idx * 25.0)
            loan_req = 25000.0

        txs_raw = []
        exs_raw = []

        # Generate 60 days of transaction history
        for d in range(60, 0, -1):
            date_time = now - timedelta(days=d)
            if (d % 7) != 0: # 6 operating days per week
                sale_amount = max(600.0, avg_daily_sales + ((d % 5) * 150.0))
                payment_method = "CASH" if d % 2 == 0 else "UPI"
                tx = Transaction(
                    vendor_id=v.vendor_id,
                    amount=round(sale_amount, 2),
                    transaction_type="SALE",
                    payment_method=payment_method,
                    timestamp=date_time,
                    source="MANUAL" if d > 5 else "VOICE",
                    confidence_score=0.98
                )
                db.add(tx)
                txs_raw.append({"amount": sale_amount, "timestamp": date_time})

                # Expenses (45% ratio)
                if d % 2 == 0:
                    exp_amt = round(sale_amount * 0.45, 2)
                    ex = Expense(
                        vendor_id=v.vendor_id,
                        category="STOCK",
                        amount=exp_amt,
                        description="Daily wholesale Mandi stock procurement",
                        timestamp=date_time,
                        source="MANUAL"
                    )
                    db.add(ex)
                    exs_raw.append({"amount": exp_amt, "timestamp": date_time})

        # Inventory Items
        db.add(Inventory(vendor_id=v.vendor_id, item_name="Primary Stock A", category="PRODUCE", quantity=50, unit_cost=30, selling_price=50))

        # Loans & Repayments
        l = Loan(
            vendor_id=v.vendor_id,
            principal=loan_req,
            interest_rate=12.0,
            due_date=now + timedelta(days=120),
            repayment_status="ACTIVE" if idx < 30 else "REQUESTED"
        )
        db.add(l)
        db.commit()

        reps_raw = []
        if idx < 30:
            for r_i in range(1, 4):
                r_date = now - timedelta(days=r_i * 30)
                rep = Repayment(
                    loan_id=l.loan_id,
                    amount=round(loan_req / 4, 2),
                    due_date=r_date,
                    paid_date=r_date,
                    status="PAID",
                    days_delayed=0
                )
                db.add(rep)
                reps_raw.append({"days_delayed": 0})
        db.commit()

        # Deterministic Feature Engineering & Scoring
        feats = compute_vendor_features(txs_raw, exs_raw, reps_raw, vendor_id=v.vendor_id, db=db)
        score_res = predict_credit_score(feats)
        explain_res = generate_explainability(feats)
        dq_res = calculate_data_quality(txs_raw, exs_raw, v.__dict__)

        db.add(CreditFeature(
            vendor_id=v.vendor_id,
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
            data_quality_score=dq_res["data_quality_score"]
        ))

        db.add(CreditScore(
            vendor_id=v.vendor_id,
            score=score_res["score"],
            risk_category=score_res["risk_category"],
            repayment_probability=score_res["repayment_probability"],
            confidence_level=dq_res["confidence_level"],
            positive_factors=explain_res["positive_factors"],
            watch_factors=explain_res["watch_factors"],
            sustainable_credit_min=score_res["sustainable_credit_min"],
            sustainable_credit_max=score_res["sustainable_credit_max"],
            model_version=score_res["model_version"]
        ))

        # Default Active Consents
        db.add(ConsentRecord(vendor_id=v.vendor_id, data_type="TRANSACTIONS", purpose="Credit intelligence profiling", granted=True))
        db.add(ConsentRecord(vendor_id=v.vendor_id, data_type="EXPENSES", purpose="Liquidity assessment", granted=True))
        db.add(ConsentRecord(vendor_id=v.vendor_id, data_type="PORTFOLIO_MATCHING", purpose="Lender portfolio allocation", granted=True))
        db.commit()

    print("Synthetic dataset successfully generated and seeded!")
    print(f"Total Seeded Vendors: {len(vendors_list)}")
    print("Total Seeded Lenders: 10")

if __name__ == "__main__":
    generate_synthetic_dataset()
