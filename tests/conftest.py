import pytest
from pathlib import Path

from workshop.pipeline.models import AffidavitExtraction, SourceRecord


@pytest.fixture(autouse=True)
def _no_live_llm_keys(monkeypatch):
    """Keep the test suite hermetic: never let a real API key reach a test.

    If a blank's implementation hardcodes use_live_api=True instead of threading
    the parameter through, this turns that bug into an immediate RuntimeError
    instead of a slow, silent, real API call.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


SAMPLE_PDF = "data/pdfs/sample_affidavit.pdf"
FORMAT_A_BUYER_A = "data/pdfs/buyer_a/2026-07-01/acct_1234_standard.pdf"
FORMAT_B_BUYER_A = "data/pdfs/buyer_a/2026-07-01/acct_5678_variant.pdf"
FORMAT_B_BUYER_B = "data/pdfs/buyer_b/2026-07-01/acct_9012_narrative.pdf"
FORMAT_B_FOOTER_BOS = "data/pdfs/buyer_a/2026-07-01/acct_2468_footer_bos.pdf"
FORMAT_A_ALT_LABELS = "data/pdfs/buyer_a/2026-07-01/acct_1357_alt_labels.pdf"
FORMAT_C_TABLE = "data/pdfs/buyer_a/2026-07-01/acct_8899_table.pdf"
FORMAT_D_ALT_FIELDS = "data/pdfs/buyer_b/2026-07-01/acct_3377_alt_fields.pdf"
FORMAT_E_MULTI_AMOUNTS = "data/pdfs/buyer_b/2026-07-01/acct_6644_multi_amounts.pdf"


@pytest.fixture
def sample_pdf_path() -> str:
    path = Path(SAMPLE_PDF)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_a
        make_format_a()
    return str(path)


@pytest.fixture
def format_a_buyer_a_path() -> str:
    path = Path(FORMAT_A_BUYER_A)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_a_buyer, ACCT_002_DATA
        make_format_a_buyer(FORMAT_A_BUYER_A, ACCT_002_DATA)
    return str(path)


@pytest.fixture
def format_b_buyer_a_path() -> str:
    path = Path(FORMAT_B_BUYER_A)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_b
        make_format_b()
    return str(path)


@pytest.fixture
def format_b_buyer_b_path() -> str:
    path = Path(FORMAT_B_BUYER_B)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_b_buyer_b
        make_format_b_buyer_b()
    return str(path)


@pytest.fixture
def format_b_footer_bos_path() -> str:
    path = Path(FORMAT_B_FOOTER_BOS)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_b_footer_bos
        make_format_b_footer_bos()
    return str(path)


@pytest.fixture
def format_a_alt_labels_path() -> str:
    path = Path(FORMAT_A_ALT_LABELS)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_a_alt_labels
        make_format_a_alt_labels()
    return str(path)


@pytest.fixture
def format_c_table_path() -> str:
    path = Path(FORMAT_C_TABLE)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_c_table
        make_format_c_table()
    return str(path)


@pytest.fixture
def format_d_alt_fields_path() -> str:
    path = Path(FORMAT_D_ALT_FIELDS)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_d_alt_field_names
        make_format_d_alt_field_names()
    return str(path)


@pytest.fixture
def format_e_multi_amounts_path() -> str:
    path = Path(FORMAT_E_MULTI_AMOUNTS)
    if not path.exists():
        from scripts.make_sample_pdf import make_format_e_multi_amounts
        make_format_e_multi_amounts()
    return str(path)


@pytest.fixture
def source_record_005() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-005",
        consumer_name="Alice B. Cooper",
        last4="8899",
        original_creditor="Summit Credit Union",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance=5400.00,
        chargeoff_date="2024-07-01",
        last_payment_date="2024-06-15",
        last_payment_amount=90.00,
        closing_date="2024-06-30",
        sale_balance=5650.00,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def source_record_006() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-006",
        consumer_name="David E. Torres",
        last4="3377",
        original_creditor="Heritage National Bank",
        debt_buyer="Buyer B, LLC",
        chargeoff_balance=4125.60,
        chargeoff_date="2024-04-20",
        last_payment_date="2024-03-01",
        last_payment_amount=100.00,
        closing_date="2024-06-30",
        sale_balance=4300.00,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def source_record_007() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-007",
        consumer_name="Patricia N. Wells",
        last4="6644",
        original_creditor="Lakeside Federal Bank",
        debt_buyer="Buyer B, LLC",
        chargeoff_balance=7892.15,
        chargeoff_date="2024-05-15",
        last_payment_date="2024-04-02",
        last_payment_amount=175.00,
        closing_date="2024-06-30",
        sale_balance=8200.00,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def source_record_004() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-004",
        consumer_name="Robert A. Johnson",
        last4="2468",
        original_creditor="Pacific Trust Bank",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance=8750.30,
        chargeoff_date="2024-05-01",
        last_payment_date="2024-03-22",
        last_payment_amount=125.00,
        closing_date="2024-06-30",
        sale_balance=9100.50,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def source_record() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-001",
        consumer_name="Jane M. Doe",
        last4="7890",
        original_creditor="First National Bank",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance=6218.55,
        chargeoff_date="2024-03-15",
        last_payment_date="2024-01-10",
        last_payment_amount=150.00,
        closing_date="2024-06-30",
        sale_balance=6418.22,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def source_record_002() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-002",
        consumer_name="John R. Smith",
        last4="4321",
        original_creditor="Metro Credit Union",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance=12450.00,
        chargeoff_date="2024-02-28",
        last_payment_date="2024-01-05",
        last_payment_amount=200.00,
        closing_date="2024-06-30",
        sale_balance=12890.33,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def source_record_003() -> SourceRecord:
    return SourceRecord(
        reference_id="ACCT-003",
        consumer_name="Maria L. Garcia",
        last4="5555",
        original_creditor="Coastal Savings Bank",
        debt_buyer="Buyer B, LLC",
        chargeoff_balance=3200.75,
        chargeoff_date="2024-04-10",
        last_payment_date="2024-02-20",
        last_payment_amount=75.00,
        closing_date="2024-06-30",
        sale_balance=3350.00,
        transfer_date="2024-07-15",
    )


@pytest.fixture
def correct_extraction() -> AffidavitExtraction:
    return AffidavitExtraction(
        consumer_name="Jane M. Doe",
        last4="7890",
        original_creditor="First National Bank",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance="$6,218.55",
        chargeoff_date="03/15/2024",
        last_payment_date="01/10/2024",
        last_payment_amount="$150.00",
        closing_date="06/30/2024",
        sale_balance="$6,418.22",
        transfer_date="07/15/2024",
        bill_of_sale_attached=True,
    )


@pytest.fixture
def hallucinated_extraction() -> AffidavitExtraction:
    return AffidavitExtraction(
        consumer_name="Jane M. Doe",
        last4="7890",
        original_creditor="First National Bank",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance="$8,218.55",
        chargeoff_date="03/15/2024",
        last_payment_date="01/10/2024",
        last_payment_amount="$150.00",
        closing_date="06/30/2024",
        sale_balance="$6,418.22",
        transfer_date="07/15/2024",
        bill_of_sale_attached=True,
    )


@pytest.fixture
def hallucinated_dates_extraction() -> AffidavitExtraction:
    return AffidavitExtraction(
        consumer_name="Jane M. Doe",
        last4="7890",
        original_creditor="First National Bank",
        debt_buyer="Buyer A, LLC",
        chargeoff_balance="$6,218.55",
        chargeoff_date="03/15/2024",
        last_payment_date="05/20/2024",
        last_payment_amount="$150.00",
        closing_date="06/30/2024",
        sale_balance="$6,418.22",
        transfer_date="07/15/2024",
        bill_of_sale_attached=True,
    )


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test_results.db"
    from workshop.pipeline.idempotency import init_db
    init_db(db_path)
    return db_path


@pytest.fixture
def temp_cache(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir
