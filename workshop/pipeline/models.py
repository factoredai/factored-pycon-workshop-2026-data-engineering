"""Data models for the pipeline.

Mental model mapping:
  AffidavitExtraction = the structured output from the Brain (LLM) or regex shortcut.
  SourceRecord        = the source of truth the Conscience (guardrails) validates against.
  Finding             = one field comparison result from the Conscience.
  Verdict             = the Conscience's final decision: PASS or REVIEW.
"""
from enum import Enum
from pydantic import BaseModel


class ClaimStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "VALUE MISMATCH"
    MISSING = "MISSING"
    EXEMPT = "EXEMPT"


class Finding(BaseModel):
    field: str
    expected_value: str | None
    document_value: str | None
    normalized_expected: str | None
    normalized_document: str | None
    claim_status: ClaimStatus
    reason: str


class VerdictType(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"


class Verdict(BaseModel):
    verdict: VerdictType
    findings: list[Finding]
    review_reasons: list[str]


class AffidavitExtraction(BaseModel):
    consumer_name: str | None = None
    last4: str | None = None
    original_creditor: str | None = None
    debt_buyer: str | None = None
    chargeoff_balance: str | None = None
    chargeoff_date: str | None = None
    last_payment_date: str | None = None
    last_payment_amount: str | None = None
    closing_date: str | None = None
    sale_balance: str | None = None
    transfer_date: str | None = None
    bill_of_sale_attached: bool | None = None


class SourceRecord(BaseModel):
    reference_id: str
    consumer_name: str
    last4: str
    original_creditor: str
    debt_buyer: str
    chargeoff_balance: float
    chargeoff_date: str
    last_payment_date: str
    last_payment_amount: float
    closing_date: str
    sale_balance: float
    transfer_date: str
