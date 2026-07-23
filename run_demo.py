"""
Self-contained vertical slice demo. Runs the full pipeline on one PDF:
  Eyes (pypdf) -> Brain (canned LLM) -> Conscience (guardrails) -> verdict.

Works on both main (blanked) and solutions branches.
Uses canned LLM responses only (no API key needed).

Usage:
    python run_demo.py                          # Correct extraction -> PASS
    python run_demo.py --variant hallucinated   # Wrong amount -> REVIEW (main demo)
    python run_demo.py --variant hallucinated_dates  # Payment after chargeoff -> REVIEW
"""
import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

from workshop.pipeline.models import (
    AffidavitExtraction,
    ClaimStatus,
    Finding,
    SourceRecord,
    Verdict,
    VerdictType,
)

VALID_VARIANTS = ("correct", "hallucinated", "hallucinated_dates")

AMOUNT_FIELDS = {"chargeoff_balance", "last_payment_amount", "sale_balance"}
DATE_FIELDS = {"chargeoff_date", "last_payment_date", "closing_date", "transfer_date"}


def load_source_of_truth(reference_id: str = "ACCT-001") -> SourceRecord:
    with open("data/seeds/source_of_truth.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["reference_id"] == reference_id:
                return SourceRecord(
                    reference_id=row["reference_id"],
                    consumer_name=row["consumer_name"],
                    last4=row["last4"],
                    original_creditor=row["original_creditor"],
                    debt_buyer=row["debt_buyer"],
                    chargeoff_balance=float(row["chargeoff_balance"]),
                    chargeoff_date=row["chargeoff_date"],
                    last_payment_date=row["last_payment_date"],
                    last_payment_amount=float(row["last_payment_amount"]),
                    closing_date=row["closing_date"],
                    sale_balance=float(row["sale_balance"]),
                    transfer_date=row["transfer_date"],
                )
    raise ValueError(f"Reference ID {reference_id} not found in source_of_truth.csv")


def read_pdf_text(pdf_path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def load_canned_extraction(pdf_path: str, variant: str = "correct") -> AffidavitExtraction:
    pdf_stem = Path(pdf_path).stem
    canned_file = Path("data/canned_llm") / pdf_stem / f"{variant}.json"
    if not canned_file.exists():
        raise FileNotFoundError(
            f"No canned response for variant '{variant}' of '{pdf_stem}' "
            f"(looked for {canned_file})"
        )
    data = json.loads(canned_file.read_text())
    return AffidavitExtraction(**data)


def normalize_amount(raw: float | int | str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = re.sub(r"[$ ,]", "", text)
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def normalize_date(raw: str | None) -> str | None:
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
    try:
        dt = datetime.strptime(text, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    return text


def _compare_field(
    field_name: str,
    expected: str | float | int | None,
    extracted: str | None,
) -> Finding:
    is_amount = field_name in AMOUNT_FIELDS
    is_date = field_name in DATE_FIELDS

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

    return Finding(
        field=field_name,
        expected_value=str(expected) if expected is not None else None,
        document_value=extracted,
        normalized_expected=str(norm_exp),
        normalized_document=str(norm_doc),
        claim_status=ClaimStatus.MATCH if match else ClaimStatus.MISMATCH,
        reason=f"{field_name}: {'values match' if match else 'VALUE MISMATCH'}",
    )


def _audit_bill_of_sale(pdf_text: str, extraction: AffidavitExtraction) -> Finding:
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

    heading_found = bool(
        re.search(
            r"BILL\s+OF\s+SALE|CHARGED-OFF\s+ACCOUNT(?:S)?\s+ASSIGNMENT",
            pdf_text,
            re.IGNORECASE,
        )
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


def _check_statement_contradiction(
    extraction: AffidavitExtraction,
    source: SourceRecord,
) -> Finding | None:
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


def compare_and_verdict(
    extraction: AffidavitExtraction,
    source: SourceRecord,
    pdf_text: str,
) -> Verdict:
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
        findings.append(_compare_field(field_name, expected, extracted))

    findings.append(_audit_bill_of_sale(pdf_text, extraction))

    contradiction = _check_statement_contradiction(extraction, source)
    if contradiction is not None:
        findings.append(contradiction)

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


def print_findings_table(verdict: Verdict) -> None:
    green = "\033[92m"
    red = "\033[91m"
    yellow = "\033[93m"
    reset = "\033[0m"
    bold = "\033[1m"

    print(f"\n{bold}{'='*80}{reset}")
    print(f"{bold}{'FIELD':<28} {'STATUS':<18} {'EXPECTED':<16} {'EXTRACTED':<16}{reset}")
    print(f"{'='*80}")

    for f in verdict.findings:
        if f.claim_status == ClaimStatus.MATCH:
            color = green
        elif f.claim_status == ClaimStatus.EXEMPT:
            color = yellow
        else:
            color = red

        expected = (f.normalized_expected or "N/A")[:15]
        extracted = (f.normalized_document or "N/A")[:15]
        status = f.claim_status.value

        print(f"{f.field:<28} {color}{status:<18}{reset} {expected:<16} {extracted:<16}")

    print(f"{'='*80}")

    if verdict.verdict == VerdictType.PASS:
        print(f"\n{green}{bold}VERDICT: PASS{reset}")
    else:
        print(f"\n{red}{bold}VERDICT: REVIEW{reset}")
        for reason in verdict.review_reasons:
            print(f"  {red}- {reason}{reset}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Vertical slice demo")
    parser.add_argument(
        "--variant",
        choices=VALID_VARIANTS,
        default="correct",
        help="Which canned LLM variant to use.",
    )
    parser.add_argument("--pdf", default="data/pdfs/sample_affidavit.pdf")
    args = parser.parse_args()

    source = load_source_of_truth()
    pdf_text = read_pdf_text(args.pdf)
    extraction = load_canned_extraction(args.pdf, args.variant)
    verdict = compare_and_verdict(extraction, source, pdf_text)
    print_findings_table(verdict)


if __name__ == "__main__":
    main()
