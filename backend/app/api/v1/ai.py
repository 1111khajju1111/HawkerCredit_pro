from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.schema import Vendor
from app.schemas.dto import VoiceTransactionInput, VoiceTransactionOutput, ReceiptOCROutput
from app.ai.nlp_voice import parse_voice_transaction
from app.ai.ocr_receipt import parse_receipt_image
from app.ai.anomaly_detector import detect_anomalies
from app.ai.cashflow_forecaster import forecast_cashflow
from app.ai.ai_coach import get_ai_coach_advice
from app.ai.data_quality import calculate_data_quality
from app.core.security import verify_vendor_access, get_current_user

router = APIRouter()

@router.post("/voice-transaction", response_model=VoiceTransactionOutput)
def voice_transaction(input_data: VoiceTransactionInput, current_user=Depends(get_current_user)):
    parsed = parse_voice_transaction(input_data.transcript)
    return VoiceTransactionOutput(**parsed)

@router.post("/receipt-ocr", response_model=ReceiptOCROutput)
async def receipt_ocr(file: UploadFile = File(None), current_user=Depends(get_current_user)):
    filename = file.filename if file else "vegetable_receipt.jpg"
    image_bytes = await file.read() if file else None
    parsed = parse_receipt_image(image_bytes=image_bytes, filename=filename)
    return ReceiptOCROutput(**parsed)

@router.get("/anomaly-detection/{vendor_id}")
def get_anomaly_analysis(vendor_id: str, db: Session = Depends(get_db), _: bool = Depends(verify_vendor_access)):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    txs = [t.__dict__ for t in vendor.transactions]
    exs = [e.__dict__ for e in vendor.expenses]
    return detect_anomalies(txs, exs)

@router.get("/forecast/{vendor_id}")
def get_forecast(vendor_id: str, period_days: int = 30, db: Session = Depends(get_db), _: bool = Depends(verify_vendor_access)):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    txs = [t.__dict__ for t in vendor.transactions]
    exs = [e.__dict__ for e in vendor.expenses]
    return forecast_cashflow(txs, exs, period_days=period_days)

@router.get("/coach/{vendor_id}")
def get_coach(vendor_id: str, query: str = None, db: Session = Depends(get_db), _: bool = Depends(verify_vendor_access)):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    score_val = vendor.credit_score.score if vendor.credit_score else 650
    features = vendor.credit_feature.__dict__ if vendor.credit_feature else {}
    return get_ai_coach_advice(score_val, features, user_query=query)

@router.get("/data-quality/{vendor_id}")
def get_data_quality(vendor_id: str, db: Session = Depends(get_db), _: bool = Depends(verify_vendor_access)):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    txs = [t.__dict__ for t in vendor.transactions]
    exs = [e.__dict__ for e in vendor.expenses]
    v_data = vendor.__dict__
    return calculate_data_quality(txs, exs, v_data)
