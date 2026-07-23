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
        """Conscience in the DAG: validate each extraction against source of truth (stretch)."""
        pass
        return []

    @task
    def create_review_tickets(validated: list[dict], buyer: str) -> None:
        """Judge routing: log REVIEW cases for human review."""
        pass

    @task_group
    def process_buyer(buyer: str, source_records: dict) -> None:
        """Wire Eyes -> Regex/Brain -> Conscience -> Judge in sequence for this buyer."""
        pass

    # DAG wiring (runs at parse time, builds the graph):
    # load_source_records runs once, shared across all buyer groups.
    # The for loop creates one TaskGroup per buyer with a unique group_id.
    sources = load_source_records()
    for buyer in BUYERS:
        process_buyer.override(group_id=f"process_{buyer}")(buyer, sources)


affidavit_validation_dag()
