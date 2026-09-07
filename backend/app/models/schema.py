import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="VENDOR") # VENDOR, LENDER, ADMIN, ANALYST
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    vendor = relationship("Vendor", back_populates="user", uselist=False)

class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    business_type = Column(String, nullable=False) # e.g., Vegetable Vendor, Tea Stall, Food Cart
    business_description = Column(Text, nullable=True)
    location = Column(String, nullable=False)
    operating_since = Column(String, nullable=True) # e.g., "2021"
    registration_status = Column(String, default="INFORMAL")
    operating_days = Column(Integer, default=6)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="vendor")
    transactions = relationship("Transaction", back_populates="vendor", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="vendor", cascade="all, delete-orphan")
    inventory_items = relationship("Inventory", back_populates="vendor", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="vendor", cascade="all, delete-orphan")
    credit_feature = relationship("CreditFeature", back_populates="vendor", uselist=False, cascade="all, delete-orphan")
    credit_score = relationship("CreditScore", back_populates="vendor", uselist=False, cascade="all, delete-orphan")
    consents = relationship("ConsentRecord", back_populates="vendor", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, default="SALE") # SALE, OTHER_INCOME
    payment_method = Column(String, default="CASH") # CASH, UPI, QR
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="MANUAL") # MANUAL, VOICE, OCR
    confidence_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="transactions")

class Expense(Base):
    __tablename__ = "expenses"

    expense_id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    category = Column(String, nullable=False) # STOCK, UTILITIES, RENT, TRANSPORT, OTHER
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, default="MANUAL") # MANUAL, VOICE, OCR
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="expenses")

class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    item_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="inventory_items")

class Loan(Base):
    __tablename__ = "loans"

    loan_id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    principal = Column(Float, nullable=False)
    interest_rate = Column(Float, default=12.0)
    start_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    repayment_status = Column(String, default="REQUESTED") # REQUESTED, ACTIVE, COMPLETED, DEFAULTED, UNDER_REVIEW
    lender_id = Column(String, nullable=True)
    human_notes = Column(Text, nullable=True)
    human_decision_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="loans")
    repayments = relationship("Repayment", back_populates="loan", cascade="all, delete-orphan")

class Repayment(Base):
    __tablename__ = "repayments"

    repayment_id = Column(String, primary_key=True, default=generate_uuid)
    loan_id = Column(String, ForeignKey("loans.loan_id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    status = Column(String, default="PENDING") # PENDING, PAID, DELAYED
    days_delayed = Column(Integer, default=0)

    loan = relationship("Loan", back_populates="repayments")

class CreditFeature(Base):
    __tablename__ = "credit_features"

    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), primary_key=True)
    revenue_stability = Column(Float, default=0.0)
    revenue_trend = Column(Float, default=0.0)
    transaction_frequency = Column(Float, default=0.0)
    average_transaction = Column(Float, default=0.0)
    expense_ratio = Column(Float, default=0.0)
    cashflow_score = Column(Float, default=0.0)
    operating_day_consistency = Column(Float, default=0.0)
    repayment_score = Column(Float, default=0.0)
    business_stability = Column(Float, default=0.0)
    seasonal_volatility = Column(Float, default=0.0)
    anomaly_score = Column(Float, default=0.0)
    data_quality_score = Column(Float, default=85.0)
    feature_version = Column(String, default="v1.0")
    generated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="credit_feature")

class CreditScore(Base):
    __tablename__ = "credit_scores"

    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), primary_key=True)
    score = Column(Integer, default=650) # 0 to 1000
    risk_category = Column(String, default="MODERATE") # LOW, LOW_MODERATE, MODERATE, HIGH, VERY_HIGH
    repayment_probability = Column(Float, default=0.85) # 0.0 to 1.0
    confidence_level = Column(String, default="HIGH")
    positive_factors = Column(JSON, default=list)
    watch_factors = Column(JSON, default=list)
    sustainable_credit_min = Column(Float, default=15000.0)
    sustainable_credit_max = Column(Float, default=35000.0)
    model_version = Column(String, default="v1.0.0")
    generated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="credit_score")

