"""Pillar 1: Extraction (Eyes + Regex shortcut + Brain fallback).

Mental model mapping:
  Eyes   = read_pdf() via pypdf. Reads raw text faithfully.
  Regex  = deterministic_extract(). Shortcut that bypasses the Brain on known formats.
  Brain  = extract_with_llm(). LLM fallback when regex fails.
"""
import re
from pypdf import PdfReader

from workshop.pipeline.models import AffidavitExtraction
from workshop.pipeline.llm_client import extract_with_llm

FIELD_PATTERNS = {
    "consumer_name": r"Consumer\s+Name:\s+(.+)",
    "last4": r"Account\s+Last\s+4(?:\s+Digits)?:\s+(\d{4})",
    "original_creditor": r"Original\s+Creditor:\s+(.+)",
    "debt_buyer": r"Debt\s+Buyer:\s+(.+)",
    "chargeoff_balance": r"Charge[- ]?off\s+Balance:\s*(\$[\d,]+\.\d{2})",
    "chargeoff_date": r"Charge[- ]?off\s+Date:\s+(\d{2}/\d{2}/\d{4})",
    "last_payment_date": r"Last\s+Payment\s+Date:\s+(\d{2}/\d{2}/\d{4})",
    "last_payment_amount": r"Last\s+Payment\s+Amount:\s*(\$[\d,]+\.\d{2})",
    "closing_date": r"Closing\s+Date:\s+(\d{2}/\d{2}/\d{4})",
    "sale_balance": r"Sale\s+Balance:\s*(\$[\d,]+\.\d{2})",
    "transfer_date": r"Transfer\s+Date:\s+(\d{2}/\d{2}/\d{4})",
}

HEADING_PATTERN = r"(?:^|\n)\s*(?:BILL\s+OF\s+SALE|CHARGED-OFF\s+ACCOUNT(?:S)?\s+ASSIGNMENT)\s*(?:\n|$)"


def read_pdf(pdf_path: str) -> str:
    """Eyes: read all text from a PDF using pypdf."""
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def detect_pdf_type(pdf_path: str) -> str:
    """Eyes check: classify a PDF as 'native' or 'scanned'."""
    pass


def deterministic_extract(pdf_text: str) -> AffidavitExtraction | None:
    """Regex shortcut: extract fields from known labeled formats. Return None if any field is missing."""
    pass


def extract_affidavit(
    pdf_path: str,
    variant: str = "correct",
    use_live_api: bool | None = None,
) -> AffidavitExtraction:
    """Hybrid extraction: Eyes -> Regex shortcut -> Brain fallback.

    use_live_api: None (default) auto-detects live mode from the environment
    (an API key present -> real LLM, otherwise canned). Pass True/False to force.
    """
    pass


if __name__ == "__main__":
    # Watch your Exercise 1 code run on a single PDF, no Docker needed (once the
    # blanks above are implemented):
    #   python -m workshop.pipeline.extract                 # a messy PDF -> Brain
    #   python -m workshop.pipeline.extract data/pdfs/buyer_a/2026-07-01/acct_1234_standard.pdf
    # Set an API key (see README "Live LLM Mode") and the Brain calls a real LLM;
    # otherwise it uses canned responses.
    import argparse
    import logging

    parser = argparse.ArgumentParser(description="Run extraction on one PDF (Exercise 1).")
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default="data/pdfs/buyer_b/2026-07-01/acct_9012_narrative.pdf",
        help="Path to a PDF (defaults to a messy one that needs the Brain).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(extract_affidavit(args.pdf_path).model_dump_json(indent=2))
