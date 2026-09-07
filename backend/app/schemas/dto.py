from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)
    role: str = "VENDOR"

class StaffRegister(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    vendor_id: Optional[str] = None

# Vendor Schemas
class VendorCreate(BaseModel):
    name: str
    phone: str
    business_type: str
    business_description: Optional[str] = None
    location: str
    operating_since: Optional[str] = "2022"
    operating_days: Optional[int] = 6

class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    vendor_id: str
    user_id: str
    name: str
    phone: str
    business_type: str
    business_description: Optional[str]
    location: str
    operating_since: Optional[str]
    registration_status: str
    operating_days: int
    created_at: datetime
    # Optional lender/admin intelligence fields populated by vendor discovery.
    score: Optional[float] = None
    risk_category: Optional[str] = None
    repayment_probability: Optional[float] = None
    data_quality_score: Optional[float] = None
    requested_loan: Optional[float] = None
    pending_human_review: Optional[bool] = None

# Transaction Schemas
class TransactionCreate(BaseModel):
    amount: float
    transaction_type: str = "SALE"
    payment_method: str = "CASH"
    source: str = "MANUAL"
    confidence_score: float = 1.0

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    vendor_id: str
    amount: float
    transaction_type: str
    payment_method: str
    timestamp: datetime
    source: str
    confidence_score: float

# Expense Schemas
class ExpenseCreate(BaseModel):
    category: str
    amount: float
    description: Optional[str] = None
    source: str = "MANUAL"

class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    expense_id: str
    vendor_id: str
    category: str
    amount: float
    description: Optional[str]
    timestamp: datetime
    source: str

# Inventory Schemas
class InventoryCreate(BaseModel):
    item_name: str
    category: str
    quantity: float
    unit_cost: float
    selling_price: float

class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    inventory_id: str
    vendor_id: str
    item_name: str
    category: str
    quantity: float
    unit_cost: float
    selling_price: float
    timestamp: datetime

# Loan Schemas
class LoanCreate(BaseModel):
    principal: float = Field(gt=0, le=500000)
    interest_rate: float = Field(default=12.0, ge=0, le=100)
    due_months: int = Field(default=6, ge=1, le=60)

class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    loan_id: str
    vendor_id: str
    principal: float
    interest_rate: float
    start_date: datetime
    due_date: datetime
    repayment_status: str
    lender_id: Optional[str]
    human_notes: Optional[str]

class HumanUnderwriteRequest(BaseModel):
    loan_id: str
    decision: str
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        value = value.upper().strip()
        if value not in {"APPROVED", "REJECTED", "UNDER_REVIEW"}:
            raise ValueError("decision must be APPROVED, REJECTED, or UNDER_REVIEW")
        return value

# Voice Transaction Input
class VoiceTransactionInput(BaseModel):
    transcript: str

class VoiceTransactionOutput(BaseModel):
    sales: float
    expenses: float
    category: str
    confidence: float
    raw_transcript: str

# Receipt OCR Output
class ReceiptOCROutput(BaseModel):
    merchant: str
    amount: float
    category: str
    date: str
    confidence: float
    items: List[str]
    extraction_method: str = "DETERMINISTIC_DEMO_FALLBACK"
    raw_text_preview: Optional[str] = None

# Quantum Portfolio Request
class QuantumPortfolioRequest(BaseModel):
    available_capital: float = Field(default=1000000.0, gt=0, le=100000000)
    vendor_ids: Optional[List[str]] = Field(default=None, min_length=1, max_length=10)
    max_exposure_per_vendor: float = Field(default=50000.0, gt=0, le=500000)
    max_risk_tolerance: float = Field(default=0.25, ge=0, le=1)
    max_category_concentration: float = Field(default=0.40, gt=0, le=1)
    p_layers: int = Field(default=2, ge=1, le=4)
    shots: int = Field(default=1024, ge=128, le=8192)
    algorithm: str = "QAOA"

# Quantum Run Response DTO
class QuantumRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_id: str
    problem_size: int
    number_of_variables: int
    num_vendor_qubits: Optional[int] = None
    algorithm: str
    backend: str
    num_qubits: int
    p_layers: int
    circuit_depth: int
    optimized_gamma: Optional[List[float]] = None
    optimized_beta: Optional[List[float]] = None
    best_bitstring: str
    objective_value: float
    # Canonical lender-facing expected monetary return objective.
    business_objective: Optional[float] = None
    execution_time: float
    # Real approximation ratio (QAOA total return / classical-optimal total
    # return) - 0.0 if the QAOA candidate failed classical validation.
    # No longer a hardcoded 0.94/0.85.
    solution_quality: float
    classical_optimal_objective: Optional[float] = None
    objective_gap: Optional[float] = None
    approximation_ratio: Optional[float] = None
    classical_reference_algorithm: Optional[str] = None
    classical_reference_is_provably_optimal: Optional[bool] = None
    selected_vendors: List[str]
    allocated_capital: float
    expected_portfolio_risk: Optional[float] = None
    expected_portfolio_return: Optional[float] = None
    # Per-vendor allocation detail from THIS optimization run - the single
    # source of truth that downstream consumers (e.g. portfolio.py) should
    # persist, instead of separately hardcoding placeholder numbers.
    allocations: Optional[List[Dict[str, Any]]] = None
    classical_benchmark: Optional[Dict[str, Any]] = None
    solution_metrics: Optional[Dict[str, Any]] = None
    status: str
    validation_status: str
    fallback_used: bool
    created_at: datetime
