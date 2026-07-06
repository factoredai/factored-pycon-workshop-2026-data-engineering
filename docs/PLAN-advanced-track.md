# Workshop Hardening: More PDF Variety, Less Guidance

## Context

The PyCon Colombia 2026 workshop teaches 4 pillars (extraction, guardrails, idempotency, orchestration) through a debt sale affidavit pipeline. The concern: AI-assisted attendees finish the original exercises in 15-25 minutes out of 90 minutes of exercise time.

**Solution:** One path, everyone follows it, harder. More affidavit PDF formats that break regex and force the Brain (LLM) fallback. Less hand-holding in the blanks. Rebalanced timing.

---

## Extraction Architecture (what we teach)

Mapped to the mental model (Eyes / Brain / Conscience / Judge):

```
PDF
 |
 v
Eyes (read_pdf via pypdf) ──── reads ALL raw text from the PDF
 |                              faithful copy, no interpretation
 |
 v
detect_pdf_type()
 |
 |── "native" (text extracted)
 |     |
 |     v
 |   Regex ──── searches raw text for known field patterns
 |     |        e.g. "Consumer Name:\s+(.+)"
 |     |        deterministic shortcut, NOT a role in the model
 |     |
 |     |── all fields found ──> structured output (AffidavitExtraction)
 |     |                        skip the Brain, go to Conscience
 |     |
 |     └── any field missing ──> Brain (LLM on text)
 |                                receives the raw text from Eyes
 |                                interprets semantically
 |                                returns structured JSON
 |                                can hallucinate
 |
 |── "scanned" (no text extracted)
 |     |
 |     └── Brain (LLM with vision)
 |          reads the PDF image directly
 |          returns structured JSON
 |          no intermediate text step
 |
 v
Conscience (Guardrails) ──── runs ALWAYS, regardless of extraction path
 |                            compares structured output against source of truth
 |                            normalizes amounts, dates
 |                            flags mismatches
 |                            pure logic, no AI
 |
 v
PASS ──── all fields match ──── done
REVIEW ── at least one mismatch ──> Judge (Human) reviews
```

**Key teaching points:**
- Eyes READ. Regex and Brain EXTRACT. Different verbs, different operations.
- Regex for scale on known formats (free, instant, deterministic). Brain for formats regex can't handle.
- Conscience runs ALWAYS, regardless of which path produced the output.
- "Can read a PDF" and "can be trusted with a PDF" are different claims (Unsiloed, 2026).
- A null is preferable to a wrong value (Unstract, 2026).
- LLM errors don't announce themselves (Unsiloed, 2026). Only the Conscience catches them.

**In the workshop:** All PDFs are native text. The "scanned" branch is taught in slides but not exercised in code.

**LLM modes:** Canned JSON (default, offline), live Anthropic API, live OpenAI API, or local models. Canned responses are the safety net. The hope is most attendees use a real model.

**Code gap (documented, not implemented):** `extract_with_llm()` currently only accepts `pdf_text` (string). For the scanned path, it would need to accept the raw PDF image. Not implemented because all workshop PDFs are native text.

---

## Timeline (13 slides, 120 min)

| Time | Block | Slides | Duration |
|------|-------|--------|----------|
| 0:00 - 0:20 | Intro | 1-8 | 20 min |
| 0:20 - 0:50 | Exercise 1: Extraction | 9 | 30 min |
| 0:50 - 1:20 | Exercise 2: Guardrails | 10 | 30 min |
| 1:20 - 1:35 | Exercise 3: Idempotency | 11 | 15 min |
| 1:35 - 1:50 | Exercise 4: Orchestration | 12 | 15 min |
| 1:50 - 2:00 | Closing + Q&A | 13 | 10 min |

---

## PDF Format Inventory

| Format | PDF file | Account | Regex? | Brain needed? | Why |
|--------|----------|---------|--------|--------------|-----|
| A (clean labels) | `sample_affidavit.pdf` | ACCT-001 | Yes | No | Labeled fields match FIELD_PATTERNS |
| A (buyer_a) | `acct_1234_standard.pdf` | ACCT-002 | Yes | No | Same labels, different data |
| A-alt (extra whitespace) | `acct_1357_alt_labels.pdf` | ACCT-004 | Yes | No | Whitespace-flexible regex handles it |
| B (narrative prose) | `acct_5678_variant.pdf` | ACCT-002 | No | Yes | Data embedded in paragraphs, no labels |
| B (buyer_b) | `acct_9012_narrative.pdf` | ACCT-003 | No | Yes | Same narrative format, different buyer |
| B (footer BOS) | `acct_2468_footer_bos.pdf` | ACCT-004 | No | Yes | Prose + bill of sale only in disclaimer |
| C (table) | `acct_8899_table.pdf` | ACCT-005 | No | Yes | Short table headers without colons |
| D (alt field names) | `acct_3377_alt_fields.pdf` | ACCT-006 | No | Yes | Different labels ("Debtor Name" vs "Consumer Name") |
| E (multi amounts) | `acct_6644_multi_amounts.pdf` | ACCT-007 | No | Yes | 6 dollar amounts in prose, regex can't pick the right one |

