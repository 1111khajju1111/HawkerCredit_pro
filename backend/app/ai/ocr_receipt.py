import io
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from PIL import Image, ImageOps, ImageEnhance, ImageFilter


# ============================================================================
# REGEX PATTERNS
# ============================================================================

# General currency amount.
#
# Supports:
#   ₹588
#   Rs 588
#   Rs. 588
#   INR 588
#   ₹ 588.00
#
_CURRENCY_AMOUNT_PATTERN = re.compile(
    r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


# Receipt total labels.
#
# These are deliberately prioritized over ordinary amounts because a receipt
# contains many prices, quantities and tax values.
_TOTAL_PATTERNS = [
    re.compile(
        r"(?:total\s+amount|grand\s+total|net\s+amount|"
        r"amount\s+payable|amount\s+due|bill\s+total)"
        r"\s*[:=\-]?\s*"
        r"(?:rs\.?|inr|₹)?\s*"
        r"([\d,]+(?:\.\d{1,2})?)",
        re.IGNORECASE,
    ),

    re.compile(
        r"(?:total)"
        r"\s*[:=\-]?\s*"
        r"(?:rs\.?|inr|₹)?\s*"
        r"([\d,]+(?:\.\d{1,2})?)",
        re.IGNORECASE,
    ),
]


# ============================================================================
# CATEGORY KEYWORDS
# ============================================================================

_CATEGORY_KEYWORDS = {
    "INVENTORY_PURCHASE": [
        "vegetable",
        "vegetables",
        "mandi",
        "apmc",
        "produce",
        "onion",
        "potato",
        "tomato",
        "capsicum",
        "fruit",
        "fruits",
        "सब्जी",
        "सब्जियां",
        "फल",
        "कांदा",
        "आलू",
        "टमाटर",
        "కూరగాయ",
        "కూరగాయలు",
        "పండ్లు",
        "ఉల్లిపాయ",
        "బంగాళాదుంప",
        "టమాటా",
    ],

    "RAW_MATERIALS": [
        "milk",
        "dairy",
        "curd",
        "paneer",
        "పాలు",
        "పెరుగు",
        "పనీర్",
        "दूध",
        "दही",
    ],

    "STOCK": [
        "wholesale",
        "stock",
        "inventory",
        "packaging",
        "gas",
        "cylinder",
        "supply",
        "material",
        "materials",
        "स्टॉक",
        "सामान",
        "माल",
        "थोक",
        "స్టాక్",
        "సామాను",
        "సరుకు",
        "హోల్‌సేల్",
    ],
}


# ============================================================================
# IMAGE PREPROCESSING
# ============================================================================

def _preprocess_image(image: Image.Image) -> Image.Image:
    """
    Improve receipt image readability before sending it to Tesseract.

    This is intentionally conservative so we don't destroy characters on
    photographs.
    """

    image = image.convert("L")

    # Improve contrast.
    image = ImageOps.autocontrast(image)

    # Slight sharpening helps thermal receipt text.
    image = image.filter(ImageFilter.SHARPEN)

    # Increase contrast further without aggressive thresholding.
    image = ImageEnhance.Contrast(image).enhance(1.5)

    return image


# ============================================================================
# TESSERACT LANGUAGE
# ============================================================================

def _get_ocr_language(pytesseract) -> str:
    """
    Select the best available OCR language combination.

    English is always preferred when available.
    Hindi and Telugu are added when installed.
    """

    try:
        installed = set(
            pytesseract.get_languages(config="")
        )
    except Exception:
        installed = set()

    languages = []

    if "eng" in installed:
        languages.append("eng")

    if "hin" in installed:
        languages.append("hin")

    if "tel" in installed:
        languages.append("tel")

    if languages:
        return "+".join(languages)

    return "eng"


# ============================================================================
# TOTAL EXTRACTION
# ============================================================================

def _extract_total(raw_text: str) -> Optional[float]:
    """
    Extract the receipt's final total.

    Priority:

    1. Total Amount
    2. Grand Total
    3. Net Amount
    4. Amount Payable
    5. Amount Due
    6. Bill Total
    7. Generic Total
    8. Currency amount fallback
    """

    if not raw_text:
        return None

    # Normalize OCR whitespace.
    normalized = raw_text.replace(",", "")
    normalized = re.sub(r"\s+", " ", normalized)

    # ---------------------------------------------------------
    # First: explicit total labels
    # ---------------------------------------------------------

    for pattern in _TOTAL_PATTERNS:

        match = pattern.search(normalized)

        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue

    # ---------------------------------------------------------
    # Second: line-by-line total detection
    #
    # Helps when OCR inserts unusual spaces/newlines.
    # ---------------------------------------------------------

    for line in raw_text.splitlines():

        line_clean = re.sub(r"\s+", " ", line).strip()

        if not line_clean:
            continue

        line_lower = line_clean.lower()

        total_words = [
            "total amount",
            "grand total",
            "net amount",
            "amount payable",
            "amount due",
            "bill total",
        ]

        if any(word in line_lower for word in total_words):

            numbers = re.findall(
                r"\d+(?:,\d{3})*(?:\.\d{1,2})?",
                line_clean,
            )

            if numbers:

                try:
                    return float(
                        numbers[-1].replace(",", "")
                    )
                except ValueError:
                    pass

    # ---------------------------------------------------------
    # Third: generic currency fallback
    # ---------------------------------------------------------

    currency_matches = _CURRENCY_AMOUNT_PATTERN.findall(raw_text)

    if currency_matches:

        values = []

        for value in currency_matches:

            try:
                values.append(
                    float(value.replace(",", ""))
                )
            except ValueError:
                continue

        if values:
            # Last currency amount is often the total on conventional receipts.
            return values[-1]

    return None


# ============================================================================
# MERCHANT EXTRACTION
# ============================================================================

def _extract_merchant(raw_text: str) -> str:
    """
    Guess the merchant from the first meaningful OCR line.

    Rejects obvious receipt metadata lines.
    """

    if not raw_text:
        return "Unrecognized Merchant"

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    ignored_prefixes = (
        "bill",
        "date",
        "time",
        "cashier",
        "phone",
        "ph",
        "gst",
        "invoice",
        "receipt",
        "no.",
        "item",
        "qty",
        "amount",
        "total",
    )

    for line in lines[:10]:

        clean = line.strip()

        if not clean:
            continue

        lower = clean.lower()

        if lower.startswith(ignored_prefixes):
            continue

        # Avoid returning a line consisting almost entirely of numbers.
        if re.fullmatch(r"[\d\s\-/:.]+", clean):
            continue

        return clean[:100]

    return "Unrecognized Merchant"


# ============================================================================
# CATEGORY EXTRACTION
# ============================================================================

def _extract_category(raw_text: str) -> str:
    """
    Detect receipt category from multilingual product/vendor keywords.
    """

    text_lower = raw_text.lower()

    for category, keywords in _CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            if keyword.lower() in text_lower:
                return category

    return "STOCK"


# ============================================================================
# REAL OCR
# ============================================================================

def _try_real_ocr(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Perform genuine OCR using Tesseract.

    Returns None if:
      - Pillow is unavailable
      - pytesseract is unavailable
      - Tesseract executable is unavailable
      - OCR returns no text
      - no usable receipt total can be extracted
    """

    try:

        import pytesseract

        # -----------------------------------------------------
        # Verify the Tesseract executable exists.
        # -----------------------------------------------------

        try:
            tesseract_version = pytesseract.get_tesseract_version()

            if not tesseract_version:
                return None

        except Exception:
            return None

        # -----------------------------------------------------
        # Open uploaded image.
        # -----------------------------------------------------

        image = Image.open(
            io.BytesIO(image_bytes)
        )

        # Fix EXIF orientation.
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        # -----------------------------------------------------
        # Preprocess.
        # -----------------------------------------------------

        processed_image = _preprocess_image(image)

        # -----------------------------------------------------
        # Determine available OCR languages.
        # -----------------------------------------------------

        language = _get_ocr_language(
            pytesseract
        )

        # -----------------------------------------------------
        # OCR.
        # -----------------------------------------------------

        raw_text = pytesseract.image_to_string(
            processed_image,
            lang=language,
            config="--psm 6",
        )

        if not raw_text or not raw_text.strip():
            return None

        raw_text = raw_text.strip()

        # -----------------------------------------------------
        # Extract receipt total.
        # -----------------------------------------------------

        amount = _extract_total(raw_text)

        if amount is None:
            return None

        # -----------------------------------------------------
        # Merchant.
        # -----------------------------------------------------

        merchant = _extract_merchant(raw_text)

        # -----------------------------------------------------
        # Category.
        # -----------------------------------------------------

        category = _extract_category(raw_text)

        # -----------------------------------------------------
        # Confidence.
        #
        # This is still a conservative application-level score.
        # It is NOT the same thing as Tesseract's internal confidence.
        # -----------------------------------------------------

        confidence = 0.75

        if amount > 0:
            confidence += 0.05

        if merchant != "Unrecognized Merchant":
            confidence += 0.05

        if len(raw_text) >= 50:
            confidence += 0.05

        confidence = min(confidence, 0.90)

        # -----------------------------------------------------
        # Result.
        # -----------------------------------------------------

        return {
            "merchant": merchant,
            "amount": amount,
            "category": category,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "confidence": confidence,
            "items": [],
            "extraction_method": "TESSERACT_OCR",
            "raw_text_preview": raw_text[:500],
            "ocr_language": language,
        }

    except Exception:
        # Never allow OCR failure to crash the receipt endpoint.
        return None


# ============================================================================
# DEMO FALLBACK
# ============================================================================

def _deterministic_demo_parse(
    filename: str,
) -> Dict[str, Any]:
    """
    Deterministic demo fallback.

    This is intentionally retained so the application continues to function
    when OCR is unavailable.

    The frontend should display the extraction_method so users can distinguish
    real OCR from demo data.
    """

    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    fname = filename.lower()

    if "vegetable" in fname or "mandi" in fname:

        merchant = "APMC Mandi Wholesale"
        amount = 4850.0
        category = "INVENTORY_PURCHASE"

        items = [
            "Onions 50kg",
            "Potatoes 40kg",
            "Tomatoes 20kg",
        ]

        confidence = 0.96

    elif "milk" in fname or "dairy" in fname:

        merchant = "Amul Dairy Distributor"
        amount = 1800.0
        category = "RAW_MATERIALS"

        items = [
            "Full Cream Milk 30L",
            "Curd 10kg",
        ]

        confidence = 0.92

    else:

        merchant = "City Wholesale Market"
        amount = 2450.0
        category = "STOCK"

        items = [
            "Packaging Material",
            "Gas Cylinder Refill",
        ]

        confidence = 0.89

    return {
        "merchant": merchant,
        "amount": amount,
        "category": category,
        "date": today_str,
        "confidence": confidence,
        "items": items,
        "extraction_method": "DETERMINISTIC_DEMO_FALLBACK",
        "raw_text_preview": None,
    }


# ============================================================================
# PUBLIC ENTRY POINT
# ============================================================================

def parse_receipt_image(
    image_bytes: bytes = None,
    filename: str = "",
) -> Dict[str, Any]:
    """
    Receipt ingestion entry point.

    Flow:

        uploaded image
            ↓
        Tesseract OCR
            ↓
        extract merchant
            ↓
        extract total
            ↓
        detect category
            ↓
        return PENDING candidate

    If genuine OCR cannot produce a usable amount, the deterministic demo
    fallback is returned.

    Nothing is written to the financial ledger here.
    """

    if image_bytes:

        real_result = _try_real_ocr(
            image_bytes
        )

        if real_result is not None:
            return real_result

    return _deterministic_demo_parse(
        filename or "receipt.jpg"
    )
