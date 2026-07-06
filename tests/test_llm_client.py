import os
import pytest
from workshop.pipeline.llm_client import extract_with_llm, CannedResponseMissing


def test_canned_correct_returns_valid_extraction(sample_pdf_path):
    result = extract_with_llm(pdf_path=sample_pdf_path, variant="correct")
    assert result.consumer_name == "Jane M. Doe"
    assert result.last4 == "7890"
    assert result.chargeoff_balance == "$6,218.55"
    assert result.bill_of_sale_attached is True


def test_canned_hallucinated_returns_wrong_balance(sample_pdf_path):
    result = extract_with_llm(pdf_path=sample_pdf_path, variant="hallucinated")
    assert result.chargeoff_balance == "$8,218.55"
    assert result.consumer_name == "Jane M. Doe"


def test_canned_hallucinated_dates_returns_late_payment(sample_pdf_path):
    result = extract_with_llm(pdf_path=sample_pdf_path, variant="hallucinated_dates")
    assert result.last_payment_date == "05/20/2024"
    assert result.chargeoff_balance == "$6,218.55"


def test_missing_variant_raises_canned_response_missing(sample_pdf_path):
    with pytest.raises(CannedResponseMissing):
        extract_with_llm(pdf_path=sample_pdf_path, variant="nonexistent_variant")


def test_missing_pdf_stem_raises_canned_response_missing():
    with pytest.raises((CannedResponseMissing, FileNotFoundError)):
        extract_with_llm(pdf_path="data/pdfs/no_such_file.pdf", variant="correct")


def test_live_api_requires_pdf_text():
    with pytest.raises(ValueError, match="pdf_text is required"):
        extract_with_llm(
            pdf_path="data/pdfs/sample_affidavit.pdf",
            use_live_api=True,
            pdf_text="",
        )


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"),
    reason="No LLM API key set (ANTHROPIC_API_KEY or OPENAI_API_KEY)",
)
def test_live_api_extracts_from_pdf(sample_pdf_path):
    from workshop.pipeline.extract import read_pdf
    text = read_pdf(sample_pdf_path)
    result = extract_with_llm(
        pdf_path=sample_pdf_path,
        pdf_text=text,
        use_live_api=True,
    )
    assert result.consumer_name is not None
    assert result.chargeoff_balance is not None
    assert result.last4 is not None