9 PDFs total. 3 where regex works (A, A-buyer_a, A-alt). 6 where Brain takes over (B, B-buyer_b, B-footer, C, D, E).

All 9 PDFs have canned LLM responses in `data/canned_llm/{pdf_stem}/correct.json`.
All 7 accounts (ACCT-001 through ACCT-007) have entries in `data/seeds/source_of_truth.csv`.

---

## Mental Model Enforcement (code)

Every Python module in the repo maps to the mental model:

| File | Module docstring maps to |
|------|-------------------------|
| `workshop/pipeline/extract.py` | Pillar 1: Eyes (`read_pdf`) + Regex (`deterministic_extract`) + Brain (`extract_with_llm`) |
| `workshop/pipeline/guardrails.py` | Pillar 2: the Conscience. Runs ALWAYS. |
| `workshop/pipeline/llm_client.py` | The Brain. Fallback when regex fails. Can hallucinate. |
| `workshop/pipeline/idempotency.py` | Pillar 3: between Brain and Conscience. |
| `workshop/pipeline/models.py` | AffidavitExtraction = Brain/regex output. SourceRecord = Conscience's truth. |
| `dags/affidavit_dag.py` | Pillar 4: wires Eyes -> Regex/Brain -> Conscience -> Judge per buyer. |
| `run_demo.py` | Eyes -> Brain -> Conscience -> verdict. |
| `scripts/make_sample_pdf.py` | Formats A/A-alt = regex works. Formats B/C/D/E = Brain needed. |
| `tests/test_extract.py` | Pillar 1 tests. |
| `tests/test_guardrails.py` | Pillar 2 (Conscience) tests. |
| `tests/test_idempotency.py` | Pillar 3 tests. |
| `tests/test_dag.py` | Pillar 4 tests. |
| `README.md` | Full mental model in intro + Role column in pillars table. |

**Naming convention:** Eyes READ (`read_pdf`). Regex and Brain EXTRACT (`deterministic_extract`, `extract_with_llm`).

---

## Execution Status: ALL PHASES COMPLETE

All phases implemented, synced to all 3 branches, pushed to remote. Verified:
- 0 stale references (needs_ocr, extract_text, Path 1/2, workshop_advanced, invoice)
- 9 PDFs, 9 canned LLM responses, 7 accounts in source_of_truth.csv
- 13 slides with exploration prompts and mental model language
- Mental model docstrings in all 7 Python modules
- Main: blanked with one-line docstrings, tests fail on blanks
- Solutions: complete code, 87+ tests pass, SOLUTIONS.md rewritten with mental model
- run_demo.py works on all branches (read_pdf_text, not extract_text_from_pdf)

### Phase 3: Reduce guidance on main branch blanks (DONE)

**Problem:** The current blanks have detailed docstrings that are basically recipes. An AI assistant reads the docstring + tests and produces the solution in seconds. The attendee learns nothing.

**Principle:** The learning happens in EXPLORATION (reading PDFs, understanding formats, making design decisions), not in typing code. Tests stay (green/red signal). Docstrings shrink to one line (WHAT, not HOW). Slides add exploration prompts.

**What stays on main branch blanked files:**
- Function signatures (attendees know WHAT to implement)
- One-line docstrings (what the function does, not how)
- Tests (verification signal, attendees know WHEN they're done)
- `FIELD_PATTERNS` constant (attendees write logic, not regex)
- `HEADING_PATTERN` constant

**What gets removed from main branch blanked files:**
- Multi-line docstrings with step-by-step instructions
- Input/output examples in docstrings
- Literal SQL in docstrings
- Comments explaining the approach
- Any text that an AI can directly translate into code

**Examples of before/after (main branch only):**

`normalize_amount`:
```python
# BEFORE (current, too detailed)
def normalize_amount(raw):
    """Normalize a dollar amount to a plain float for comparison.
    Examples:
        "$6,218.55"  -> 6218.55
        "6218.55"    -> 6218.55
        None         -> None
    Coerce to str first, strip $ and commas, convert to float, round to 2 decimals.
    """
    pass

# AFTER (trimmed)
def normalize_amount(raw):
    """Normalize a dollar amount to a float for comparison."""
    pass
```

`upsert_result`:
```python
# BEFORE (literal SQL in docstring)
def upsert_result(reference_id, buyer, batch_date, verdict, db_path):
    """INSERT INTO results ... ON CONFLICT(reference_id) DO UPDATE SET ...
    Return True if new row, False if update.
    """
    pass

# AFTER (trimmed)
def upsert_result(reference_id, buyer, batch_date, verdict, db_path):
    """Insert or update a result row by reference_id. Return True if new, False if updated."""
    pass
```

`extract_affidavit`:
```python
# BEFORE (step-by-step recipe)
def extract_affidavit(pdf_path, variant="correct", use_live_api=False):
    """1. Extract text from the PDF with read_pdf().
    2. Try deterministic_extract(). If it succeeds AND variant is "correct", return it.
    3. Otherwise: call extract_with_llm() with the text, path, variant, and use_live_api flag.
    """
    pass

# AFTER (trimmed)
def extract_affidavit(pdf_path, variant="correct", use_live_api=False):
    """Hybrid extraction: Eyes -> Regex shortcut -> Brain fallback."""
    pass
```

**Solutions branch keeps full docstrings.** Attendees who run `git checkout solutions` see the detailed explanations as reference.

**Slide updates for exploration prompts:**

Each exercise slide adds an exploration step before the coding:

- **Slide 9 (Extraction, 30 min):** Add to speaker notes: "Antes de escribir codigo: corran `read_pdf()` en 2-3 PDFs diferentes. Impriman el texto. Miren como aparecen los campos. Algunos PDFs tienen campos etiquetados. Otros no. Eso les dice cuando el regex va a funcionar y cuando necesitan el Cerebro."
- **Slide 10 (Guardrails, 30 min):** Add to speaker notes: "Antes de implementar: miren source_of_truth.csv. Comparen los valores de la fuente de verdad contra lo que extrajeron en el Ejercicio 1. Los montos vienen como '$6,218.55' en el PDF y como 6218.55 en el CSV. Las fechas vienen como '03/15/2024' en el PDF y como '2024-03-15' en el CSV. Eso les dice que normalizar."
- **Slide 11 (Idempotency, 15 min):** Add to speaker notes: "La idea: si corren el pipeline dos veces sobre el mismo PDF, no debe duplicar resultados. Miren idempotency.py. La funcion hash_content les dice como crear un cache key. La funcion upsert_result les dice como guardar sin duplicar."

**Why this works with AI-assisted attendees:**
1. The AI can still help write code once the attendee understands the problem.
2. But the understanding comes from EXPLORING the data (reading PDFs, comparing formats, studying source_of_truth.csv).
3. The exploration is the part AI can't shortcut (unless the attendee pastes PDF text into the AI, which is fine because then they're doing the exploration anyway).
4. The one-line docstrings tell the attendee WHAT the function does. The tests tell them WHEN they're done. But HOW to implement is up to them.

