from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.models.schema import User, Vendor, AuditLog, ConsentRecord
from app.schemas.dto import UserRegister, UserLogin, TokenResponse, StaffRegister
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.core.config import settings
from app.core.rate_limit import limiter

router = APIRouter()


def _issue_token_response(user: User, vendor_id: Optional[str]) -> TokenResponse:
    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role,
        vendor_id=vendor_id
    )


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register(request: Request, user_in: UserRegister, db: Session = Depends(get_db)):
    """
    PUBLIC self-registration. VENDOR ONLY.

    LENDER and ADMIN are staff/institutional roles with elevated
    permissions (viewing every vendor's data, running capital allocation,
    reading audit logs and system metrics) - letting anyone self-assign
    one of those roles through public registration would make the entire
    role system decorative. Any other role is rejected outright rather
    than silently downgraded, so a caller's mistake is visible immediately
    instead of quietly becoming a VENDOR account.
    """
    requested_role = (user_in.role or "VENDOR").upper()
    if requested_role != "VENDOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public registration is only available for the VENDOR role. "
                   "LENDER and ADMIN accounts are created internally by an administrator."
        )

    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        phone=user_in.phone,
        password_hash=get_password_hash(user_in.password),
        role="VENDOR"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    vendor = Vendor(
        user_id=user.id,
        name=user_in.email.split("@")[0].capitalize(),
        phone=user_in.phone or "9876543210",
        business_type="Vegetable Vendor",
        location="Connaught Place, New Delhi"
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    # Default consent: granted for all categories at signup (an opt-out
    # model, matching this app's existing UX in the consent settings
    # page). This matters more now than before: consent enforcement fails
    # CLOSED when no record exists at all (see feature_engineering.py), so
    # every vendor needs a real record from day one rather than relying on
    # one being lazily created the first time they happen to open the
    # consent settings page.
    for data_type, purpose in [
        ("TRANSACTIONS", "Financial feature calculation & credit intelligence scoring"),
        ("EXPENSES", "Expense-to-revenue ratio and liquidity assessment"),
        ("INVENTORY", "Stock valuation and business continuity analysis"),
        ("PORTFOLIO_MATCHING", "Anonymized inclusion in lender quantum portfolio allocation"),
    ]:
        db.add(ConsentRecord(vendor_id=vendor.vendor_id, data_type=data_type, purpose=purpose, granted=True))
    db.commit()

    db.add(AuditLog(user_id=user.id, action="USER_REGISTERED", resource_type="USER", resource_id=user.id))
    db.commit()

    return _issue_token_response(user, vendor.vendor_id)


@router.post("/staff/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register_staff(
    request: Request,
    staff_in: StaffRegister,
    db: Session = Depends(get_db),
    x_bootstrap_secret: Optional[str] = Header(default=None, alias="X-Bootstrap-Secret"),
    authorization: Optional[str] = Header(default=None),
):
    """
    INTERNAL-ONLY endpoint for creating LENDER/ADMIN accounts. Not linked
    from any public UI. Reachable only two ways:

      1. An already-authenticated ADMIN calls it with a normal bearer
         token (Authorization header) to create further staff accounts.
      2. Before any ADMIN exists at all (first-run bootstrap), the caller
         supplies the `X-Bootstrap-Secret` header matching the
         STAFF_BOOTSTRAP_SECRET environment variable set by whoever
         deploys the service. If that env var isn't set, this bootstrap
         path is disabled entirely - there is no default secret.
    """
    role = (staff_in.role or "").upper()
    if role not in ("LENDER", "ADMIN"):
        raise HTTPException(status_code=400, detail="role must be LENDER or ADMIN for this endpoint")

    authorized = False

    # Path 1: bootstrap secret (only meaningful pre-first-admin, but we
    # don't hard-block it afterwards either - an operator may legitimately
    # need to re-bootstrap in a break-glass scenario; the secret itself is
    # the access control).
    if settings.STAFF_BOOTSTRAP_SECRET and x_bootstrap_secret == settings.STAFF_BOOTSTRAP_SECRET:
        authorized = True

    # Path 2: an existing ADMIN's bearer token, decoded manually since a
    # single FastAPI dependency can't cleanly express "this OR that".
    if not authorized and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_token(token)
        caller_id = payload.get("sub")
        if caller_id:
            caller = db.query(User).filter(User.id == caller_id).first()
            if caller and caller.role == "ADMIN":
                authorized = True

    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create staff accounts. Provide a valid "
                   "X-Bootstrap-Secret header or an ADMIN bearer token."
        )

    existing = db.query(User).filter(User.email == staff_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=staff_in.email,
        phone=staff_in.phone,
        password_hash=get_password_hash(staff_in.password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(AuditLog(user_id=user.id, action=f"STAFF_ACCOUNT_CREATED_{role}", resource_type="USER", resource_id=user.id))
    db.commit()

    return _issue_token_response(user, None)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("15/minute")
def login(request: Request, user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    vendor_id = None
    if user.vendor:
        vendor_id = user.vendor.vendor_id

    # Audit log
    db.add(AuditLog(user_id=user.id, action="USER_LOGIN", resource_type="USER", resource_id=user.id))
    db.commit()

    return _issue_token_response(user, vendor_id)
