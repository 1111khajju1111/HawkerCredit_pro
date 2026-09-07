
import re
from typing import Dict, Any, List, Tuple


# ============================================================================
# TEXT NORMALIZATION
# ============================================================================

def _normalize_text(text: str) -> str:
    """
    Normalize whitespace and common currency formatting.

    Important:
    Do NOT remove Hindi or Telugu Unicode characters.
    """

    if not text:
        return ""

    text = text.replace("₹", " rupees ")
    text = text.replace(",", "")

    # Normalize common punctuation to spaces.
    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================================
# AMOUNT EXTRACTION
# ============================================================================

def _find_amounts(text: str) -> List[Tuple[float, int, int]]:
    """
    Extract every numeric amount and its character position.

    Returns:
        [
            (amount, start_position, end_position),
            ...
        ]
    """

    results: List[Tuple[float, int, int]] = []

    pattern = r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])"

    for match in re.finditer(pattern, text):

        try:
            amount = float(match.group(0))

            if amount > 0:
                results.append(
                    (
                        amount,
                        match.start(),
                        match.end(),
                    )
                )

        except ValueError:
            continue

    return results


# ============================================================================
# KEYWORDS
# ============================================================================

SALES_KEYWORDS = [
    # ------------------------------------------------------------------------
    # English
    # ------------------------------------------------------------------------
    "sales",
    "sale",
    "sold",
    "selling",
    "sell",
    "revenue",
    "income",
    "earned",
    "earn",
    "earning",
    "earnings",
    "made",

    # ------------------------------------------------------------------------
    # Hindi
    # ------------------------------------------------------------------------
    "कमाई",
    "कमाया",
    "कमाए",
    "कमाई हुई",
    "आय",
    "बिक्री",
    "बेचा",
    "बेची",
    "बेचे",
    "बेचकर",
    "बिके",

    # ------------------------------------------------------------------------
    # Telugu
    # ------------------------------------------------------------------------
    "అమ్మకాలు",
    "అమ్మకం",
    "అమ్మాను",
    "అమ్మి",
    "అమ్మిన",
    "సంపాదించాను",
    "సంపాదించాడు",
    "సంపాదించింది",
    "సంపాదన",
    "ఆదాయం",
    "వచ్చింది",
]


EXPENSE_KEYWORDS = [
    # ------------------------------------------------------------------------
    # English
    # ------------------------------------------------------------------------
    "stock",
    "stocks",
    "expense",
    "expenses",
    "spent",
    "spend",
    "spending",
    "cost",
    "costs",
    "purchase",
    "purchased",
    "bought",
    "buy",
    "paid",
    "payment",
    "inventory",
    "wholesale",
    "material",
    "materials",

    # ------------------------------------------------------------------------
    # Hindi
    # ------------------------------------------------------------------------
    "खर्च",
    "खर्चा",
    "खर्चे",
    "खर्च किया",
    "खर्च किए",
    "खरीदा",
    "खरीद",
    "खरीदारी",
    "भुगतान",
    "दिया",
    "लागत",
    "स्टॉक",
    "सामान",
    "माल",
    "थोक",

    # ------------------------------------------------------------------------
    # Telugu
    # ------------------------------------------------------------------------
    "ఖర్చు",
    "ఖర్చు చేశాను",
    "ఖర్చుచేశాను",
    "ఖర్చు చేశాడు",
    "ఖర్చు చేసింది",
    "కొన్నాను",
    "కొన్న",
    "కొనుగోలు",
    "చెల్లించాను",
    "చెల్లింపు",
    "వ్యయం",
    "ధర",
    "స్టాక్",
    "ఇన్వెంటరీ",
    "హోల్‌సేల్",
    "హోల్ సేల్",
    "సామాను",
    "సరుకు",
    "మెటీరియల్",
]


# ============================================================================
# CATEGORY KEYWORDS
# ============================================================================

PRODUCE_KEYWORDS = [
    # English
    "vegetable",
    "vegetables",
    "fruit",
    "fruits",
    "produce",
    "sabzi",

    # Hindi
    "सब्जी",
    "सब्जियां",
    "सब्ज़ी",
    "फल",

    # Telugu
    "కూరగాయ",
    "కూరగాయలు",
    "పండ్లు",
    "పండు",
]


FOOD_KEYWORDS = [
    # English
    "tea",
    "chai",
    "milk",
    "sugar",
    "snack",
    "snacks",
    "food",

    # Hindi
    "चाय",
    "दूध",
    "चीनी",
    "नाश्ता",
    "खाना",

    # Telugu
    "టీ",
    "పాలు",
    "చక్కెర",
    "స్నాక్స్",
    "ఆహారం",
]


