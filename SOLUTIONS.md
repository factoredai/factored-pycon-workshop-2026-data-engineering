# Solutions Guide

This file explains each workshop blank: what to implement, why, and the key insight.
If you are reading this, you switched to the `solutions` branch (`git checkout solutions`).

To go back to the exercise branch: `git checkout main`

---

## Pillar 1: Extraction (`workshop/pipeline/extract.py`)

Mental model: Eyes (`read_pdf`) + Regex shortcut (`deterministic_extract`) + Brain fallback (`extract_with_llm`).

### Blank A: `detect_pdf_type`

**What:** Use `read_pdf()` (the Eyes) to get raw text. If the result has more than 100 characters,
the PDF is text-native (`"native"`). Otherwise it is a scanned image (`"scanned"`).

**Why:** Native PDFs can try the regex shortcut first (free, instant, deterministic). Scanned PDFs
go straight to the Brain (LLM with vision reads the image directly, no OCR step needed).

**Key insight:** This is a one-line decision after calling `read_pdf()`. The 100-char threshold
filters out blank pages and image-only PDFs.

### Blank B: `deterministic_extract`

**What:** Iterate over `FIELD_PATTERNS`. For each pattern, `re.search` the PDF text. If any field
is not found, return `None` (this format does not match the regex shortcut). If all match,
also check for the bill of sale heading using `HEADING_PATTERN`, then build and return an
`AffidavitExtraction`.

**Why:** The regex shortcut works on clean, labeled formats (Format A). It fails on narrative
prose (Format B), tabular layouts (Format C), different labels (Format D), and multi-amount
prose (Format E). When it returns `None`, the caller knows to fall back to the Brain.

**Key insight:** The function returns `None` (not partial results) so the caller knows to
fall back to the Brain. All-or-nothing is the correct behavior for format detection.

### Blank C (stretch): `extract_affidavit`

**What:** The hybrid extraction orchestrator:
1. Resolve live mode: if `use_live_api is None` (the default), set it from `live_mode_enabled()`
   so a real LLM is used when an API key is present and canned responses otherwise.
2. Eyes read the PDF with `read_pdf()`.
3. Regex shortcut tries `deterministic_extract()`. If it succeeds and variant is "correct", return it.
4. Otherwise: Brain takes over with `extract_with_llm()`.

**Why:** Regex for scale on known formats. Brain for everything else.
The variant guard ensures demo variants ("hallucinated") always take the Brain path.
The `use_live_api=None` auto-detect means the same code goes live (with a key) or canned
(without one) with no flags, everywhere it is called (REPL, the `python -m workshop.pipeline.extract`
CLI, and the Airflow DAG). See the README "Live LLM Mode" section.

---

## Pillar 2: Guardrails (`workshop/pipeline/guardrails.py`)

Mental model: the Conscience. Runs ALWAYS, regardless of whether regex or the Brain produced the output.

### Blank A: `normalize_amount`

**What:** Coerce input to string, strip `$` and commas, handle negatives (parenthetical like
`($150.00)` and minus sign like `-$150.00`), convert to float, round to 2 decimals.
Return None for empty/None input.

**Why:** The Brain returns `"$6,218.55"` (string). The source of truth has `6218.55` (float).
Without normalization, every amount comparison would be a mismatch.

### Blank B: `normalize_date`

**What:** Convert date strings to ISO format (YYYY-MM-DD). Handle: ISO passthrough,
MM/DD/YYYY, M/D/YYYY (no leading zeros). Stretch: verbose formats like "March 15, 2024"
and "15 March 2024".

**Why:** The Brain returns `"03/15/2024"`. The source of truth has `"2024-03-15"`.
Both must normalize to the same value for comparison.

### Blank C: `audit_bill_of_sale`

**What:** If the Brain claims `bill_of_sale_attached=True`, verify the PDF text actually
contains a standalone heading like "BILL OF SALE" or "CHARGED-OFF ACCOUNT ASSIGNMENT".
Four branches: `None` (MISSING), `False` (EXEMPT), `True` + heading found (MATCH),
`True` + heading not found (MISMATCH).

