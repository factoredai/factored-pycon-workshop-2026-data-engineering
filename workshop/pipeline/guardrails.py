"""Pillar 2: Guardrails (the Conscience).

Mental model mapping:
  Conscience = this entire module. Deterministic validation of structured output.
  Runs ALWAYS, regardless of whether regex or the Brain (LLM) produced the extraction.
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
    """Normalize a dollar amount to a float for comparison."""
    pass


def normalize_date(raw: str | None) -> str | None:
    """Normalize a date string to ISO format (YYYY-MM-DD)."""
    pass


def normalize_name(raw: str | None) -> str | None:
    """Normalize a name so word order/punctuation don't matter: "GARCIA; MARIA L." == "Maria L. Garcia" (stretch)."""
    pass


def audit_bill_of_sale(pdf_text: str, extraction: AffidavitExtraction) -> Finding:
    """Check if the bill of sale claim matches what is actually in the PDF text."""
    pass


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
    """Check for logical contradictions in the extracted data."""
    pass


def check_all_fields(
    extraction: AffidavitExtraction,
    source: SourceRecord,
    pdf_text: str,
) -> list[Finding]:
    """Run all comparisons + audit. Provided to attendees."""
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
    """Assign PASS or REVIEW based on findings. Never auto-approve."""
    pass
