"""Generate synthetic affidavit PDFs for the workshop. Uses fpdf2.

Formats A and A-alt have labeled fields that the regex shortcut handles.
Formats B, C, D, E break regex in different ways and require the Brain (LLM) fallback.
Values match data/seeds/source_of_truth.csv (ACCT-001 through ACCT-007).
"""
from pathlib import Path

from fpdf import FPDF

AFFIDAVIT_DATA = {
    "consumer_name": "Jane M. Doe",
    "last4": "7890",
    "original_creditor": "First National Bank",
    "debt_buyer": "Buyer A, LLC",
    "chargeoff_balance": "$6,218.55",
    "chargeoff_date": "03/15/2024",
    "last_payment_date": "01/10/2024",
    "last_payment_amount": "$150.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$6,418.22",
    "transfer_date": "07/15/2024",
}


def make_format_a(output_path: str = "data/pdfs/sample_affidavit.pdf") -> None:
    """Format A (clean): modeled on UCS-CCR4 structure.
    4 pages: affidavit form (pgs 1-3) + Bill of Sale exhibit (pg 4)."""
    d = AFFIDAVIT_DATA
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    # --- Page 1: Header + perjury statement + paragraphs 1-5 ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIRMATION OF FACTS AND SALE OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Form UCS-CCR4 (Synthetic)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 5, "I state under the penalties of perjury that the following statements "
                   "are true and correct to the best of my knowledge:")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    paras = [
        f"1. I am a servicer for {d['original_creditor']} (\"Original Creditor\"). "
        f"The above-referenced account was sold or assigned by Original Creditor to "
        f"{d['debt_buyer']} (\"Debt Buyer\"), on {d['transfer_date']}.",

        "2. The statements herein are based on my review of the business records of "
        "Original Creditor maintained in the regular course of business.",

        "3. A copy of the bill of sale or written assignment from the Original Creditor "
        "to the Debt Buyer is attached as an exhibit to this affirmation.",

        f"4. The account was opened by the consumer identified below and the consumer "
        f"made charges or received advances on the account.",

        f"5. The consumer defaulted on the account. The last payment received by "
        f"Original Creditor was on {d['last_payment_date']} in the amount of "
        f"{d['last_payment_amount']}. The account was charged off on {d['chargeoff_date']}.",
    ]
    for p in paras:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    # --- Page 2: Para 7 + labeled data block + signature ---
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        "6. The account was a revolving credit account.")
    pdf.ln(2)
    pdf.multi_cell(0, 5,
        "7. [X] The following account information is true and correct based on "
        "Original Creditor's business records:")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Account Details", new_x="LMARGIN", new_y="NEXT")
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    fields = [
        ("Consumer Name", d["consumer_name"]),
        ("Account Last 4", d["last4"]),
        ("Original Creditor", d["original_creditor"]),
        ("Debt Buyer", d["debt_buyer"]),
        ("Chargeoff Balance", d["chargeoff_balance"]),
        ("Chargeoff Date", d["chargeoff_date"]),
        ("Last Payment Date", d["last_payment_date"]),
        ("Last Payment Amount", d["last_payment_amount"]),
        ("Closing Date", d["closing_date"]),
        ("Sale Balance", d["sale_balance"]),
        ("Transfer Date", d["transfer_date"]),
    ]
    for label, value in fields:
        pdf.cell(55, 6, f"{label}:", new_x="RIGHT")
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Signature of Affiant", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Date: ________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.cell(0, 5, "Account Reference: ACCT-001", new_x="LMARGIN", new_y="NEXT")

    # --- Page 3: Exhibits checklist ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Exhibits to be Attached to Affirmation", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    exhibits = [
        "1. [X] Bill of Sale from Original Creditor to Debt Buyer",
        "2. [ ] Agreement, Contract, or Invoice, or Charge-off Statement",
        "3. [ ] Most Recent Charge, Payment, or Balance Transfer Statement",
        f"4. [X] Additional Books and Records (debtor: {d['consumer_name']}, "
        f"last 4: {d['last4']}, last payment: {d['last_payment_date']}, "
        f"chargeoff: {d['chargeoff_date']}, balance: {d['chargeoff_balance']})",
    ]
    for ex in exhibits:
        pdf.multi_cell(0, 5, ex)
        pdf.ln(3)

    # --- Page 4: Bill of Sale exhibit ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BILL OF SALE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    bos_text = (
        f"This Bill of Sale is entered into as of the Closing Date ({d['closing_date']}), "
        f"by and between {d['original_creditor']} (\"Seller\") and "
        f"{d['debt_buyer']} (\"Purchaser\").\n\n"
        f"Seller hereby sells, assigns, transfers, and conveys to Purchaser all of Seller's "
        f"right, title, and interest in and to the accounts identified in the attached schedule, "
        f"including but not limited to the account referenced as ACCT-001.\n\n"
        f"The total purchase price for the accounts sold hereunder is based on the aggregate "
        f"sale balance of the accounts as of the Closing Date.\n\n"
        f"IN WITNESS WHEREOF, the parties have executed this Bill of Sale as of the date "
        f"first written above."
    )
    pdf.multi_cell(0, 5, bos_text)

    pdf.ln(10)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Seller: {d['original_creditor']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.cell(0, 5, f"Purchaser: {d['debt_buyer']}", new_x="LMARGIN", new_y="NEXT")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


ACCT_002_DATA = {
    "consumer_name": "John R. Smith",
    "last4": "4321",
    "original_creditor": "Metro Credit Union",
    "debt_buyer": "Buyer A, LLC",
    "chargeoff_balance": "$12,450.00",
    "chargeoff_date": "02/28/2024",
    "last_payment_date": "01/05/2024",
    "last_payment_amount": "$200.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$12,890.33",
    "transfer_date": "07/15/2024",
}

ACCT_003_DATA = {
    "consumer_name": "Maria L. Garcia",
    "last4": "5555",
    "original_creditor": "Coastal Savings Bank",
    "debt_buyer": "Buyer B, LLC",
    "chargeoff_balance": "$3,200.75",
    "chargeoff_date": "04/10/2024",
    "last_payment_date": "02/20/2024",
    "last_payment_amount": "$75.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$3,350.00",
    "transfer_date": "07/15/2024",
}


def make_format_a_buyer(output_path: str, data: dict[str, str]) -> None:
    """Format A (clean labeled fields) for any account data dict."""
    d = data
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIRMATION OF FACTS AND SALE OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Form UCS-CCR4 (Synthetic)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 5, "I state under the penalties of perjury that the following statements "
                   "are true and correct to the best of my knowledge:")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    paras = [
        f"1. I am a servicer for {d['original_creditor']} (\"Original Creditor\"). "
        f"The above-referenced account was sold or assigned by Original Creditor to "
        f"{d['debt_buyer']} (\"Debt Buyer\"), on {d['transfer_date']}.",
        "2. The statements herein are based on my review of the business records of "
        "Original Creditor maintained in the regular course of business.",
        "3. A copy of the bill of sale or written assignment from the Original Creditor "
        "to the Debt Buyer is attached as an exhibit to this affirmation.",
        "4. The account was opened by the consumer identified below and the consumer "
        "made charges or received advances on the account.",
        f"5. The consumer defaulted on the account. The last payment received by "
        f"Original Creditor was on {d['last_payment_date']} in the amount of "
        f"{d['last_payment_amount']}. The account was charged off on {d['chargeoff_date']}.",
    ]
    for p in paras:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, "6. The account was a revolving credit account.")
    pdf.ln(2)
    pdf.multi_cell(0, 5,
        "7. [X] The following account information is true and correct based on "
        "Original Creditor's business records:")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Account Details", new_x="LMARGIN", new_y="NEXT")
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    fields = [
        ("Consumer Name", d["consumer_name"]),
        ("Account Last 4", d["last4"]),
        ("Original Creditor", d["original_creditor"]),
        ("Debt Buyer", d["debt_buyer"]),
        ("Chargeoff Balance", d["chargeoff_balance"]),
        ("Chargeoff Date", d["chargeoff_date"]),
        ("Last Payment Date", d["last_payment_date"]),
        ("Last Payment Amount", d["last_payment_amount"]),
        ("Closing Date", d["closing_date"]),
        ("Sale Balance", d["sale_balance"]),
        ("Transfer Date", d["transfer_date"]),
    ]
    for label, value in fields:
        pdf.cell(55, 6, f"{label}:", new_x="RIGHT")
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Signature of Affiant", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Date: ________________", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BILL OF SALE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    bos_text = (
        f"This Bill of Sale is entered into as of the Closing Date ({d['closing_date']}), "
        f"by and between {d['original_creditor']} (\"Seller\") and "
        f"{d['debt_buyer']} (\"Purchaser\").\n\n"
        f"Seller hereby sells, assigns, transfers, and conveys to Purchaser all of Seller's "
        f"right, title, and interest in and to the accounts identified in the attached schedule."
    )
    pdf.multi_cell(0, 5, bos_text)
    pdf.ln(10)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Seller: {d['original_creditor']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.cell(0, 5, f"Purchaser: {d['debt_buyer']}", new_x="LMARGIN", new_y="NEXT")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


def _strip_leading_zeros(date_str: str) -> str:
    """'01/05/2024' -> '1/5/2024' (M/D/YYYY without leading zeros)."""
    parts = date_str.split("/")
    return f"{int(parts[0])}/{int(parts[1])}/{parts[2]}"


def _to_last_first(name: str) -> str:
    """'Jane M. Doe' -> 'DOE; JANE M.' or 'John R. Smith' -> 'SMITH; JOHN R.'"""
    parts = name.split()
    last = parts[-1].upper()
    first_middle = " ".join(parts[:-1]).upper()
    return f"{last}; {first_middle}"


def _mask_account(last4: str) -> str:
    """'4321' -> 'XXXXXXXXXXXX4321' (12 X's + last4)."""
    return "X" * 12 + last4


def make_format_b(
    output_path: str = "data/pdfs/buyer_a/2026-07-01/acct_5678_variant.pdf",
    data: dict[str, str] | None = None,
) -> None:
    """Format B (narrative prose): data inline in paragraphs, no labeled fields.
    Modeled on real 'Affidavit of Account' documents (reviewed 2026-07-18)."""
    d = data or ACCT_002_DATA
    consumer_lf = _to_last_first(d["consumer_name"])
    masked_acct = _mask_account(d["last4"])
    lp_date = _strip_leading_zeros(d["last_payment_date"])
    co_date = _strip_leading_zeros(d["chargeoff_date"])
    xfer_date = _strip_leading_zeros(d["transfer_date"])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIDAVIT OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"I, __________, the __________ of {d['original_creditor']} "
        f"(\"Creditor\"), am duly authorized to make this affidavit on behalf of "
        f"Creditor and do hereby state under oath as follows:")
    pdf.ln(4)

    paras = [
        "1. I am familiar with the manner and method by which Creditor creates and "
        "maintains its business records in the ordinary course of its regularly "
        "conducted business activities.",

        f"2. Creditor is the original creditor of an Account owed by "
        f"{consumer_lf}, which Account number was {masked_acct}. The Account was "
        f"issued by {d['original_creditor']} and is a revolving credit account.",

        "3. The information set forth herein is based upon my review of Creditor's "
        "business records maintained in the ordinary course of Creditor's regularly "
        "conducted business activities, which records were made at or near the time "
        "of the events recorded by persons with knowledge of such events.",

        f"4. The Account was charged off on {co_date} in the amount of "
        f"{d['chargeoff_balance']}. The charge-off balance represents the total "
        f"amount owed on the Account as of the date of charge-off, including all "
        f"principal, interest, and fees assessed through that date.",

        f"5. Creditor records reflect a last payment to the Account in the amount "
        f"of {d['last_payment_amount']} posted on {lp_date}. No further payments "
        f"have been received or credited to the Account since that date.",

        f"6. Creditor, on {xfer_date}, sold, transferred and conveyed to "
        f"{d['debt_buyer']} all of its rights, title, interest, and obligations "
        f"in and to the Account referenced herein.",

        "7. Since the transfer referenced herein, no credits or uncredited payments "
        "have been received or applied to the Account by Creditor. Creditor has no "
        "further interest in the Account.",
    ]
    for p in paras:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        "I declare under penalty of perjury under the laws of the Commonwealth of "
        "Virginia that the foregoing is true and correct.")
    pdf.ln(6)

    pdf.cell(0, 5, "Dated: ________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Signature", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Name: __________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Title: __________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4,
        "COMMONWEALTH OF VIRGINIA\n"
        "CITY OF RICHMOND\n\n"
        "Subscribed and sworn to before me this ____ day of __________, 20____.\n\n"
        "____________________________\n"
        "Notary Public\n"
        "My commission expires: __________")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "CHARGED-OFF ACCOUNT ASSIGNMENT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"This Assignment is entered into as of {d['closing_date']}, by and between "
        f"{d['original_creditor']} (\"Assignor\") and {d['debt_buyer']} (\"Assignee\").\n\n"
        f"Assignor hereby assigns, transfers, and conveys to Assignee all of Assignor's "
        f"right, title, and interest in and to the charged-off accounts identified in the "
        f"attached Account Schedule, for a total sale balance of {d['sale_balance']}.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


