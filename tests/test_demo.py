from workshop.pipeline.models import VerdictType, ClaimStatus


def test_correct_variant_produces_pass(sample_pdf_path, source_record):
    from run_demo import load_canned_extraction, compare_and_verdict, read_pdf_text

    pdf_text = read_pdf_text(sample_pdf_path)
    extraction = load_canned_extraction(sample_pdf_path, variant="correct")
    verdict = compare_and_verdict(extraction, source_record, pdf_text)

    assert verdict.verdict == VerdictType.PASS
    assert len(verdict.review_reasons) == 0
    for f in verdict.findings:
        assert f.claim_status in (ClaimStatus.MATCH, ClaimStatus.EXEMPT)


def test_hallucinated_variant_produces_review(sample_pdf_path, source_record):
    from run_demo import load_canned_extraction, compare_and_verdict, read_pdf_text

    pdf_text = read_pdf_text(sample_pdf_path)
    extraction = load_canned_extraction(sample_pdf_path, variant="hallucinated")
    verdict = compare_and_verdict(extraction, source_record, pdf_text)

    assert verdict.verdict == VerdictType.REVIEW
    assert len(verdict.review_reasons) > 0
    mismatch_fields = [f.field for f in verdict.findings if f.claim_status == ClaimStatus.MISMATCH]
    assert "chargeoff_balance" in mismatch_fields


def test_hallucinated_dates_variant_produces_review(sample_pdf_path, source_record):
    from run_demo import load_canned_extraction, compare_and_verdict, read_pdf_text

    pdf_text = read_pdf_text(sample_pdf_path)
    extraction = load_canned_extraction(sample_pdf_path, variant="hallucinated_dates")
    verdict = compare_and_verdict(extraction, source_record, pdf_text)

    assert verdict.verdict == VerdictType.REVIEW
    assert len(verdict.review_reasons) > 0
    mismatch_fields = [f.field for f in verdict.findings if f.claim_status == ClaimStatus.MISMATCH]
    assert "last_payment_date" in mismatch_fields


def test_hallucinated_dates_has_contradiction_finding(sample_pdf_path, source_record):
    from run_demo import load_canned_extraction, compare_and_verdict, read_pdf_text

    pdf_text = read_pdf_text(sample_pdf_path)
    extraction = load_canned_extraction(sample_pdf_path, variant="hallucinated_dates")
    verdict = compare_and_verdict(extraction, source_record, pdf_text)

    contradiction_findings = [
        f for f in verdict.findings
        if "contradiction" in f.reason.lower() or "after chargeoff" in f.reason.lower()
    ]
    assert len(contradiction_findings) >= 1
