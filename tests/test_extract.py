"""Tests for Pillar 1: Extraction (Eyes + Regex shortcut + Brain fallback)."""
import pytest
from workshop.pipeline.extract import (
    read_pdf,
    detect_pdf_type,
    deterministic_extract,
    extract_affidavit,
)


class TestExtractText:
    def test_read_pdf_returns_content(self, sample_pdf_path):
        text = read_pdf(sample_pdf_path)
        assert len(text) > 100
        assert "Jane M. Doe" in text


class TestDetectPdfType:
    def test_native_pdf(self, sample_pdf_path):
        assert detect_pdf_type(sample_pdf_path) == "native"

    def test_format_a_buyer_a(self, format_a_buyer_a_path):
        assert detect_pdf_type(format_a_buyer_a_path) == "native"

    def test_format_b_buyer_a(self, format_b_buyer_a_path):
        assert detect_pdf_type(format_b_buyer_a_path) == "native"

    def test_blank_pdf_scanned(self, tmp_path):
        from fpdf import FPDF
        blank_pdf = tmp_path / "blank.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.output(str(blank_pdf))
        assert detect_pdf_type(str(blank_pdf)) == "scanned"

    def test_barely_enough_text_is_native(self, tmp_path):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, "x" * 101)
        sparse_pdf = tmp_path / "sparse.pdf"
        pdf.output(str(sparse_pdf))
        assert detect_pdf_type(str(sparse_pdf)) == "native"

    def test_just_under_threshold_scanned(self, tmp_path):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, "x" * 99)
        sparse_pdf = tmp_path / "tiny.pdf"
        pdf.output(str(sparse_pdf))
        assert detect_pdf_type(str(sparse_pdf)) == "scanned"


class TestDeterministicExtract:
    def test_clean_format_returns_all_fields(self, sample_pdf_path):
        text = read_pdf(sample_pdf_path)
        result = deterministic_extract(text)
        assert result is not None
        assert result.consumer_name == "Jane M. Doe"
        assert result.last4 == "7890"
        assert result.original_creditor == "First National Bank"
        assert result.debt_buyer == "Buyer A, LLC"
        assert result.chargeoff_balance == "$6,218.55"
        assert result.chargeoff_date == "03/15/2024"
        assert result.last_payment_date == "01/10/2024"
        assert result.last_payment_amount == "$150.00"
        assert result.closing_date == "06/30/2024"
        assert result.sale_balance == "$6,418.22"
        assert result.transfer_date == "07/15/2024"
        assert result.bill_of_sale_attached is True

    def test_format_a_buyer_a(self, format_a_buyer_a_path):
        text = read_pdf(format_a_buyer_a_path)
        result = deterministic_extract(text)
        assert result is not None
        assert result.consumer_name == "John R. Smith"
        assert result.last4 == "4321"
        assert result.chargeoff_balance == "$12,450.00"
        assert result.bill_of_sale_attached is True

    def test_variant_format_returns_none(self, format_b_buyer_a_path):
        text = read_pdf(format_b_buyer_a_path)
        result = deterministic_extract(text)
        assert result is None


    @pytest.mark.stretch
    def test_alt_labels_format(self, format_a_alt_labels_path):
        """Labels with extra whitespace (e.g. 'Consumer  Name:') should still extract."""
        text = read_pdf(format_a_alt_labels_path)
        result = deterministic_extract(text)
        assert result is not None
        assert result.consumer_name == "Robert A. Johnson"
        assert result.last4 == "2468"
        assert result.chargeoff_balance == "$8,750.30"
        assert result.bill_of_sale_attached is True

    def test_footer_bos_returns_none(self, format_b_footer_bos_path):
        text = read_pdf(format_b_footer_bos_path)
        result = deterministic_extract(text)
        assert result is None


    def test_format_c_table_returns_none(self, format_c_table_path):
        """Format C (tabular, no colons): regex fails, Brain (LLM) needed."""
        text = read_pdf(format_c_table_path)
        result = deterministic_extract(text)
        assert result is None

    def test_format_d_alt_fields_returns_none(self, format_d_alt_fields_path):
        """Format D (different labels): regex fails, Brain (LLM) needed."""
        text = read_pdf(format_d_alt_fields_path)
        result = deterministic_extract(text)
        assert result is None

    def test_format_e_multi_amounts_returns_none(self, format_e_multi_amounts_path):
        """Format E (multiple amounts in prose): regex fails, Brain (LLM) needed."""
        text = read_pdf(format_e_multi_amounts_path)
        result = deterministic_extract(text)
        assert result is None


class TestExtractAffidavit:
    def test_regex_path_on_clean_format(self, sample_pdf_path, monkeypatch):
        calls = []
        import workshop.pipeline.extract as ext_mod
        real_llm = ext_mod.extract_with_llm
        def spy_llm(**kwargs):
            calls.append(kwargs)
            return real_llm(**kwargs)
        monkeypatch.setattr(ext_mod, "extract_with_llm", spy_llm)

        result = extract_affidavit(sample_pdf_path, variant="correct")
        assert result is not None
        assert result.consumer_name == "Jane M. Doe"
        assert result.chargeoff_balance == "$6,218.55"
        assert len(calls) == 0, "LLM fallback should not be called when regex succeeds"

    @pytest.mark.stretch
    def test_llm_fallback_on_variant(self, format_b_buyer_a_path):
        result = extract_affidavit(format_b_buyer_a_path, variant="correct")
        assert result is not None
        assert result.consumer_name == "John R. Smith"
        assert result.chargeoff_balance == "$12,450.00"

    @pytest.mark.stretch
    def test_llm_fallback_on_buyer_b(self, format_b_buyer_b_path):
        result = extract_affidavit(format_b_buyer_b_path, variant="correct")
        assert result is not None
        assert result.consumer_name == "Maria L. Garcia"
        assert result.last4 == "5555"

    @pytest.mark.stretch
    def test_llm_fallback_on_format_c(self, format_c_table_path):
        """Format C (table): regex fails, Brain (LLM) extracts via canned response."""
        result = extract_affidavit(format_c_table_path, variant="correct")
        assert result is not None
        assert result.consumer_name == "Alice B. Cooper"
        assert result.chargeoff_balance == "$5,400.00"

    @pytest.mark.stretch
    def test_llm_fallback_on_format_d(self, format_d_alt_fields_path):
        """Format D (alt labels): regex fails, Brain (LLM) extracts via canned response."""
        result = extract_affidavit(format_d_alt_fields_path, variant="correct")
        assert result is not None
        assert result.consumer_name == "David E. Torres"
        assert result.chargeoff_balance == "$4,125.60"

    @pytest.mark.stretch
    def test_llm_fallback_on_format_e(self, format_e_multi_amounts_path):
        """Format E (multi amounts): regex fails, Brain (LLM) extracts via canned response."""
        result = extract_affidavit(format_e_multi_amounts_path, variant="correct")
        assert result is not None
        assert result.consumer_name == "Patricia N. Wells"
        assert result.chargeoff_balance == "$7,892.15"