def make_format_b_buyer_b(
    output_path: str = "data/pdfs/buyer_b/2026-07-01/acct_9012_narrative.pdf",
) -> None:
    """Format B for buyer_b with ACCT-003 data (Maria L. Garcia, Buyer B, LLC)."""
    make_format_b(output_path=output_path, data=ACCT_003_DATA)


ACCT_004_DATA = {
    "consumer_name": "Robert A. Johnson",
    "last4": "2468",
    "original_creditor": "Pacific Trust Bank",
    "debt_buyer": "Buyer A, LLC",
    "chargeoff_balance": "$8,750.30",
    "chargeoff_date": "05/01/2024",
    "last_payment_date": "03/22/2024",
    "last_payment_amount": "$125.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$9,100.50",
    "transfer_date": "07/15/2024",
}


def make_format_b_footer_bos(
    output_path: str = "data/pdfs/buyer_a/2026-07-01/acct_2468_footer_bos.pdf",
    data: dict[str, str] | None = None,
) -> None:
    """Format B variant where 'Bill of Sale' appears ONLY in a footer disclaimer,
    not as an actual exhibit heading. Tests audit_bill_of_sale edge case:
    the heading is present in the text but not as an actual exhibit."""
    d = data or ACCT_004_DATA
    consumer_lf = _to_last_first(d["consumer_name"])
    masked_acct = _mask_account(d["last4"])
    lp_date = _strip_leading_zeros(d["last_payment_date"])
    co_date = _strip_leading_zeros(d["chargeoff_date"])
    xfer_date = _strip_leading_zeros(d["transfer_date"])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIDAVIT OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"I, __________, the __________ of {d['original_creditor']} "
        f"(\"Creditor\"), am duly authorized to make this affidavit on behalf of "
        f"Creditor and do hereby state under oath as follows:")
    pdf.ln(4)

    paras = [
        "1. I am familiar with the manner and method by which Creditor creates and "
        "maintains its business records in the ordinary course of its regularly "
        "conducted business activities.",

        f"2. Creditor is the original creditor of an Account owed by "
        f"{consumer_lf}, which Account number was {masked_acct}. The Account was "
        f"issued by {d['original_creditor']} and is a revolving credit account.",

        f"3. The Account was charged off on {co_date} in the amount of "
        f"{d['chargeoff_balance']}.",

        f"4. Creditor records reflect a last payment to the Account in the amount "
        f"of {d['last_payment_amount']} posted on {lp_date}.",

        f"5. Creditor, on {xfer_date}, sold, transferred and conveyed to "
        f"{d['debt_buyer']} all of its rights, title, and interest in the Account.",
    ]
    for p in paras:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        "I declare under penalty of perjury that the foregoing is true and correct.")
    pdf.ln(6)
    pdf.cell(0, 5, "Dated: ________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Signature", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(20)
    pdf.set_font("Helvetica", "", 7)
    pdf.multi_cell(0, 3,
        "DISCLAIMER: This affidavit is provided in connection with the "
        "Bill of Sale and Assignment Agreement executed between the parties. "
        "The Bill of Sale referenced herein is maintained on file by the "
        "purchasing entity and is available upon request. This document does "
        "not itself constitute a Bill of Sale or transfer of ownership.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


def make_format_a_alt_labels(
    output_path: str = "data/pdfs/buyer_a/2026-07-01/acct_1357_alt_labels.pdf",
    data: dict[str, str] | None = None,
) -> None:
    """Format A variant with slightly different field labels (extra whitespace,
    different label text) to test regex robustness. Same data, different presentation."""
    d = data or ACCT_004_DATA
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIRMATION OF FACTS AND SALE OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Form UCS-CCR4 (Synthetic)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 5, "I state under the penalties of perjury that the following statements "
                   "are true and correct to the best of my knowledge:")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    paras = [
        f"1. I am a servicer for {d['original_creditor']} (\"Original Creditor\"). "
        f"The above-referenced account was sold or assigned by Original Creditor to "
        f"{d['debt_buyer']} (\"Debt Buyer\"), on {d['transfer_date']}.",
        f"2. The consumer defaulted on the account. The last payment received by "
        f"Original Creditor was on {d['last_payment_date']} in the amount of "
        f"{d['last_payment_amount']}. The account was charged off on {d['chargeoff_date']}.",
    ]
    for p in paras:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Account Information", new_x="LMARGIN", new_y="NEXT")
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    fields = [
        ("Consumer  Name", d["consumer_name"]),
        ("Account Last 4 Digits", d["last4"]),
        ("Original  Creditor", d["original_creditor"]),
        ("Debt  Buyer", d["debt_buyer"]),
        ("Chargeoff  Balance", d["chargeoff_balance"]),
        ("Chargeoff  Date", d["chargeoff_date"]),
        ("Last Payment  Date", d["last_payment_date"]),
        ("Last Payment  Amount", d["last_payment_amount"]),
        ("Closing  Date", d["closing_date"]),
        ("Sale  Balance", d["sale_balance"]),
        ("Transfer  Date", d["transfer_date"]),
    ]
    for label, value in fields:
        pdf.cell(60, 6, f"{label}:", new_x="RIGHT")
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Signature of Affiant", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BILL OF SALE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"This Bill of Sale is entered into as of the Closing Date ({d['closing_date']}), "
        f"by and between {d['original_creditor']} (\"Seller\") and "
        f"{d['debt_buyer']} (\"Purchaser\").")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


