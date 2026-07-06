# Workshop PyCon Colombia 2026: PDF Data Extraction + Deterministic Guardrails

## Context

Douglas represents **Factored** at PyCon Colombia 2026 (July 24-26). 2-hour hands-on workshop,
in Spanish, for a senior audience. Based on a real production pipeline at a US fintech client
(Airflow + Snowflake Cortex + deterministic guardrails). ~$60M+ in proceeds.

Attendees do not have Snowflake. The workshop recreates the **architecture and patterns** in a
local, self-contained environment (Docker + pure Python).

### Key dates

- **Deck to Diego (marketing)**: July 15. DONE. Google Slides maintained by Douglas.
- **Repo public**: July 22. Coordinate with IT. IN PROGRESS.
- **Workshop**: Sunday July 26.

### Progress (updated 2026-07-22)

| Phase | Status |
|-------|--------|
| Fase 0 (vertical slice) | DONE |
| Fase 1 (4 pillars) | DONE |
| Fase 2 (Docker/Airflow) | DONE |
| Fase 3 (branching) | DONE |
| Fase 4 (rehearsal) | IN PROGRESS (Docker verified, timer rehearsal pending) |

### Branch layout

| Branch | Purpose | Internal docs | Code |
|--------|---------|---------------|------|
| `main` | Attendees clone this | No | Blanked |
| `solutions` | Escape hatch | SOLUTIONS.md | Complete |
| `feat/workshop-content` | Internal archive (frozen) | PLAN.md, deck-draft.html | Complete |

---

## Decisions

1. **LLM**: canned JSON responses in repo (works offline). Optional live API with own key.
2. **Airflow**: dockerized, DAG with placeholders. Production disclaimer: Airflow is an
   orchestrator, not a compute engine. Heavy lifting goes elsewhere.
3. **4 pillars**: extraction, guardrails, idempotency, orchestration.
4. **Setup**: `docker compose build` (pre-event) + `docker compose up -d` (day of).
5. **Title**: "Extraccion de datos de PDFs a escala: cuando confiar en un LLM" (FINAL, submitted).
6. **Tone**: patterns first, tools as examples. No name-dropping frameworks attendees have not used.
7. **Regex patterns provided**: FIELD_PATTERNS and HEADING_PATTERN are given as constants.
   Attendees write the extraction logic, not the regex.
8. **DAG tasks mostly provided**: download_pdfs and parse_and_extract are given. Attendees
   implement create_review_tickets (trivial) and process_buyer wiring (the real lesson).
9. **Exercise 4 dependency**: requires Exercises 1-2 to be solved. Documented in DAG docstring
   and README.
10. **process_buyer uses `pass`** on main (not NotImplementedError) because @task_group body
    runs at parse time. NotImplementedError would prevent the DAG from loading in the UI.

---

## Conventions

- **Language**: all repo content in English. Delivery in Spanish. Title/summary for PyCon in Spanish.
- **Sanitization**: no client name, no PII, no real buyer names, no internal URLs.
  Use "a fintech client of Factored" or "inspired by a real production system."

---

## Glosario de conceptos clave

| Termino | Significado |
|---|---|
| **PDF** | Portable Document Format. Can contain embedded text (native) or scanned images. The distinction determines the extraction tool. |
| **OCR** | Optical Character Recognition. Converts images of text into machine-readable text. Examples: Tesseract, Amazon Textract, Google Vision. |
| **LLM** | Large Language Model. Interprets and structures text. Can hallucinate. Examples: Claude, GPT, Gemini. |
| **VLM** | Vision Language Model. An LLM that can also "see" images. Can read scanned PDFs directly. |
| **Determinismo** | A process that always produces the same output for the same input. Regex is deterministic. LLMs are NOT, even with temperature=0. |
| **Guardrail** | Deterministic validation (rules, not AI) that verifies LLM output against a source of truth. |
| **Alucinacion** | When an LLM generates plausible but fabricated information. Critical in legal/financial contexts. |
| **Idempotencia** | An operation that produces the same result no matter how many times you run it. Hash + upsert in this workshop. |
| **DAG** | Directed Acyclic Graph. In Airflow, a workflow defined as a graph of tasks with dependencies. |
| **Pydantic** | Python library for data validation using type hints. Defines AffidavitExtraction, Finding, Verdict schemas. |
| **Fuente de verdad** | The transactional data (`source_of_truth.csv`) against which LLM extractions are compared. |
| **Affidavit** | Sworn legal document. A wrong number = perjury. This is why guardrails are non-negotiable. |
| **Bill of Sale** | Document transferring account ownership from seller to buyer. Attached as an exhibit. |
| **Chargeoff** | When the creditor writes off the debt as a loss. The chargeoff balance and date are critical fields. |
| **Debt Buyer** | Company that buys charged-off debt portfolios. In the workshop: "Buyer A, LLC", "Buyer B, LLC". |
| **Original Creditor** | The financial institution that originated the credit. Signs the affidavit (or its servicer does). |
| **PASS / REVIEW** | Pipeline verdicts. PASS: all fields match. REVIEW: at least one mismatch, needs human review. |
| **Proceeds** | Money collected from selling debt portfolios. ~$60M impact measure for the production system. |
| **Perjury** | Crime of making a false statement under oath. Why the guardrails exist. |