# ============================================================================
# KEYWORD MATCHING
# ============================================================================

def _find_keyword_positions(
    text: str,
    keywords: List[str],
) -> List[Tuple[str, int, int]]:
    """
    Find every occurrence of every keyword.

    Returns:
        [
            (keyword, start_position, end_position),
            ...
        ]
    """

    matches: List[Tuple[str, int, int]] = []

    for keyword in keywords:

        start = 0

        while True:

            position = text.find(keyword, start)

            if position == -1:
                break

            matches.append(
                (
                    keyword,
                    position,
                    position + len(keyword),
                )
            )

            start = position + max(len(keyword), 1)

    return matches


# ============================================================================
# DIRECT PAIR MATCHING
# ============================================================================

def _find_direct_amount_for_keywords(
    text: str,
    amounts: List[Tuple[float, int, int]],
    keywords: List[str],
    used_indexes: set,
) -> Tuple[float, int]:
    """
    Strong extraction method.

    Handles:

        sales 5000
        stock 2000

        5000 sales
        2000 stock

        5000 అమ్మకాలు
        2000 ఖర్చు

        5000 कमाई
        2000 खर्च

    The amount must be close to the keyword.

    The same numeric occurrence cannot be reused.
    """

    keyword_matches = _find_keyword_positions(text, keywords)

    best_index = -1
    best_distance = float("inf")

    for keyword, keyword_start, keyword_end in keyword_matches:

        for index, (amount, amount_start, amount_end) in enumerate(amounts):

            if index in used_indexes:
                continue

            # ---------------------------------------------------------------
            # Case 1:
            # keyword -> amount
            #
            # Example:
            # sales 5000
            # stock 2000
            # ---------------------------------------------------------------

            if amount_start >= keyword_end:

                distance = amount_start - keyword_end

                # Do not associate unrelated amounts far away.
                if distance <= 30 and distance < best_distance:

                    # Reject if another keyword is between them.
                    text_between = text[keyword_end:amount_start]

                    if not _contains_opposite_financial_keyword(
                        text_between,
                        keywords,
                    ):
                        best_distance = distance
                        best_index = index

            # ---------------------------------------------------------------
            # Case 2:
            # amount -> keyword
            #
            # Example:
            # 5000 sales
            # 2000 stock
            # ---------------------------------------------------------------

            elif amount_end <= keyword_start:

                distance = keyword_start - amount_end

                if distance <= 30 and distance < best_distance:

                    text_between = text[amount_end:keyword_start]

                    if not _contains_opposite_financial_keyword(
                        text_between,
                        keywords,
                    ):
                        best_distance = distance
                        best_index = index

    if best_index == -1:
        return 0.0, -1

    return amounts[best_index][0], best_index


def _contains_opposite_financial_keyword(
    text: str,
    current_keywords: List[str],
) -> bool:
    """
    Prevent an amount from jumping across another financial keyword.

    Example:

        sales 5000 stock 2000

    The 5000 should not accidentally be associated with stock.
    """

    all_keywords = SALES_KEYWORDS + EXPENSE_KEYWORDS

    current_set = set(current_keywords)

    for keyword in all_keywords:

        if keyword in current_set:
            continue

        if keyword in text:
            return True

    return False


# ============================================================================
# PROXIMITY FALLBACK
# ============================================================================

def _find_closest_amount(
    text: str,
    amounts: List[Tuple[float, int, int]],
    keywords: List[str],
    used_indexes: set,
) -> Tuple[float, int]:
    """
    Fallback extraction based on nearest keyword.

    Used only when direct keyword/amount matching did not find a value.
    """

    keyword_positions = _find_keyword_positions(
        text,
        keywords,
    )

    if not keyword_positions:
        return 0.0, -1

    best_index = -1
    best_distance = float("inf")

    for index, (_, amount_start, amount_end) in enumerate(amounts):

        if index in used_indexes:
            continue

        for _, keyword_start, keyword_end in keyword_positions:

            distance = min(
                abs(amount_start - keyword_end),
                abs(amount_end - keyword_start),
            )

            if distance < best_distance:
                best_distance = distance
                best_index = index

    if best_index == -1:
        return 0.0, -1

    # Do not accept extremely distant matches.
    if best_distance > 80:
        return 0.0, -1

    return amounts[best_index][0], best_index


# ============================================================================
# MAIN PARSER
# ============================================================================