ACCT_005_DATA = {
    "consumer_name": "Alice B. Cooper",
    "last4": "8899",
    "original_creditor": "Summit Credit Union",
    "debt_buyer": "Buyer A, LLC",
    "chargeoff_balance": "$5,400.00",
    "chargeoff_date": "07/01/2024",
    "last_payment_date": "06/15/2024",
    "last_payment_amount": "$90.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$5,650.00",
    "transfer_date": "07/15/2024",
}

ACCT_006_DATA = {
    "consumer_name": "David E. Torres",
    "last4": "3377",
    "original_creditor": "Heritage National Bank",
    "debt_buyer": "Buyer B, LLC",
    "chargeoff_balance": "$4,125.60",
    "chargeoff_date": "04/20/2024",
    "last_payment_date": "03/01/2024",
    "last_payment_amount": "$100.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$4,300.00",
    "transfer_date": "07/15/2024",
}

ACCT_007_DATA = {
    "consumer_name": "Patricia N. Wells",
    "last4": "6644",
    "original_creditor": "Lakeside Federal Bank",
    "debt_buyer": "Buyer B, LLC",
    "chargeoff_balance": "$7,892.15",
    "chargeoff_date": "05/15/2024",
    "last_payment_date": "04/02/2024",
    "last_payment_amount": "$175.00",
    "closing_date": "06/30/2024",
    "sale_balance": "$8,200.00",
    "transfer_date": "07/15/2024",
}