class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    anomaly_type = Column(String, nullable=False)
    severity = Column(String, default="LOW") # LOW, MEDIUM, HIGH
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    period_days = Column(Integer, default=30)
    expected_revenue = Column(Float, default=0.0)
    expected_expenses = Column(Float, default=0.0)
    expected_cashflow = Column(Float, default=0.0)
    forecast_data = Column(JSON, default=dict)
    generated_at = Column(DateTime, default=datetime.utcnow)

class ConsentRecord(Base):
    __tablename__ = "consent_records"

    consent_id = Column(String, primary_key=True, default=generate_uuid)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    data_type = Column(String, nullable=False) # TRANSACTIONS, EXPENSES, LOANS, PROFILE
    purpose = Column(String, nullable=False) # CREDIT_INTELLIGENCE, PORTFOLIO_MATCHING
    granted = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    vendor = relationship("Vendor", back_populates="consents")

class QuantumRun(Base):
    __tablename__ = "quantum_runs"

    run_id = Column(String, primary_key=True, default=generate_uuid)
    problem_size = Column(Integer, default=0)
    number_of_variables = Column(Integer, default=0)
    qubo_parameters = Column(JSON, default=dict)
    algorithm = Column(String, default="QAOA") # QAOA, CLASSICAL_EXACT_BRUTE_FORCE, CLASSICAL_GREEDY_HEURISTIC
    backend = Column(String, default="qiskit_qasm_simulator")
    num_qubits = Column(Integer, default=0)
    shots = Column(Integer, default=1024)
    objective_value = Column(Float, default=0.0)
    execution_time = Column(Float, default=0.0)
    solution_quality = Column(Float, default=0.0)
    result = Column(JSON, default=dict)
    status = Column(String, default="COMPLETED") # QUEUED, RUNNING, COMPLETED, FAILED, CLASSICAL_FALLBACK
    validation_status = Column(String, default="PASSED") # PASSED, FAILED
    fallback_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PortfolioRun(Base):
    __tablename__ = "portfolio_runs"

    portfolio_id = Column(String, primary_key=True, default=generate_uuid)
    lender_id = Column(String, nullable=False, index=True)
    available_capital = Column(Float, nullable=False)
    risk_limit = Column(Float, default=0.25)
    objective_value = Column(Float, default=0.0)
    selected_vendor_count = Column(Integer, default=0)
    allocated_capital = Column(Float, default=0.0)
    expected_portfolio_return = Column(Float, default=0.0)
    expected_portfolio_risk = Column(Float, default=0.0)
    status = Column(String, default="COMPLETED")
    quantum_run_id = Column(String, ForeignKey("quantum_runs.run_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    allocations = relationship("PortfolioAllocation", back_populates="portfolio", cascade="all, delete-orphan")

class PortfolioAllocation(Base):
    __tablename__ = "portfolio_allocations"

    id = Column(String, primary_key=True, default=generate_uuid)
    portfolio_id = Column(String, ForeignKey("portfolio_runs.portfolio_id"), nullable=False, index=True)
    vendor_id = Column(String, ForeignKey("vendors.vendor_id"), nullable=False, index=True)
    requested_amount = Column(Float, default=0.0)
    allocated_amount = Column(Float, default=0.0)
    predicted_risk = Column(Float, default=0.0)
    expected_return = Column(Float, default=0.0)
    selected = Column(Boolean, default=False)

    portfolio = relationship("PortfolioRun", back_populates="allocations")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="INFO")
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    model_name = Column(String, nullable=False) # HawkerCredit AI Scorer, QAOA QUBO Solver
    version = Column(String, nullable=False)
    accuracy = Column(Float, default=0.89)
    precision = Column(Float, default=0.88)
    recall = Column(Float, default=0.91)
    f1_score = Column(Float, default=0.89)
    roc_auc = Column(Float, default=0.92)
    training_dataset_size = Column(Integer, default=120)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