---

## Real Document Analysis (reviewed 2026-07-18)

Reference files in `~/Downloads/affidavits samples/` (NOT committed, contains PII).

### Three formats discovered

| Format | Title | Pages | Key traits |
|---|---|---|---|
| "Affidavit of Account" | AFFIDAVIT OF ACCOUNT | 2 | Narrative prose, LAST; FIRST names, masked accounts, no labeled fields |
| "Affirmation CCR4" | Affirmation of Facts and Sale (UCS-CCR4) | 3 + exhibits | NY court form, checkbox structure, data in exhibits |
| "Affirmation CCR5" | Affirmation of Purchase and Sale (UCS-CCR5) | 3 + exhibits | Same form, different entity language |

### Real patterns in our synthetic PDFs

- Consumer name "LAST; FIRST" format: implemented in Format B.
- Account masking XXXXXXXXXXXX+last4: implemented in Format B.
- Dates without leading zeros (M/D/YYYY): implemented in normalize_date.
- "CHARGED-OFF ACCOUNT ASSIGNMENT" heading: implemented in audit_bill_of_sale regex.

### Deliberate simplifications

**What we replicate:** two structurally different formats (regex works on one, fails on the other),
full guardrail pipeline, hallucination caught by deterministic code, idempotency, orchestration.

**What we do NOT replicate:** multi-page bundles (18-41 pages), OCR/scanned challenges,
table extraction from exhibits, portfolio-level fields without per-account values.

### Decision: dropped Format C (scanned)

Real affidavits are text-native PDFs. Simulating a scan adds Pillow dependency for minimal value.
Scanned handling in production is a one-line `if` (route to human review).

---

## Title and Summary (submitted to PyCon)

> **"Extraccion de datos de PDFs a escala: cuando confiar en un LLM"**

> Los LLMs leen documentos caoticos como nadie, pero cuando te juegas dinero o responsabilidad
> legal, la pregunta no es "puede?" sino "cuando debo confiar y como lo atrapo cuando se
> equivoca?"...

STATUS: submitted July 6. Do not change without notifying marketing.

---

## Architecture: Eyes / Brain / Conscience / Judge

The mental model taught in the workshop:

- **Eyes** (Parser): extracts faithful text. Does not interpret.
- **Brain** (LLM): interprets text, structures into fields. Can hallucinate.
- **Conscience** (Guardrails): deterministic Python comparing LLM output against source of truth.
- **Judge** (Human): reviews cases where the conscience flagged a mismatch.

Key concepts taught:
- LLM for discovery (new formats), deterministic for scale (known formats).
- The hybrid pattern: regex first, LLM fallback.
- Never auto-approve. One mismatch = REVIEW.
- Prompt versioning invalidates cache (prevents silent bugs on prompt changes).
- Idempotency via content hash + INSERT ON CONFLICT DO UPDATE.
- TaskGroup per entity for clean parallel orchestration.

---

## Docker decisions (Airflow 3)

- **5 services**: postgres, airflow-init, airflow-apiserver, airflow-scheduler, airflow-dag-processor.
- **LocalExecutor** (no Celery, no Redis).
- **dag-processor required**: without it, DAGs never appear in the UI (Airflow 3 separated parsing).
- **EXECUTION_API_SERVER_URL**: required for scheduler-to-apiserver communication.
- **Shared secrets** (WEBSERVER_SECRET_KEY, JWT_SECRET): without them, each container generates
  its own secret and JWT verification fails between services.
- **Volume mounts**: dags/, workshop/, data/, tests/ mounted so local edits are visible instantly.
- **PYTHONPATH=/opt/airflow**: lets DAG do `from workshop.pipeline...`.
- **Timing**: `docker compose build` ~35-40s cold. `docker compose up -d` ~40-45s cold.

---

## Timeline (14 slides, 120 min)

