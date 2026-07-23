"""The Brain: LLM client for structured extraction.

Mental model mapping:
  Brain = this module. Interprets text (or images) and returns structured fields.
  Fallback when the regex shortcut fails. Powerful but fallible. Can hallucinate.

Default mode reads pre-recorded JSON from data/canned_llm/. This works
offline with zero dependencies beyond pydantic.

Live mode calls Anthropic, OpenAI, or OpenRouter to extract data from the PDF text.
Install the SDK you want: `pip install anthropic` or `pip install openai` (OpenRouter
speaks the OpenAI-compatible chat completions API, so it reuses the `openai` package).
Set the corresponding env var: ANTHROPIC_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY.

Live mode is auto-detected: if any of those keys is present in the environment,
the pipeline uses the real LLM without any code change or flag. If none is set,
it falls back to the canned responses. See live_mode_enabled().
"""
import json
import logging
import os
from pathlib import Path

from workshop.pipeline.models import AffidavitExtraction

logger = logging.getLogger(__name__)

CANNED_DIR = Path("data/canned_llm")


def active_provider() -> str | None:
    """Return the live LLM provider to use, based on which API key is set.

    Precedence: Anthropic -> OpenRouter -> OpenAI. Returns None if no key is set
    (canned mode). This is the single source of truth for "is live mode on".
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def live_mode_enabled() -> bool:
    """True if an API key is set, so the pipeline should call a real LLM."""
    return active_provider() is not None

EXTRACTION_PROMPT = """Extract the following fields from this legal affidavit PDF text.
Return ONLY a JSON object with exactly these keys:
- consumer_name (string or null)
- last4 (string: last 4 digits of the account number, or null)
- original_creditor (string or null)
- debt_buyer (string or null)
- chargeoff_balance (string with dollar sign like "$6,218.55", or null)
- chargeoff_date (string in MM/DD/YYYY format, or null)
- last_payment_date (string in MM/DD/YYYY format, or null)
- last_payment_amount (string with dollar sign like "$150.00", or null)
- closing_date (string in MM/DD/YYYY format, or null)
- sale_balance (string with dollar sign, or null)
- transfer_date (string in MM/DD/YYYY format, or null)
- bill_of_sale_attached (boolean: true if a Bill of Sale or Account Assignment is present)

Do not add any fields beyond these. Do not wrap the JSON in markdown code fences."""


class CannedResponseMissing(Exception):
    pass


def _extract_with_anthropic(pdf_text: str) -> AffidavitExtraction:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError(
            "Anthropic SDK not installed. Run: pip install anthropic"
        )

    model = "claude-haiku-4-5-20251001"
    logger.info("Brain: live extraction via Anthropic (%s)", model)
    client = Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\n---\n\nPDF TEXT:\n{pdf_text}",
            }
        ],
    )
    raw = message.content[0].text
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    return AffidavitExtraction(**data)


def _extract_with_openai(pdf_text: str) -> AffidavitExtraction:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI SDK not installed. Run: pip install openai"
        )

    model = "gpt-4o-mini"
    logger.info("Brain: live extraction via OpenAI (%s)", model)
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": pdf_text},
        ],
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    return AffidavitExtraction(**data)


def _extract_with_openrouter(pdf_text: str) -> AffidavitExtraction:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "OpenAI SDK not installed. Run: pip install openai"
        )

    model = "anthropic/claude-haiku-4.5"
    logger.info("Brain: live extraction via OpenRouter (%s)", model)
    client = OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": pdf_text},
        ],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    return AffidavitExtraction(**data)


def extract_with_llm(
    pdf_path: str,
    variant: str = "correct",
    pdf_text: str = "",
    use_live_api: bool = False,
) -> AffidavitExtraction:
    """Extract affidavit fields using canned responses or a live LLM API.

    Canned mode (default): reads data/canned_llm/{pdf_stem}/{variant}.json.
    Live mode: calls Anthropic, OpenAI, or OpenRouter based on which API key is set.
    """
    if use_live_api:
        if not pdf_text:
            raise ValueError("pdf_text is required for live API mode")
        provider = active_provider()
        if provider == "anthropic":
            return _extract_with_anthropic(pdf_text)
        if provider == "openrouter":
            return _extract_with_openrouter(pdf_text)
        if provider == "openai":
            return _extract_with_openai(pdf_text)
        raise RuntimeError(
            "Live API mode requested but no API key found. "
            "Set ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY in your environment. "
            "Or run without a key to use pre-recorded responses."
        )

    pdf_stem = Path(pdf_path).stem
    canned_file = CANNED_DIR / pdf_stem / f"{variant}.json"

    if not canned_file.exists():
        raise CannedResponseMissing(
            f"No canned response at {canned_file}"
        )

    logger.info("Brain: canned response (%s, variant=%s)", pdf_stem, variant)
    data = json.loads(canned_file.read_text())
    return AffidavitExtraction(**data)
