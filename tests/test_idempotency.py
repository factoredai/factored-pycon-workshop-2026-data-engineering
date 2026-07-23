"""Tests for Pillar 3: Idempotency (between the Brain and the Conscience)."""
from workshop.pipeline.models import VerdictType
from workshop.pipeline.idempotency import (
    hash_content,
    get_cached_extraction,
    save_to_cache,
    upsert_result,
    get_result_count,
    process_with_cache,
)


class TestHashContent:
    def test_consistent(self):
        h1 = hash_content("hello")
        h2 = hash_content("hello")
        assert h1 == h2

    def test_different_content(self):
        h1 = hash_content("hello")
        h2 = hash_content("world")
        assert h1 != h2

    def test_prompt_version_matters(self):
        h1 = hash_content("hello", prompt_version="v1")
        h2 = hash_content("hello", prompt_version="v2")
        assert h1 != h2


class TestCache:
    def test_round_trip(self, temp_cache, correct_extraction):
        save_to_cache("abc123", correct_extraction, temp_cache)
        loaded = get_cached_extraction("abc123", temp_cache)
        assert loaded is not None
        assert loaded.consumer_name == correct_extraction.consumer_name
        assert loaded.chargeoff_balance == correct_extraction.chargeoff_balance

    def test_miss(self, temp_cache):
        result = get_cached_extraction("nonexistent", temp_cache)
        assert result is None


class TestUpsertResult:
    def test_insert_then_upsert(self, temp_db, correct_extraction, source_record):
        from workshop.pipeline.guardrails import check_all_fields, assign_verdict

        pdf_text = "dummy text BILL OF SALE dummy"
        findings = check_all_fields(correct_extraction, source_record, pdf_text)
        verdict = assign_verdict(findings)

        inserted = upsert_result("ACCT-001", "Buyer A, LLC", "2026-07-01", verdict, temp_db)
        assert inserted is True
        assert get_result_count(temp_db) == 1

        inserted_again = upsert_result("ACCT-001", "Buyer A, LLC", "2026-07-01", verdict, temp_db)
        assert inserted_again is False
        assert get_result_count(temp_db) == 1

    def test_update_changes_verdict(self, temp_db, correct_extraction, hallucinated_extraction, source_record):
        from workshop.pipeline.guardrails import check_all_fields, assign_verdict
        import sqlite3

        pdf_text = "dummy text BILL OF SALE dummy"

        findings_pass = check_all_fields(correct_extraction, source_record, pdf_text)
        verdict_pass = assign_verdict(findings_pass)
        upsert_result("ACCT-001", "Buyer A, LLC", "2026-07-01", verdict_pass, temp_db)

        findings_review = check_all_fields(hallucinated_extraction, source_record, pdf_text)
        verdict_review = assign_verdict(findings_review)
        upsert_result("ACCT-001", "Buyer A, LLC", "2026-07-01", verdict_review, temp_db)

        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT verdict FROM results WHERE reference_id='ACCT-001'").fetchone()
        conn.close()
        assert row[0] == "REVIEW"


class TestCacheInvalidation:
    def test_prompt_version_change_invalidates_cache(self, temp_cache, correct_extraction):
        save_to_cache("abc123", correct_extraction, temp_cache)
        cached_v1 = get_cached_extraction("abc123", temp_cache)
        assert cached_v1 is not None

        new_hash = hash_content("same content", prompt_version="v2")
        cached_v2 = get_cached_extraction(new_hash, temp_cache)
        assert cached_v2 is None

    def test_different_accounts_separate_cache(self, temp_cache, correct_extraction):
        h1 = hash_content("pdf content account 1")
        h2 = hash_content("pdf content account 2")
        save_to_cache(h1, correct_extraction, temp_cache)

        assert get_cached_extraction(h1, temp_cache) is not None
        assert get_cached_extraction(h2, temp_cache) is None


class TestProcessWithCache:
    def test_run_twice_no_duplicates(self, sample_pdf_path, source_record, tmp_path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        db_path = tmp_path / "results.db"

        v1 = process_with_cache(
            sample_pdf_path, source_record,
            cache_dir=cache_dir, db_path=db_path,
        )
        assert v1.verdict == VerdictType.PASS
        assert get_result_count(db_path) == 1

        v2 = process_with_cache(
            sample_pdf_path, source_record,
            cache_dir=cache_dir, db_path=db_path,
        )
        assert v2.verdict == VerdictType.PASS
        assert get_result_count(db_path) == 1

        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 1