**Why:** The Brain can claim an exhibit is attached when it is not. The Conscience catches
this by searching for the actual heading. The regex requires a standalone heading (not inline
mentions in disclaimers).

### Blank D (stretch): `check_statement_contradiction`

**What:** Check for logical contradictions: (1) negative chargeoff balance (impossible),
(2) last payment date after chargeoff date (timeline violation).

**Why:** Even if all individual fields match, the combination can be nonsensical. A payment
after chargeoff should not exist. The Conscience catches logical impossibilities, not just
value mismatches.

### Blank E: `assign_verdict`

**What:** If ANY finding has a status other than MATCH or EXEMPT, the verdict is REVIEW.
The only path to PASS is every field matching.

**Why:** Never auto-approve. One wrong number in a sworn legal document is perjury.

### Blank F (stretch): `normalize_name`

**What:** Normalize a person's name so word order and punctuation do not matter: drop
punctuation (`.,;`), lowercase, split into tokens, sort them, and join. So `"GARCIA; MARIA L."`
and `"Maria L. Garcia"` both become `"garcia l maria"`.

**Why:** A live LLM often returns names as `"LAST; FIRST MIDDLE"` while the source of truth
stores `"First Middle Last"`. A strict compare would wrongly flag a mismatch. `compare_field`
falls back to `normalize_name` only when a plain match fails, and guards against `None`, so
leaving this blank unimplemented does **not** break the core exercise: clean/canned names still
match via the plain comparison. It only matters in live mode, which is why it is a stretch.

**Key insight:** Normalize before you compare (same lesson as `normalize_amount`/`normalize_date`),
applied to the messiest field an LLM produces: human names.

---

## Pillar 3: Idempotency (`workshop/pipeline/idempotency.py`)

Mental model: sits between the Brain and the Conscience. Caches the Brain's output, stores
the Conscience's verdict.

### Blank A: `hash_content`

**What:** SHA-256 hash of `f"{prompt_version}:{content}"`. Returns the hex digest.

**Why:** Same PDF text + same prompt version = same hash = cache hit. Changing the prompt
version invalidates all cached responses: old outputs may have been produced by a different
prompt and should not be trusted.

### Blank B: `upsert_result`

**What:** `INSERT ... ON CONFLICT DO UPDATE` in SQLite. The business key is
`(reference_id, buyer, process_date)`. Serialize the verdict fields as JSON.

**Why:** Running the pipeline twice on the same data should produce exactly one row,
not duplicates. Same pattern as Snowflake/BigQuery MERGE.

---

## Pillar 4: Orchestration (`dags/affidavit_dag.py`)

Mental model: the DAG wires all four roles together per buyer:
Eyes (read PDF) -> Regex/Brain (extract fields) -> Conscience (guardrails) -> Judge (review tickets).

**Prerequisite:** Complete Pillars 1 and 2 first. The DAG calls functions from both.

### Blank A (stretch): `validate_results`

**What:** The Conscience inside the DAG. For each extraction:
1. If status != "ok" or extraction is None: verdict REVIEW.
2. If reference_id not in source_records: verdict REVIEW.
3. Otherwise: build SourceRecord + AffidavitExtraction, run `check_all_fields` + `assign_verdict`.

### Blank B: `create_review_tickets`

**What:** The Judge routing. Loop over validated entries. For REVIEW cases, log the buyer,
reference_id, and reasons with `logger.warning(...)`. Skip PASS entries. (Logging, not `print`,
so the tickets show up cleanly in the Airflow task logs as WARNING lines.)

### Blank C: `process_buyer`

**What:** Wire the four tasks in sequence: `download -> parse -> validate -> tickets`.

**Key insight:** Without `.override(group_id=f"process_{buyer}")`, Airflow raises
`DuplicateTaskIdFound` because the `@task_group` uses the function name for every loop iteration.
