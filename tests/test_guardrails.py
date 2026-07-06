"""Tests for Pillar 2: Guardrails (the Conscience)."""
import pytest
from workshop.pipeline.models import (
    AffidavitExtraction,
    ClaimStatus,
    Finding,
    VerdictType,
)
from workshop.pipeline.guardrails import (
    normalize_amount,
    normalize_date,
    normalize_name,
    audit_bill_of_sale,
    compare_field,
    check_statement_contradiction,
    check_all_fields,
    assign_verdict,
)


class TestNormalizeAmount:
    def test_dollar_string(self):
        assert normalize_amount("$6,218.55") == 6218.55

    def test_plain_number(self):
        assert normalize_amount("6218.55") == 6218.55

    def test_empty_string(self):
        assert normalize_amount("") is None

    def test_none(self):
        assert normalize_amount(None) is None

    def test_float_input(self):
        assert normalize_amount(6218.55) == 6218.55

    def test_integer_input(self):
        assert normalize_amount(1234) == 1234.0

    def test_no_cents(self):
        assert normalize_amount("$1,234") == 1234.0

    def test_leading_trailing_whitespace(self):
        assert normalize_amount("  $6,218.55  ") == 6218.55

    @pytest.mark.stretch
    def test_parenthetical_negative(self):
        assert normalize_amount("($150.00)") == -150.00

    @pytest.mark.stretch
    def test_negative_with_minus(self):
        assert normalize_amount("-$150.00") == -150.00

    def test_double_dollar_sign(self):
        assert normalize_amount("$$1,234.56") == 1234.56


class TestNormalizeDate:
    def test_us_format(self):
        assert normalize_date("03/15/2024") == "2024-03-15"

    def test_iso_passthrough(self):
        assert normalize_date("2024-03-15") == "2024-03-15"

    def test_none(self):
        assert normalize_date(None) is None

    def test_empty_string(self):
        assert normalize_date("") is None

    def test_no_leading_zeros(self):
        assert normalize_date("3/15/2024") == "2024-03-15"

    def test_single_digit_day(self):
        assert normalize_date("1/5/2024") == "2024-01-05"

    @pytest.mark.stretch
    def test_verbose_format(self):
        assert normalize_date("March 15, 2024") == "2024-03-15"

    @pytest.mark.stretch
    def test_verbose_format_day_first(self):
        """Day-first verbose: '15 March 2024' -> '2024-03-15'."""
        assert normalize_date("15 March 2024") == "2024-03-15"

    def test_leading_trailing_whitespace(self):
        assert normalize_date("  03/15/2024  ") == "2024-03-15"

    def test_leap_year_feb_29(self):
        assert normalize_date("02/29/2024") == "2024-02-29"


class TestAuditBillOfSale:
    def test_present(self):
        text = "Some text\nBILL OF SALE\nMore text"
        ext = AffidavitExtraction(bill_of_sale_attached=True)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MATCH

    def test_missing_heading(self):
        text = "Some legal text without the heading"
        ext = AffidavitExtraction(bill_of_sale_attached=True)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MISMATCH
        assert "CRITICAL EXHIBIT MISSING" in finding.reason

    def test_not_claimed(self):
        text = "Some text"
        ext = AffidavitExtraction(bill_of_sale_attached=False)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.EXEMPT

    def test_none_claimed(self):
        text = "Some text"
        ext = AffidavitExtraction(bill_of_sale_attached=None)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MISSING

    def test_charged_off_account_assignment(self):
        text = "Some text\nCHARGED-OFF ACCOUNT ASSIGNMENT\nMore text"
        ext = AffidavitExtraction(bill_of_sale_attached=True)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MATCH

    def test_charged_off_accounts_plural(self):
        text = "Some text\nCHARGED-OFF ACCOUNTS ASSIGNMENT\nMore text"
        ext = AffidavitExtraction(bill_of_sale_attached=True)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MATCH

    def test_case_insensitive(self):
        text = "Some text\nBill of Sale\nThis Bill of Sale is entered into as of the Closing Date"
        ext = AffidavitExtraction(bill_of_sale_attached=True)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MATCH


    @pytest.mark.stretch
    def test_footer_disclaimer_not_real_bos(self):
        """Bill of Sale mentioned in a footer disclaimer should NOT count as a real exhibit."""
        text = (
            "AFFIDAVIT OF ACCOUNT\n"
            "Some legal text here.\n\n"
            "DISCLAIMER: This affidavit is provided in connection with the "
            "Bill of Sale and Assignment Agreement executed between the parties. "
            "This document does not itself constitute a Bill of Sale."
        )
        ext = AffidavitExtraction(bill_of_sale_attached=True)
        finding = audit_bill_of_sale(text, ext)
        assert finding.claim_status == ClaimStatus.MISMATCH