### Phase 4: Sync branches and verify (DONE)

All three branches synced and pushed to remote. Verified.

---

## Branch Sync Strategy

| Branch | Purpose | Who sees it |
|--------|---------|-------------|
| `feat/workshop-content` | Development | Only us |
| `main` | Attendees clone | Attendees |
| `solutions` | Escape hatch | Attendees (opt-in) |

| Content | feat/workshop-content | main | solutions |
|---------|----------------------|------|-----------|
| `workshop/pipeline/*.py` | Complete | Blanked (trimmed docstrings) | Complete |
| `dags/affidavit_dag.py` | Complete | Blanked | Complete |
| `tests/` | All tests | All tests | All tests |
| `data/pdfs/` (9 PDFs) | Yes | Yes | Yes |
| `data/canned_llm/` (9 dirs) | Yes | Yes | Yes |
| `data/seeds/source_of_truth.csv` | Yes | Yes | Yes |
| `run_demo.py` | Yes | Yes | Yes |
| `docs/PLAN.md` | Yes (unchanged) | No | No |
| `docs/PLAN-advanced-track.md` | Yes | No | No |
| `slides/deck-draft.html` | Yes | No | No |
| `SOLUTIONS.md` | No | No | Yes |

---

## Decisions

- **Single path.** No two-path fork. Everyone follows the same exercises.
- **9 PDFs, 6 formats.** 3 regex-friendly, 6 that force the Brain.
- **Less docstring guidance** on main branch blanks (Phase 3, done).
- **`"needs_ocr"` renamed to `"scanned"`.** Describes the PDF, not the action.
- **`extract_text` renamed to `read_pdf`.** Eyes READ. Regex/Brain EXTRACT.
- **Brain is the fallback for everything.** Native PDFs where regex fails AND scanned PDFs both route to the Brain. Conscience validates regardless.
- **Slides use mental model language consistently.** Eyes/Brain/Conscience/Judge in all speaker notes.
- **13 slides.** Old slide 10 ("Guardrails in Focus") removed, content in Exercise 2 speaker notes.
- **Timing: 30/30/15/15/10.**

## References (speaker prep)

- Unstract: "LLMs for Structured Data Extraction from PDFs" (null > wrong value, "traditional OCR remains the most reliable for uniform workloads")
- Unsiloed: "Are LLMs Good Enough for Document Extraction in 2026?" ("errors do not announce themselves")
- Medium: "Building Trust in LLM Answers: Highlighting Source Texts in PDFs" (source attribution, out of scope)
- Klippa: "LLMs vs OCR Software" (https://www.klippa.com/en/blog/information/llms-vs-ocr-software/). Hybrid approach comparison, supports our regex-first architecture
- Medium (evalowisz): "Don't Use LLMs as OCR" (https://medium.com/@evalowisz/dont-use-llms-as-ocr-lessons-from-complex-documents-8401b6a54d62). Lessons from complex documents, validates deterministic layer
- LlamaIndex: "Beyond OCR: How LLMs Are Revolutionizing PDF Parsing" (https://www.llamaindex.ai/blog/beyond-ocr-how-llms-are-revolutionizing-pdf-parsing). Industry trend toward LLM-based extraction
