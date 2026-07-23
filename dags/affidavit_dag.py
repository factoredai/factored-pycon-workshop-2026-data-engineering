"""Pillar 4: Orchestration (Airflow DAG).

Mental model mapping:
  The DAG wires all four roles together per buyer:
  Eyes (extract text) -> Regex/Brain (extract fields) -> Conscience (guardrails) -> Judge (review tickets).

Exercise 4 teaches: orchestration with TaskGroups per buyer, separation of
extraction/validation/ticketing concerns, and how Airflow coordinates a
multi-step pipeline without doing the heavy lifting itself.

Design note: in production, the DAG file is a thin orchestrator (30-40
lines of wiring) and the business logic lives in separate modules. Here
we keep everything in one file so you see the full picture in one place
during the exercise. After the workshop, refactor the task bodies out.

Prerequisite: complete Exercises 1-2 first. The DAG tasks call functions
from extract.py and guardrails.py. If those blanks are not solved, the
DAG tasks will fail at runtime.

Trigger manually from the Airflow UI at localhost:8080 with default params
or override target_date.

Note: this file must contain the literal string 'airflow' for Airflow 3
DAG discovery (safe_mode skips files that don't mention airflow).
"""
import csv
import logging
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task, task_group
from airflow.operators.python import get_current_context

# Fixed name (not __name__): Airflow imports DAG files under a mangled module name
# like "unusual_prefix_<hash>_affidavit_dag", which makes log lines hard to read.
logger = logging.getLogger("affidavit_dag")

# Quiet Airflow's per-task "Done. Returned value was: <full XCom>" dump. It prints
# each task's entire return payload (the whole extraction list) and drowns out the
# readable summary lines below. Our own loggers are unaffected (different names).
logging.getLogger("airflow.task.operators").setLevel(logging.WARNING)

BUYERS = ["buyer_a", "buyer_b"]