def make_format_c_table(
    output_path: str = "data/pdfs/buyer_a/2026-07-01/acct_8899_table.pdf",
    data: dict[str, str] | None = None,
) -> None:
    """Format C: tabular layout with short headers (no colons).
    Regex fails because labels like 'Consumer', 'CO Balance' don't match
    FIELD_PATTERNS which expect 'Consumer Name:', 'Chargeoff Balance:', etc.
    The Brain (LLM) reads the table semantically."""
    d = data or ACCT_005_DATA
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIRMATION OF FACTS AND SALE OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Form UCS-CCR4 (Synthetic)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 5, "I state under the penalties of perjury that the following statements "
                   "are true and correct to the best of my knowledge:")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"1. The account referenced below was sold to {d['debt_buyer']} on {d['transfer_date']}.")
    pdf.ln(3)

    col_w = 34
    pdf.set_font("Helvetica", "B", 9)
    for h in ["Consumer", "Last 4", "Creditor", "Buyer", "CO Balance"]:
        pdf.cell(col_w, 6, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for v in [d["consumer_name"], d["last4"], d["original_creditor"][:14], d["debt_buyer"], d["chargeoff_balance"]]:
        pdf.cell(col_w, 6, v, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    for h in ["CO Date", "Last Pmt Date", "Last Pmt Amt", "Sale Balance", "Transfer"]:
        pdf.cell(col_w, 6, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for v in [d["chargeoff_date"], d["last_payment_date"], d["last_payment_amount"], d["sale_balance"], d["transfer_date"]]:
        pdf.cell(col_w, 6, v, border=1, align="C")
    pdf.ln()

    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, f"2. The closing date for the sale was {d['closing_date']}.")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BILL OF SALE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"This Bill of Sale is entered into as of the Closing Date ({d['closing_date']}), "
        f"by and between {d['original_creditor']} (\"Seller\") and "
        f"{d['debt_buyer']} (\"Purchaser\").")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


def make_format_d_alt_field_names(
    output_path: str = "data/pdfs/buyer_b/2026-07-01/acct_3377_alt_fields.pdf",
    data: dict[str, str] | None = None,
) -> None:
    """Format D: same structure as Format A but with different label text.
    Regex fails because 'Debtor Name' doesn't match 'Consumer Name:', etc.
    The Brain (LLM) understands semantically that 'Debtor Name' = 'Consumer Name'."""
    d = data or ACCT_006_DATA
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIRMATION OF FACTS AND SALE OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Form UCS-CCR5 (Synthetic)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 5, "I state under the penalties of perjury that the following statements "
                   "are true and correct to the best of my knowledge:")
    pdf.ln(4)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Account Details", new_x="LMARGIN", new_y="NEXT")
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    fields = [
        ("Debtor Name", d["consumer_name"]),
        ("Account Number (last 4)", d["last4"]),
        ("Issuing Bank", d["original_creditor"]),
        ("Purchasing Entity", d["debt_buyer"]),
        ("Balance at Chargeoff", d["chargeoff_balance"]),
        ("Date of Chargeoff", d["chargeoff_date"]),
        ("Date of Last Payment", d["last_payment_date"]),
        ("Most Recent Payment", d["last_payment_amount"]),
        ("Portfolio Closing Date", d["closing_date"]),
        ("Outstanding Sale Balance", d["sale_balance"]),
        ("Date of Transfer", d["transfer_date"]),
    ]
    for label, value in fields:
        pdf.cell(60, 6, f"{label}:", new_x="RIGHT")
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BILL OF SALE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"This Bill of Sale is entered into as of the Closing Date ({d['closing_date']}), "
        f"by and between {d['original_creditor']} (\"Seller\") and "
        f"{d['debt_buyer']} (\"Purchaser\").")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


