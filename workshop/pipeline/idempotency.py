"""Pillar 3: Idempotency (content-hash cache + SQLite upsert).

Mental model mapping:
  This module sits between the Brain and the Conscience. It caches the Brain's
  output so re-runs skip expensive LLM calls, and stores the Conscience's
  verdict so running twice produces zero duplicates.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

from workshop.pipeline.models import (
    AffidavitExtraction,
    SourceRecord,
    Verdict,
)

CACHE_DIR = Path("data/cache")
DB_PATH = Path("data/results.db")
PROMPT_VERSION = "v1"


def init_db(db_path: Path = DB_PATH) -> None:
    """Create the results table if it does not exist. Provided to attendees."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            reference_id TEXT NOT NULL,
            buyer TEXT NOT NULL,
            process_date TEXT NOT NULL,
            verdict TEXT NOT NULL,
            review_reasons TEXT,
            findings TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (reference_id, buyer, process_date)
        )
    """)
    conn.commit()
    conn.close()


def hash_content(content: str, prompt_version: str = PROMPT_VERSION) -> str:
    """Create a cache key from content and prompt version."""
    pass


def get_cached_extraction(
    content_hash: str,
    cache_dir: Path = CACHE_DIR,
) -> AffidavitExtraction | None:
    """Load cached extraction if it exists. Provided to attendees."""
    cache_file = cache_dir / f"{content_hash}.json"
    if not cache_file.exists():
        return None
    data = json.loads(cache_file.read_text())
    return AffidavitExtraction(**data)


def save_to_cache(
    content_hash: str,
    extraction: AffidavitExtraction,
    cache_dir: Path = CACHE_DIR,
) -> None:
    """Save extraction to cache. Provided to attendees."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{content_hash}.json"
    cache_file.write_text(json.dumps(extraction.model_dump(), indent=2))


def upsert_result(
    reference_id: str,
    buyer: str,
    process_date: str,
    verdict: Verdict,
    db_path: Path = DB_PATH,
) -> bool:
    """Insert or update a result row by reference_id. Return True if new, False if updated."""
    pass


def get_result_count(db_path: Path = DB_PATH) -> int:
    """Return total row count in results table. Used by tests."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM results")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def process_with_cache(
    pdf_path: str,
    source: SourceRecord,
    variant: str = "correct",
    process_date: str = "2026-07-01",
    cache_dir: Path = CACHE_DIR,
    db_path: Path = DB_PATH,
) -> Verdict:
    """Full idempotent pipeline: read -> cache check -> extract -> guardrails -> upsert."""
    init_db(db_path)

    from workshop.pipeline.extract import read_pdf, extract_affidavit
    from workshop.pipeline.guardrails import check_all_fields, assign_verdict

    text = read_pdf(pdf_path)
    h = hash_content(text)

    cached = get_cached_extraction(h, cache_dir)
    if cached is not None:
        extraction = cached
    else:
        extraction = extract_affidavit(pdf_path, variant=variant)
        save_to_cache(h, extraction, cache_dir)

    findings = check_all_fields(extraction, source, text)
    verdict = assign_verdict(findings)

    upsert_result(
        reference_id=source.reference_id,
        buyer=source.debt_buyer,
        process_date=process_date,
        verdict=verdict,
        db_path=db_path,
    )

    return verdict