@dag(
    dag_id="affidavit_validation",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={"target_date": "2026-07-01"},
)
def affidavit_validation_dag() -> None:

    @task
    def download_pdfs(buyer: str) -> list[dict]:
        """List PDF paths for a buyer/date using pdf_manifest.csv for reference_id lookup.

        Directory structure: data/pdfs/{buyer}/{target_date}/*.pdf
        Manifest path: data/seeds/pdf_manifest.csv (maps pdf_stem -> reference_id)
        Get target_date from: get_current_context()["params"]["target_date"]

        Return: list of {"pdf_path": str, "reference_id": str} dicts.

        Provided to attendees (plumbing, not orchestration).
        """
        context = get_current_context()
        target_date = context["params"]["target_date"]

        pdf_dir = Path(f"data/pdfs/{buyer}/{target_date}")
        if not pdf_dir.exists():
            return []

        manifest = {}
        manifest_path = Path("data/seeds/pdf_manifest.csv")
        if manifest_path.exists():
            with open(manifest_path, newline="") as f:
                for row in csv.DictReader(f):
                    manifest[row["pdf_stem"]] = row["reference_id"]

        entries = []
        for pdf_file in sorted(pdf_dir.glob("*.pdf")):
            ref_id = manifest.get(pdf_file.stem, "UNKNOWN")
            entries.append({"pdf_path": str(pdf_file), "reference_id": ref_id})
        return entries

    @task
    def parse_and_extract(pdf_entries: list[dict]) -> list[dict]:
        """Extract data from each PDF using extract_affidavit().

        For each entry: call extract_affidavit(pdf_path). If it raises
        CannedResponseMissing, set status="canned_missing" and extraction=None
        (degrade gracefully instead of crashing the pipeline).

        Return: list of {"pdf_path", "reference_id", "extraction" (dict or None), "status"}.

        Provided to attendees (extraction logic lives in extract.py).
        """
        from workshop.pipeline.extract import extract_affidavit
        from workshop.pipeline.llm_client import CannedResponseMissing

        results = []
        for entry in pdf_entries:
            pdf_path = entry["pdf_path"]
            name = Path(pdf_path).name
            try:
                extraction = extract_affidavit(pdf_path)
                logger.info("extracted %s (%s) -> ok", entry["reference_id"], name)
                results.append({
                    "pdf_path": pdf_path,
                    "reference_id": entry["reference_id"],
                    "extraction": extraction.model_dump(),
                    "status": "ok",
                })
            except CannedResponseMissing:
                logger.warning("no canned response for %s (%s) -> canned_missing", entry["reference_id"], name)
                results.append({
                    "pdf_path": pdf_path,
                    "reference_id": entry["reference_id"],
                    "extraction": None,
                    "status": "canned_missing",
                })
        return results

    @task
    def load_source_records() -> dict:
        """Load source_of_truth.csv into a dict keyed by reference_id. Provided to attendees."""
        records = {}
        with open("data/seeds/source_of_truth.csv", newline="") as f:
            for row in csv.DictReader(f):
                records[row["reference_id"]] = row
        return records

    @task
    def validate_results(extractions: list[dict], source_records: dict) -> list[dict]:
        """Assign a verdict to each extraction against source data.

        Each entry in extractions is a dict with keys:
            "pdf_path", "reference_id", "extraction" (dict or None), "status" ("ok" or "canned_missing")

        source_records is a dict keyed by reference_id, where each value is a
        CSV row dict (string values, e.g. {"chargeoff_balance": "6218.55", ...}).

        Logic:
        1. If status != "ok" or extraction is None -> verdict REVIEW
           ("LLM extraction unavailable, manual review needed").
        2. If reference_id not in source_records -> verdict REVIEW.
        3. Otherwise: build SourceRecord from the CSV row (float() the amount
           fields), build AffidavitExtraction from extraction dict, run
           check_all_fields + assign_verdict from guardrails.py.

        Return: list of {"reference_id", "verdict" (str), "reasons" (list[str])}.

        Workshop blank A (stretch): implement status branching.
        """
        from workshop.pipeline.models import (
            AffidavitExtraction,
            SourceRecord,
            VerdictType,
        )
        from workshop.pipeline.guardrails import check_all_fields, assign_verdict
        from workshop.pipeline.extract import read_pdf

        validated = []
        for entry in extractions:
            ref_id = entry["reference_id"]

            if entry["status"] != "ok" or entry["extraction"] is None:
                validated.append({
                    "reference_id": ref_id,
                    "verdict": VerdictType.REVIEW.value,
                    "reasons": ["LLM extraction unavailable, manual review needed"],
                })
                continue

            source_row = source_records.get(ref_id)
            if source_row is None:
                validated.append({
                    "reference_id": ref_id,
                    "verdict": VerdictType.REVIEW.value,
                    "reasons": [f"No source record found for {ref_id}"],
                })
                continue

            source = SourceRecord(
                reference_id=source_row["reference_id"],
                consumer_name=source_row["consumer_name"],
                last4=source_row["last4"],
                original_creditor=source_row["original_creditor"],
                debt_buyer=source_row["debt_buyer"],
                chargeoff_balance=float(source_row["chargeoff_balance"]),
                chargeoff_date=source_row["chargeoff_date"],
                last_payment_date=source_row["last_payment_date"],
                last_payment_amount=float(source_row["last_payment_amount"]),
                closing_date=source_row["closing_date"],
                sale_balance=float(source_row["sale_balance"]),
                transfer_date=source_row["transfer_date"],
            )

            extraction = AffidavitExtraction(**entry["extraction"])
            pdf_text = read_pdf(entry["pdf_path"])
            findings = check_all_fields(extraction, source, pdf_text)
            verdict = assign_verdict(findings)

            validated.append({
                "reference_id": ref_id,
                "verdict": verdict.verdict.value,
                "reasons": verdict.review_reasons,
            })
        return validated

    @task
    def create_review_tickets(validated: list[dict], buyer: str) -> None:
        """Log REVIEW verdicts. Simulates Jira ticket creation in production.

        Each entry in validated is a dict with keys:
            "reference_id" (str), "verdict" ("PASS" or "REVIEW"), "reasons" (list[str])

        For entries where verdict == "REVIEW", log the buyer, reference_id,
        and reasons (use logger.warning). Skip PASS entries silently.

        Workshop blank B (core): define the task.
        """
        for entry in validated:
            if entry["verdict"] == "REVIEW":
                logger.warning(
                    "[REVIEW] %s / %s: %s",
                    buyer,
                    entry["reference_id"],
                    ", ".join(entry["reasons"]),
                )

    @task_group
    def process_buyer(buyer: str, source_records: dict) -> None:
        """Wire up tasks in sequence per buyer.

        In Airflow's TaskFlow API, dependencies are implicit: passing the
        return value of one task as the argument to the next creates the
        dependency edge. No >> operator needed. Example:

            pdfs = download_pdfs(buyer)           # runs first
            extractions = parse_and_extract(pdfs)  # waits for pdfs

        Airflow sees that parse_and_extract needs the output of download_pdfs,
        so it schedules them in order.

        Workshop blank C (core): define the task group wiring.
        """
        pdfs = download_pdfs(buyer)
        extractions = parse_and_extract(pdfs)
        validated = validate_results(extractions, source_records)
        create_review_tickets(validated, buyer)

    # DAG wiring (runs at parse time, builds the graph):
    # load_source_records runs once, shared across all buyer groups.
    # The for loop creates one TaskGroup per buyer with a unique group_id.
    sources = load_source_records()
    for buyer in BUYERS:
        process_buyer.override(group_id=f"process_{buyer}")(buyer, sources)


affidavit_validation_dag()