def make_format_e_multi_amounts(
    output_path: str = "data/pdfs/buyer_b/2026-07-01/acct_6644_multi_amounts.pdf",
    data: dict[str, str] | None = None,
) -> None:
    """Format E: narrative prose with multiple dollar amounts on the page.
    Regex for dollar amounts matches 6+ values. Which is the chargeoff balance?
    The Brain (LLM) reads context and picks the right one."""
    d = data or ACCT_007_DATA
    co_balance_num = float(d["chargeoff_balance"].replace("$", "").replace(",", ""))
    interest = round(co_balance_num * 0.12, 2)
    fees = 350.00
    original_limit = 15000.00
    principal = round(co_balance_num - interest - fees, 2)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "AFFIDAVIT OF ACCOUNT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"I, __________, am duly authorized to make this affidavit on behalf of "
        f"{d['original_creditor']} (\"Creditor\").")
    pdf.ln(3)

    paras = [
        f"1. The account held by {d['consumer_name']} (account ending in "
        f"{d['last4']}) was a revolving credit account with an original credit "
        f"limit of ${original_limit:,.2f}.",

        f"2. As of the date of default, the outstanding principal balance was "
        f"${principal:,.2f}, with accrued interest of ${interest:,.2f} and "
        f"assessed late fees of ${fees:,.2f}, for a total chargeoff balance of "
        f"{d['chargeoff_balance']}. The account was charged off on "
        f"{_strip_leading_zeros(d['chargeoff_date'])}.",

        f"3. The last payment received was {d['last_payment_amount']} posted on "
        f"{_strip_leading_zeros(d['last_payment_date'])}.",

        f"4. Creditor sold and assigned all rights in the account to "
        f"{d['debt_buyer']} on {_strip_leading_zeros(d['transfer_date'])}, for "
        f"a total sale balance of {d['sale_balance']}. The closing date of the "
        f"portfolio sale was {d['closing_date']}.",
    ]
    for p in paras:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        "I declare under penalty of perjury that the foregoing is true and correct.")
    pdf.ln(6)
    pdf.cell(0, 5, "Dated: ________________", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "CHARGED-OFF ACCOUNT ASSIGNMENT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5,
        f"This Assignment is entered into as of {d['closing_date']}, by and between "
        f"{d['original_creditor']} (\"Assignor\") and {d['debt_buyer']} (\"Assignee\").")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)


