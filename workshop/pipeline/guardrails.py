"""Pillar 2: Guardrails (the Conscience).

Mental model mapping:
  Conscience = this entire module. Deterministic validation of structured output.
  Runs ALWAYS, regardless of whether regex or the Brain (LLM) produced the extraction.

Exercise 2 teaches: never trust an LLM without a deterministic layer to
verify it. Normalize values, audit exhibits, check logical consistency,
and assign a verdict (PASS or REVIEW). Never auto-approve.
"""
import re
from datetime import datetime

from workshop.pipeline.models import (
    AffidavitExtraction,
    ClaimStatus,
    Finding,
    SourceRecord,
    Verdict,
    VerdictType,
)

AMOUNT_FIELDS = {"chargeoff_balance", "last_payment_amount", "sale_balance"}
DATE_FIELDS = {"chargeoff_date", "last_payment_date", "closing_date", "transfer_date"}
NAME_FIELDS = {"consumer_name"}


def normalize_amount(raw: float | int | str | None) -> float | None:
    """Normalize a dollar amount to a plain float for comparison.

    Examples:
        "$6,218.55"  -> 6218.55   (LLM extraction format)
        "6218.55"    -> 6218.55
        6218.55      -> 6218.55   (SourceRecord float)
        "$1,234"     -> 1234.0
        None         -> None
        ""           -> None

    Coerce to str first (handles float/int from SourceRecord), strip $
    and commas, convert to float, round to 2 decimals.

    Workshop blank A (core).
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    is_negative = False
    if text.startswith("(") and text.endswith(")"):
        is_negative = True
        text = text[1:-1]
    if text.startswith("-"):
        is_negative = True
        text = text[1:]
    text = re.sub(r"[$ ,]", "", text)
    try:
        val = round(float(text), 2)
        return -val if is_negative else val
    except ValueError:
        return None


def normalize_date(raw: str | None) -> str | None:
    """Convert date string to ISO (YYYY-MM-DD).

    Core cases (must implement):
        "03/15/2024"  -> "2024-03-15"   (MM/DD/YYYY)
        "3/15/2024"   -> "2024-03-15"   (M/D/YYYY, no leading zeros)
        "2024-03-15"  -> "2024-03-15"   (ISO passthrough)
        None          -> None
        ""            -> None

    Hint: strptime with "%m/%d/%Y" handles both MM/DD and M/D.

    Stretch case: "March 15, 2024" (verbose month name).

    Workshop blank B (core). The verbose format block below is STRETCH
    (blank it in Fase 3 along with the core cases).
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", text):
        dt = datetime.strptime(text, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    # --- STRETCH (blank B stretch): verbose month name like "March 15, 2024" or "15 March 2024" ---
    try:
        dt = datetime.strptime(text, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(text, "%d %B %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    return text


def normalize_name(raw: str | None) -> str | None:
    """Normalize a person's name so word order and punctuation do not matter.

    A live LLM often returns names as "LAST; FIRST MIDDLE" while the source of
    truth stores "First Middle Last". Both name the same person, so a strict
    string compare would wrongly flag a mismatch. Normalize by dropping
    punctuation, lowercasing, and sorting the tokens.

    Examples:
        "GARCIA; MARIA L."  -> "garcia l maria"
        "Maria L. Garcia"   -> "garcia l maria"   (matches the above)
        "John R. Smith"     -> "john r smith"
        None / ""           -> None

    Workshop blank F (stretch). compare_field() falls back to this only when a
    plain match fails, so leaving it blank does not break the core exercise.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    tokens = re.sub(r"[.,;]", " ", text).lower().split()
    if not tokens:
        return None
    return " ".join(sorted(tokens))


def audit_bill_of_sale(pdf_text: str, extraction: AffidavitExtraction) -> Finding:
    """Check if the LLM's bill_of_sale_attached claim matches the actual PDF text.

    Search the PDF text for a heading like:
        r"BILL\\s+OF\\s+SALE|CHARGED-OFF\\s+ACCOUNT(?:S)?\\s+ASSIGNMENT"

    Return a Finding with the appropriate ClaimStatus:
        - claimed is None  -> MISSING ("LLM did not extract this field")
        - claimed is False -> EXEMPT ("not claimed, nothing to verify")
        - claimed is True AND heading found -> MATCH
        - claimed is True AND heading NOT found -> MISMATCH ("CRITICAL EXHIBIT MISSING")

    Workshop blank C (core).
    """
    claimed = extraction.bill_of_sale_attached

    if claimed is None:
        return Finding(
            field="bill_of_sale_attached",
            expected_value="N/A",
            document_value="None",
            normalized_expected="N/A",
            normalized_document="None",
            claim_status=ClaimStatus.MISSING,
            reason="bill_of_sale_attached: LLM did not extract this field",
        )

    if not claimed:
        return Finding(
            field="bill_of_sale_attached",
            expected_value="N/A",
            document_value=str(claimed),
            normalized_expected="N/A",
            normalized_document=str(claimed),
            claim_status=ClaimStatus.EXEMPT,
            reason="bill_of_sale_attached: not claimed, exempt from audit",
        )

    heading_found = bool(
        re.search(
            r"(?:^|\n)\s*(?:BILL\s+OF\s+SALE|CHARGED-OFF\s+ACCOUNT(?:S)?\s+ASSIGNMENT)\s*(?:\n|$)",
            pdf_text,
            re.IGNORECASE,
        )
    )

    if heading_found:
        return Finding(
            field="bill_of_sale_attached",
            expected_value="True",
            document_value=str(claimed),
            normalized_expected="True",
            normalized_document="True",
            claim_status=ClaimStatus.MATCH,
            reason="bill_of_sale_attached: claimed and heading found in PDF",
        )

    return Finding(
        field="bill_of_sale_attached",
        expected_value="True",
        document_value=str(claimed),
        normalized_expected="True",
        normalized_document="heading not found",
        claim_status=ClaimStatus.MISMATCH,
        reason="bill_of_sale_attached: CRITICAL EXHIBIT MISSING",
    )


def compare_field(
    field_name: str,
    expected: str | float | int | None,
    extracted: str | None,
    is_amount: bool = False,
    is_date: bool = False,
    is_name: bool = False,
) -> Finding:
    """Compare a single field after normalizing both sides. Provided to attendees."""
    if extracted is None or str(extracted).strip() == "":
        return Finding(
            field=field_name,
            expected_value=str(expected) if expected is not None else None,
            document_value=None,
            normalized_expected=str(expected) if expected is not None else None,
            normalized_document=None,
            claim_status=ClaimStatus.MISSING,
            reason=f"{field_name}: not found in extraction",
        )

    if is_amount:
        norm_exp = normalize_amount(expected)
        norm_doc = normalize_amount(extracted)
        match = norm_exp is not None and norm_doc is not None and norm_exp == norm_doc
    elif is_date:
        norm_exp = normalize_date(str(expected) if expected is not None else None)
        norm_doc = normalize_date(extracted)
        match = norm_exp is not None and norm_doc is not None and norm_exp == norm_doc
    else:
        norm_exp = str(expected).strip() if expected is not None else None
        norm_doc = str(extracted).strip()
        match = norm_exp is not None and norm_exp.lower() == norm_doc.lower()
        if not match and is_name:
            # Fall back to order-insensitive name matching ("GARCIA; MARIA L."
            # vs "Maria L. Garcia"). normalize_name is a stretch blank: if it is
            # not implemented (returns None) this fallback is simply skipped, so
            # the core exercise still works.
            nx = normalize_name(expected)
            nd = normalize_name(extracted)
            match = nx is not None and nd is not None and nx == nd

    return Finding(
        field=field_name,
        expected_value=str(expected) if expected is not None else None,
        document_value=extracted,
        normalized_expected=str(norm_exp),
        normalized_document=str(norm_doc),
        claim_status=ClaimStatus.MATCH if match else ClaimStatus.MISMATCH,
        reason=f"{field_name}: {'values match' if match else 'VALUE MISMATCH'}",
    )


def check_statement_contradiction(
    extraction: AffidavitExtraction,
    source: SourceRecord,
) -> Finding | None:
    """If the extracted last_payment_date is after the source chargeoff_date, that is a contradiction.

    Compare normalize_date(extraction.last_payment_date) against
    normalize_date(source.chargeoff_date). If payment is later, return a
    Finding with MISMATCH. Otherwise return None (no issue).

    Workshop blank D (stretch).
    """
    co_balance = normalize_amount(extraction.chargeoff_balance)
    if co_balance is not None and co_balance < 0:
        return Finding(
            field="statement_contradiction",
            expected_value="chargeoff_balance >= 0",
            document_value=str(co_balance),
            normalized_expected="positive balance",
            normalized_document="negative balance",
            claim_status=ClaimStatus.MISMATCH,
            reason="Statement contradiction: chargeoff balance cannot be negative",
        )

    last_payment = normalize_date(extraction.last_payment_date)
    chargeoff = normalize_date(source.chargeoff_date)

    if last_payment is None or chargeoff is None:
        return None

    if last_payment > chargeoff:
        return Finding(
            field="statement_contradiction",
            expected_value=f"last_payment_date ({last_payment}) <= chargeoff_date ({chargeoff})",
            document_value=f"last_payment_date={last_payment}, chargeoff_date={chargeoff}",
            normalized_expected="payment before chargeoff",
            normalized_document="payment after chargeoff",
            claim_status=ClaimStatus.MISMATCH,
            reason="Statement contradiction: last payment date is after chargeoff date",
        )
    return None


def check_all_fields(
    extraction: AffidavitExtraction,
    source: SourceRecord,
    pdf_text: str,
) -> list[Finding]:
    """Run all comparisons + audit. Provided to attendees (wires everything together)."""
    field_pairs = [
        ("consumer_name", source.consumer_name, extraction.consumer_name),
        ("last4", source.last4, extraction.last4),
        ("original_creditor", source.original_creditor, extraction.original_creditor),
        ("debt_buyer", source.debt_buyer, extraction.debt_buyer),
        ("chargeoff_balance", source.chargeoff_balance, extraction.chargeoff_balance),
        ("chargeoff_date", source.chargeoff_date, extraction.chargeoff_date),
        ("last_payment_date", source.last_payment_date, extraction.last_payment_date),
        ("last_payment_amount", source.last_payment_amount, extraction.last_payment_amount),
        ("closing_date", source.closing_date, extraction.closing_date),
        ("sale_balance", source.sale_balance, extraction.sale_balance),
        ("transfer_date", source.transfer_date, extraction.transfer_date),
    ]

    findings = []
    for field_name, expected, extracted in field_pairs:
        findings.append(
            compare_field(
                field_name,
                expected,
                extracted,
                is_amount=field_name in AMOUNT_FIELDS,
                is_date=field_name in DATE_FIELDS,
                is_name=field_name in NAME_FIELDS,
            )
        )

    findings.append(audit_bill_of_sale(pdf_text, extraction))

    contradiction = check_statement_contradiction(extraction, source)
    if contradiction is not None:
        findings.append(contradiction)

    return findings


def assign_verdict(findings: list[Finding]) -> Verdict:
    """ANY non-MATCH/non-EXEMPT finding -> REVIEW. Never auto-approves.

    Workshop blank E (core).
    """
    review_reasons = [
        f.reason
        for f in findings
        if f.claim_status not in (ClaimStatus.MATCH, ClaimStatus.EXEMPT)
    ]
    verdict_type = VerdictType.REVIEW if review_reasons else VerdictType.PASS
    return Verdict(
        verdict=verdict_type,
        findings=findings,
        review_reasons=review_reasons,
    )