class TestCompareField:
    def test_matching_amounts(self):
        finding = compare_field("chargeoff_balance", 6218.55, "$6,218.55", is_amount=True)
        assert finding.claim_status == ClaimStatus.MATCH

    def test_mismatching_amounts(self):
        finding = compare_field("chargeoff_balance", 6218.55, "$8,218.55", is_amount=True)
        assert finding.claim_status == ClaimStatus.MISMATCH

    def test_matching_dates(self):
        finding = compare_field("chargeoff_date", "2024-03-15", "03/15/2024", is_date=True)
        assert finding.claim_status == ClaimStatus.MATCH

    def test_missing_extracted(self):
        finding = compare_field("consumer_name", "Jane M. Doe", None)
        assert finding.claim_status == ClaimStatus.MISSING

    def test_case_insensitive_strings(self):
        finding = compare_field("consumer_name", "Jane M. Doe", "jane m. doe")
        assert finding.claim_status == ClaimStatus.MATCH

    def test_mismatching_dates(self):
        finding = compare_field("chargeoff_date", "2024-03-15", "04/20/2024", is_date=True)
        assert finding.claim_status == ClaimStatus.MISMATCH

    def test_empty_string_is_missing(self):
        finding = compare_field("consumer_name", "Jane M. Doe", "")
        assert finding.claim_status == ClaimStatus.MISSING

    def test_string_mismatch(self):
        finding = compare_field("debt_buyer", "Buyer A, LLC", "Buyer B, LLC")
        assert finding.claim_status == ClaimStatus.MISMATCH

    @pytest.mark.stretch
    def test_name_reordered_matches(self):
        """A live LLM's "LAST; FIRST" name should still match "First Last"."""
        finding = compare_field(
            "consumer_name", "Maria L. Garcia", "GARCIA; MARIA L.", is_name=True
        )
        assert finding.claim_status == ClaimStatus.MATCH

    @pytest.mark.stretch
    def test_name_genuinely_different_still_mismatches(self):
        """Order-insensitive matching must not collapse two different people."""
        finding = compare_field(
            "consumer_name", "Maria L. Garcia", "John R. Smith", is_name=True
        )
        assert finding.claim_status == ClaimStatus.MISMATCH


class TestNormalizeName:
    @pytest.mark.stretch
    def test_last_first_matches_first_last(self):
        assert normalize_name("GARCIA; MARIA L.") == normalize_name("Maria L. Garcia")
        assert normalize_name("SMITH; JOHN R.") == normalize_name("John R. Smith")

    @pytest.mark.stretch
    def test_different_names_differ(self):
        assert normalize_name("Maria L. Garcia") != normalize_name("John R. Smith")

    @pytest.mark.stretch
    def test_none_and_empty(self):
        assert normalize_name(None) is None
        assert normalize_name("") is None


class TestAssignVerdict:
    def test_all_match(self):
        findings = [
            Finding(
                field="f1", expected_value="a", document_value="a",
                normalized_expected="a", normalized_document="a",
                claim_status=ClaimStatus.MATCH, reason="ok",
            ),
            Finding(
                field="f2", expected_value="b", document_value="b",
                normalized_expected="b", normalized_document="b",
                claim_status=ClaimStatus.MATCH, reason="ok",
            ),
        ]
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS
        assert len(verdict.review_reasons) == 0

    def test_one_mismatch(self):
        findings = [
            Finding(
                field="f1", expected_value="a", document_value="a",
                normalized_expected="a", normalized_document="a",
                claim_status=ClaimStatus.MATCH, reason="ok",
            ),
            Finding(
                field="f2", expected_value="100", document_value="200",
                normalized_expected="100", normalized_document="200",
                claim_status=ClaimStatus.MISMATCH, reason="f2: VALUE MISMATCH",
            ),
        ]
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.REVIEW
        assert len(verdict.review_reasons) == 1

    def test_exempt_does_not_trigger_review(self):
        findings = [
            Finding(
                field="f1", expected_value="a", document_value="a",
                normalized_expected="a", normalized_document="a",
                claim_status=ClaimStatus.MATCH, reason="ok",
            ),
            Finding(
                field="f2", expected_value="N/A", document_value="False",
                normalized_expected="N/A", normalized_document="False",
                claim_status=ClaimStatus.EXEMPT, reason="exempt",
            ),
        ]
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS

    def test_missing_triggers_review(self):
        findings = [
            Finding(
                field="f1", expected_value="a", document_value="a",
                normalized_expected="a", normalized_document="a",
                claim_status=ClaimStatus.MATCH, reason="ok",
            ),
            Finding(
                field="f2", expected_value="Jane Doe", document_value=None,
                normalized_expected="Jane Doe", normalized_document=None,
                claim_status=ClaimStatus.MISSING, reason="f2: not found in extraction",
            ),
        ]
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.REVIEW
        assert len(verdict.review_reasons) == 1