if __name__ == "__main__":
    make_format_a()
    print("Generated Format A (clean): data/pdfs/sample_affidavit.pdf")
    make_format_a_buyer(
        "data/pdfs/buyer_a/2026-07-01/acct_1234_standard.pdf", ACCT_002_DATA
    )
    print("Generated Format A (buyer_a): data/pdfs/buyer_a/2026-07-01/acct_1234_standard.pdf")
    make_format_b()
    print("Generated Format B (buyer_a variant): data/pdfs/buyer_a/2026-07-01/acct_5678_variant.pdf")
    make_format_b_buyer_b()
    print("Generated Format B (buyer_b): data/pdfs/buyer_b/2026-07-01/acct_9012_narrative.pdf")
    make_format_b_footer_bos()
    print("Generated Format B (footer BOS): data/pdfs/buyer_a/2026-07-01/acct_2468_footer_bos.pdf")
    make_format_a_alt_labels()
    print("Generated Format A (alt labels): data/pdfs/buyer_a/2026-07-01/acct_1357_alt_labels.pdf")
    make_format_c_table()
    print("Generated Format C (table): data/pdfs/buyer_a/2026-07-01/acct_8899_table.pdf")
    make_format_d_alt_field_names()
    print("Generated Format D (alt field names): data/pdfs/buyer_b/2026-07-01/acct_3377_alt_fields.pdf")
    make_format_e_multi_amounts()
    print("Generated Format E (multi amounts): data/pdfs/buyer_b/2026-07-01/acct_6644_multi_amounts.pdf")