def parse_voice_transaction(transcript: str) -> Dict[str, Any]:
    """
    Multilingual financial NLP parser.

    Supports:
        English
        Hindi
        Telugu

    Examples:

        sales 5000, stock 2000

        5000 అమ్మకాలు, 2000 ఖర్చు

        5000 कमाई, 2000 खर्च

        Today I sold vegetables for 4500 rupees
        and spent 1800 rupees on stock.

        ఈ రోజు కూరగాయలు అమ్మి 4500 రూపాయలు సంపాదించాను
        మరియు స్టాక్ కోసం 1800 ఖర్చు చేశాను.

        आज मैंने सब्जियां बेचकर 4500 रुपये कमाए
        और स्टॉक पर 1800 रुपये खर्च किए।
    """

    # ------------------------------------------------------------------------
    # Empty input
    # ------------------------------------------------------------------------

    if not transcript:

        return {
            "sales": 0.0,
            "expenses": 0.0,
            "category": "GENERAL",
            "confidence": 0.0,
            "raw_transcript": transcript,
        }

    # ------------------------------------------------------------------------
    # Normalize
    # ------------------------------------------------------------------------

    text = _normalize_text(transcript)

    if not text:

        return {
            "sales": 0.0,
            "expenses": 0.0,
            "category": "GENERAL",
            "confidence": 0.0,
            "raw_transcript": transcript,
        }

    text_lower = text.lower()

    # ------------------------------------------------------------------------
    # Extract all numeric amounts ONCE
    # ------------------------------------------------------------------------

    amounts = _find_amounts(text_lower)

    used_indexes = set()

    sales = 0.0
    expenses = 0.0

    # ------------------------------------------------------------------------
    # STEP 1
    #
    # Strong/direct revenue matching
    # ------------------------------------------------------------------------

    sales, sales_index = _find_direct_amount_for_keywords(
        text_lower,
        amounts,
        SALES_KEYWORDS,
        used_indexes,
    )

    if sales_index >= 0:
        used_indexes.add(sales_index)

    # ------------------------------------------------------------------------
    # STEP 2
    #
    # Strong/direct expense matching
    # ------------------------------------------------------------------------

    expenses, expense_index = _find_direct_amount_for_keywords(
        text_lower,
        amounts,
        EXPENSE_KEYWORDS,
        used_indexes,
    )

    if expense_index >= 0:
        used_indexes.add(expense_index)

    # ------------------------------------------------------------------------
    # STEP 3
    #
    # Proximity fallback for revenue
    # ------------------------------------------------------------------------

    if sales == 0.0:

        sales, sales_index = _find_closest_amount(
            text_lower,
            amounts,
            SALES_KEYWORDS,
            used_indexes,
        )

        if sales_index >= 0:
            used_indexes.add(sales_index)

    # ------------------------------------------------------------------------
    # STEP 4
    #
    # Proximity fallback for expenses
    # ------------------------------------------------------------------------

    if expenses == 0.0:

        expenses, expense_index = _find_closest_amount(
            text_lower,
            amounts,
            EXPENSE_KEYWORDS,
            used_indexes,
        )

        if expense_index >= 0:
            used_indexes.add(expense_index)

    # ------------------------------------------------------------------------
    # STEP 5
    #
    # Last-resort numeric fallback
    #
    # Only use numbers that have not already been assigned.
    #
    # This prevents:
    #
    #     sales = 5000
    #     expenses = 5000
    #
    # ------------------------------------------------------------------------

    remaining_indexes = [
        index
        for index in range(len(amounts))
        if index not in used_indexes
    ]

    if sales == 0.0 and remaining_indexes:

        index = remaining_indexes.pop(0)

        sales = amounts[index][0]

        used_indexes.add(index)

    if expenses == 0.0 and remaining_indexes:

        index = remaining_indexes.pop(0)

        expenses = amounts[index][0]

        used_indexes.add(index)

    # ------------------------------------------------------------------------
    # CATEGORY DETECTION
    # ------------------------------------------------------------------------

    category = "GENERAL"

    if any(
        keyword.lower() in text_lower
        for keyword in PRODUCE_KEYWORDS
    ):
        category = "PRODUCE"

    elif any(
        keyword.lower() in text_lower
        for keyword in FOOD_KEYWORDS
    ):
        category = "BEVERAGES_FOOD"

    elif any(
        keyword.lower() in text_lower
        for keyword in EXPENSE_KEYWORDS
    ):
        category = "STOCK"

    # ------------------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------------------

    if sales > 0 and expenses > 0:

        confidence = 0.96

    elif sales > 0 or expenses > 0:

        confidence = 0.85

    else:

        confidence = 0.40

    # ------------------------------------------------------------------------
    # RESULT
    # ------------------------------------------------------------------------

    return {
        "sales": sales,
        "expenses": expenses,
        "category": category,
        "confidence": confidence,
        "raw_transcript": transcript,
    }
