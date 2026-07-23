"""Pillar 1: Extraction (Eyes + Regex shortcut + Brain fallback).

Mental model mapping:
  Eyes   = read_pdf() via pypdf. Reads raw text faithfully.
  Regex  = deterministic_extract(). Shortcut that bypasses the Brain on known formats.
  Brain  = extract_with_llm(). LLM fallback when regex fails.

Exercise 1 teaches: regex works on clean labeled formats, fails on narrative
prose or different layouts. The LLM handles both. Choose your tool based on
the PDF structure.
"""
import logging
import re
from pathlib import Path

from pypdf import PdfReader

from workshop.pipeline.models import AffidavitExtraction
from workshop.pipeline.llm_client import extract_with_llm, live_mode_enabled

logger = logging.getLogger(__name__)

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
    """Eyes: extract all text from a PDF using pypdf. Faithful copy, no interpretation."""
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def detect_pdf_type(pdf_path: str) -> str:
    """Eyes check: return 'native' if pypdf extracts meaningful text (>100 chars), else 'scanned'.

    Native PDFs have embedded text. Scanned PDFs are images with no extractable text.
    Native -> regex can try first, then LLM fallback.
    Scanned -> go straight to the LLM (Brain reads the image directly).

    Workshop blank A (core).
    """
    text = read_pdf(pdf_path)
    if len(text.strip()) > 100:
        return "native"
    return "scanned"


def deterministic_extract(pdf_text: str) -> AffidavitExtraction | None:
    """Use FIELD_PATTERNS to extract labeled fields from Format A PDFs.

    For each pattern in FIELD_PATTERNS: search pdf_text for a match.
    If ANY field is not found, return None (this format does not match).
    Also check for a bill of sale heading using HEADING_PATTERN.

    Workshop blank B (core).
    """
    result = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, pdf_text)
        if match:
            result[field] = match.group(1).strip()
        else:
            return None

    result["bill_of_sale_attached"] = bool(
        re.search(HEADING_PATTERN, pdf_text, re.IGNORECASE)
    )
    return AffidavitExtraction(**result)


def extract_affidavit(
    pdf_path: str,
    variant: str = "correct",
    use_live_api: bool | None = None,
) -> AffidavitExtraction:
    """Hybrid extraction: Eyes -> Regex shortcut -> Brain fallback.

    Eyes (pypdf) extract raw text. Regex tries known patterns.
    If regex succeeds, return structured output (skip the Brain).
    If regex fails, the Brain (LLM) interprets the text and returns structured fields.

    use_live_api: None (default) auto-detects live mode from the environment (an
    API key present -> real LLM, otherwise canned). Pass True/False to force it.

    Workshop blank C (stretch).
    """
    if use_live_api is None:
        use_live_api = live_mode_enabled()

    text = read_pdf(pdf_path)
    det = deterministic_extract(text)
    if det is not None and variant == "correct":
        logger.info("Regex shortcut hit for %s (Brain skipped)", Path(pdf_path).name)
        return det

    logger.info(
        "Regex missed for %s -> Brain fallback (%s)",
        Path(pdf_path).name,
        "live LLM" if use_live_api else "canned",
    )
    return extract_with_llm(
        pdf_path=pdf_path, variant=variant,
        pdf_text=text, use_live_api=use_live_api,
    )


if __name__ == "__main__":
    # Watch your Exercise 1 code run on a single PDF, no Docker needed:
    #   python -m workshop.pipeline.extract                 # a messy PDF -> Brain
    #   python -m workshop.pipeline.extract data/pdfs/buyer_a/2026-07-01/acct_1234_standard.pdf
    # Set an API key (see README "Live LLM Mode") and the Brain calls a real LLM;
    # otherwise it uses canned responses. The INFO log shows regex-vs-Brain either way.
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