class TestCheckStatementContradiction:
    @pytest.mark.stretch
    def test_payment_after_chargeoff(self, source_record, hallucinated_dates_extraction):
        finding = check_statement_contradiction(hallucinated_dates_extraction, source_record)
        assert finding is not None
        assert finding.claim_status == ClaimStatus.MISMATCH
        assert "contradiction" in finding.reason.lower()

    @pytest.mark.stretch
    def test_payment_before_chargeoff(self, source_record, correct_extraction):
        finding = check_statement_contradiction(correct_extraction, source_record)
        assert finding is None

    @pytest.mark.stretch
    def test_negative_chargeoff_balance(self, source_record):
        ext = AffidavitExtraction(
            chargeoff_balance="-$500.00",
            chargeoff_date="03/15/2024",
            last_payment_date="01/10/2024",
        )
        finding = check_statement_contradiction(ext, source_record)
        assert finding is not None
        assert finding.claim_status == ClaimStatus.MISMATCH


class TestFullPipeline:
    def test_correct_extraction_pass(self, correct_extraction, source_record, sample_pdf_path):
        from workshop.pipeline.extract import read_pdf
        pdf_text = read_pdf(sample_pdf_path)
        findings = check_all_fields(correct_extraction, source_record, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS

    def test_hallucinated_extraction_review(self, hallucinated_extraction, source_record, sample_pdf_path):
        from workshop.pipeline.extract import read_pdf
        pdf_text = read_pdf(sample_pdf_path)
        findings = check_all_fields(hallucinated_extraction, source_record, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.REVIEW
        mismatch_fields = [f.field for f in findings if f.claim_status == ClaimStatus.MISMATCH]
        assert "chargeoff_balance" in mismatch_fields

    @pytest.mark.stretch
    def test_hallucinated_dates_review(self, hallucinated_dates_extraction, source_record, sample_pdf_path):
        from workshop.pipeline.extract import read_pdf
        pdf_text = read_pdf(sample_pdf_path)
        findings = check_all_fields(hallucinated_dates_extraction, source_record, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.REVIEW
        fields = [f.field for f in findings if f.claim_status == ClaimStatus.MISMATCH]
        assert "last_payment_date" in fields
        assert "statement_contradiction" in fields

    @pytest.mark.stretch
    def test_format_b_buyer_a_pass(self, source_record_002, format_b_buyer_a_path):
        from workshop.pipeline.extract import read_pdf, extract_affidavit
        pdf_text = read_pdf(format_b_buyer_a_path)
        extraction = extract_affidavit(format_b_buyer_a_path)
        findings = check_all_fields(extraction, source_record_002, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS

    @pytest.mark.stretch
    def test_format_b_buyer_b_pass(self, source_record_003, format_b_buyer_b_path):
        from workshop.pipeline.extract import read_pdf, extract_affidavit
        pdf_text = read_pdf(format_b_buyer_b_path)
        extraction = extract_affidavit(format_b_buyer_b_path)
        findings = check_all_fields(extraction, source_record_003, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS

    @pytest.mark.stretch
    def test_format_c_table_pass(self, source_record_005, format_c_table_path):
        """Full pipeline: Format C (table) -> Brain fallback -> Conscience -> PASS."""
        from workshop.pipeline.extract import read_pdf, extract_affidavit
        pdf_text = read_pdf(format_c_table_path)
        extraction = extract_affidavit(format_c_table_path)
        findings = check_all_fields(extraction, source_record_005, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS

    @pytest.mark.stretch
    def test_format_d_alt_fields_pass(self, source_record_006, format_d_alt_fields_path):
        """Full pipeline: Format D (alt labels) -> Brain fallback -> Conscience -> PASS."""
        from workshop.pipeline.extract import read_pdf, extract_affidavit
        pdf_text = read_pdf(format_d_alt_fields_path)
        extraction = extract_affidavit(format_d_alt_fields_path)
        findings = check_all_fields(extraction, source_record_006, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS

    @pytest.mark.stretch
    def test_format_e_multi_amounts_pass(self, source_record_007, format_e_multi_amounts_path):
        """Full pipeline: Format E (multi amounts) -> Brain fallback -> Conscience -> PASS."""
        from workshop.pipeline.extract import read_pdf, extract_affidavit
        pdf_text = read_pdf(format_e_multi_amounts_path)
        extraction = extract_affidavit(format_e_multi_amounts_path)
        findings = check_all_fields(extraction, source_record_007, pdf_text)
        verdict = assign_verdict(findings)
        assert verdict.verdict == VerdictType.PASS