| Time | Block | Slides | Duration |
|---|---|---|---|
| 0:00-0:20 | Intro (title, objectives, problem, context, demo) | 1-8 | 20 min |
| 0:20-0:35 | **Exercise 1: Extraction** | 9 | 15 min |
| 0:35-1:05 | **Exercise 2: Guardrails** (star) | 10-11 | 30 min (2 intro + 26 work + 2 checkpoint) |
| 1:05-1:23 | **Exercise 3: Idempotency** | 12 | 18 min |
| 1:23-1:41 | **Exercise 4: Orchestration** | 13 | 18 min |
| 1:41-2:00 | Closing + Q&A | 14 | 19 min |

---

## Exercises: what is blanked

### Exercise 1: `workshop/pipeline/extract.py`
- **Blank A (core)**: `detect_pdf_type` (3 lines)
- **Blank B (core)**: `deterministic_extract` (10 lines, patterns given as FIELD_PATTERNS)
- **Blank C (stretch)**: `extract_affidavit` (7 lines, hybrid extraction wiring)

### Exercise 2: `workshop/pipeline/guardrails.py`
- **Blank A (core)**: `normalize_amount` (6 lines)
- **Blank B (core)**: `normalize_date` (8 lines, stretch: verbose month name)
- **Blank C (core)**: `audit_bill_of_sale` (25 lines, 4-way branching)
- **Blank D (stretch)**: `check_statement_contradiction` (8 lines)
- **Blank E (core)**: `assign_verdict` (6 lines)

### Exercise 3: `workshop/pipeline/idempotency.py`
- **Blank A (core)**: `hash_content` (2 lines)
- **Blank B (core)**: `upsert_result` (15 lines, SQL given in docstring)

### Exercise 4: `dags/affidavit_dag.py`
- **Blank A (stretch)**: `validate_results` (35 lines)
- **Blank B (core)**: `create_review_tickets` (4 lines)
- **Blank C (core)**: `process_buyer` wiring (4 lines)
- Provided: `download_pdfs`, `parse_and_extract`, `load_source_records`

---

## Slide list (14 slides, source: Google Slides maintained by Douglas)

1. Title + QR
2. What You Will Learn (4 objectives)
3. The Real Problem ($60M, perjury risk)
4. How Extraction Evolved (4 waves)
5. PDF Types (during smoke test)
6. Eyes / Brain / Conscience / Judge + Poll
7. Architecture + Demo (run_demo.py)
8. The 4 Pillars (exercise map)
9. Exercise 1: Extraction (15 min)
10. Guardrails in Focus (failure modes, production accuracy)
11. Exercise 2: Guardrails (26 min + 2 min checkpoint)
12. Exercise 3: Idempotency (15 min + 2 min checkpoint)
13. Exercise 4: Orchestration (16 min, Airflow primer included)
14. Closing (5 patterns + Q&A)

Reference HTML: `slides/deck-draft.html` on `feat/workshop-content` branch.

---

## PyCon form (submitted, reference only)

- **Type**: Workshop (2 hours). **Written**: English. **Spoken**: Spanish. **Level**: Advanced.
- **Tags**: Artificial Intelligence, Data Engineering.
- **Repo**: https://github.com/factoredai/factored-pycon-workshop-2026-data-engineering
- **Tech requirements**: HDMI projector, stable WiFi for ~30 attendees, power outlets.

---

## Verification checklist (pre-event)

- [ ] Cold setup on clean machine: clone, venv, pip install, docker compose build+up.
- [ ] `python run_demo.py` produces PASS. `--variant hallucinated` produces REVIEW.
- [ ] `pytest` on `main` fails (blanks). On `solutions` passes (65+).
- [ ] `run_demo.py` works on BOTH branches (self-contained).
- [ ] Airflow UI at localhost:8080, DAG trigger produces green graph with TaskGroups.
- [ ] Volume mount: local edit visible in Airflow without rebuild.
- [ ] Format B falls back to LLM in DAG (regex returns None, canned response used).
- [ ] Idempotency: run twice, 0 duplicates, cache hit on second run.
- [ ] Cache invalidation: change PROMPT_VERSION, verify fresh extraction.
- [ ] `docker compose exec airflow-scheduler pytest /opt/airflow/tests/test_dag.py` passes.
- [ ] Degraded mode (no Docker): exercises 1-3 work with pytest only.
- [ ] Timer rehearsal: 120-min dry-run with speaker notes.
- [ ] Multi-OS: macOS (done), Windows WSL2, Linux.
- [ ] Repo public: `git clone` from a non-Douglas account works.
