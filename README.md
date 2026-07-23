# PDF Data Extraction at Scale: When to Trust an LLM

> Workshop at [PyCon Colombia 2026](https://2026.pycon.co/talks/48/) by Douglas Ardila ([Factored](https://factored.ai))

LLMs can read chaotic documents like no other tool, but when money or legal liability is on the line, the question is not "can it?" but "when should I trust it and how do I catch it when it's wrong?"

During this 2 hour workshop, you will build a production-tested pipeline for extracting data from variable-format legal PDFs. The mental model: **Eyes** (pypdf reads the PDF), **Regex** (deterministic shortcut on known formats), **Brain** (LLM fallback when regex fails), **Conscience** (guardrails cross-check against transactional data), and **Judge** (human reviews flagged cases). If the Brain hallucinates, the Conscience catches it.


## What You Will Build

| Pillar | Role | What | File |
|--------|------|------|------|
| 1. Extraction | Eyes + Regex + Brain | PDF type detection, regex for clean formats, LLM fallback for the rest | `workshop/pipeline/extract.py` |
| 2. Guardrails | Conscience | Normalize amounts/dates, audit exhibits, assign PASS or REVIEW verdict | `workshop/pipeline/guardrails.py` |
| 3. Idempotency | (between Brain and Conscience) | Content-hash cache + SQLite upsert by business key (run twice, zero duplicates) | `workshop/pipeline/idempotency.py` |
| 4. Orchestration | Wires all roles per buyer | Airflow DAG with TaskGroups | `dags/affidavit_dag.py` |

Try the end-to-end demo before starting the exercises:

```bash
python run_demo.py                              # Correct extraction -> PASS
python run_demo.py --variant hallucinated       # Guardrail catches fabricated amount -> REVIEW
python run_demo.py --variant hallucinated_dates # Catches payment-after-chargeoff -> REVIEW
```

## Project Layout

```
.
├── workshop/pipeline/
│   ├── models.py           # Pydantic models (Finding, Verdict, AffidavitExtraction)
│   ├── llm_client.py       # Canned LLM responses (or live API if you have a key)
│   ├── extract.py          # Exercise 1: extraction
│   ├── guardrails.py       # Exercise 2: guardrails
│   └── idempotency.py      # Exercise 3: idempotency
├── dags/
│   └── affidavit_dag.py    # Exercise 4: orchestration
├── data/
│   ├── pdfs/               # Synthetic affidavit PDFs (6 formats, some regex-friendly, some not)
│   ├── canned_llm/         # Pre-recorded LLM responses (correct + hallucinated)
│   └── seeds/              # Source of truth CSV (transactional data) + PDF manifest
├── tests/                  # One test file per exercise (your green/red signal)
├── run_demo.py             # Self-contained demo (works even with blanked exercises)
├── docker-compose.yml      # Airflow 3 infra (Exercise 4)
└── Dockerfile
```

## Prerequisites

- Python 3.11+
- Docker Desktop (4 GB RAM, 5 GB disk)
- Git
- (Optional) An Anthropic, OpenRouter, or OpenAI API key for live LLM mode

| Platform | Docker | Notes |
|----------|--------|-------|
| **macOS** | Docker Desktop | Works out of the box. |
| **Linux** | Docker Engine + Compose v2 | Create `.env` with `AIRFLOW_UID=$(id -u)` (see step 3). |
| **Windows** | Docker Desktop (WSL2) | Make sure WSL2 is enabled. |

## Setup (run this before the event)

1. Clone and install:
   ```bash
   git clone https://github.com/factoredai/factored-pycon-workshop-2026-data-engineering.git
   
   cd factored-pycon-workshop-2026-data-engineering
   
   python -m venv .venv
   
   source .venv/bin/activate    # Linux/macOS
   .venv\Scripts\activate       # Windows
   
   pip install -r requirements.txt
   ```

2. (Linux only) Set your user ID for Docker file permissions:
   ```bash
   echo "AIRFLOW_UID=$(id -u)" > .env
   ```

3. Build Docker images (**do this on good WiFi, before the event**):
   ```bash
   docker compose build
   ```
   Downloads ~1.9 GB. Takes under a minute on fast WiFi, potentially 10+ minutes on conference WiFi. Do this ahead of time.

4. Start Airflow:
   ```bash
   docker compose up -d
   ```
   Cold start: ~40-45s to all services healthy. No network needed.

5. Verify:
   ```bash
   python run_demo.py                    # Should print VERDICT: PASS
   ```

   Open http://localhost:8080          # Login: airflow / airflow


> **Tip:** Steps 1-3 need good WiFi. On event day, `source .venv/bin/activate` +
> `docker compose up -d` starts in under a minute.

### Security note

`docker-compose.yml` ships with hardcoded secrets and the default `airflow`/`airflow` login.
This is intentional for an ephemeral localhost workshop with synthetic data. Not appropriate for
real deployments. Override via `.env` if you want your own values (see `.env.example`).

## Exercises

| # | Role | File | Run with | What You Do |
|---|------|------|----------|-------------|
| 1 | Eyes + Regex + Brain | `workshop/pipeline/extract.py` | `pytest` (local) | PDF type detection + extraction logic (regex patterns provided) |
| 2 | Conscience | `workshop/pipeline/guardrails.py` | `pytest` (local) | Normalize amounts/dates, audit exhibits, assign verdict |
| 3 | (between Brain and Conscience) | `workshop/pipeline/idempotency.py` | `pytest` (local) | Content-hash cache + SQLite upsert |
| 4 | Wires all roles | `dags/affidavit_dag.py` | Airflow UI (Docker) | Wire TaskGroup per buyer + review ticket task (most tasks provided) |

Each exercise has **core blanks** (required) and **stretch blanks** (for fast participants).

Exercises 1-3 are independent (solve in any order).
Exercise 4 calls functions from Exercises 1 and 2, so complete those first.

### Checking your work

After filling in a blank, run the corresponding test:
```bash
pytest tests/test_extract.py        # Exercise 1
pytest tests/test_guardrails.py     # Exercise 2
pytest tests/test_idempotency.py    # Exercise 3
```

**Core vs stretch blanks.** Each exercise has required *core* blanks and optional *stretch*
blanks. Tests for the stretch blanks are tagged with a custom `stretch` marker (registered in
`pyproject.toml`, applied via `@pytest.mark.stretch`). If you only did the core blanks, run
core-only so the stretch tests don't show as failures:
```bash
pytest tests/test_guardrails.py -m "not stretch"   # core blanks only
pytest tests/test_guardrails.py -m stretch         # just the stretch blanks
```
`-m` filters by marker (pytest's built-in mechanism, see the
[pytest docs](https://docs.pytest.org/en/stable/how-to/usage.html)). `-k "not stretch"` also
works because pytest treats a marker name as a test keyword.

The full suite (`pytest`) skips `test_dag.py` locally because `apache-airflow` is not in the venv. That is expected. For Exercise 4, trigger the DAG from the Airflow UI at `localhost:8080`.

Advanced (run DAG tests inside the container):
```bash
docker compose exec airflow-scheduler pytest /opt/airflow/tests/test_dag.py
```

### Stuck?

```bash
git checkout solutions    # Complete implementation + SOLUTIONS.md walkthrough
```

### Docker not working?

Exercises 1-3 are pure Python and work without Docker:
```bash
pytest tests/test_extract.py tests/test_guardrails.py tests/test_idempotency.py
```
Only Exercise 4 requires Docker. If Docker fails, follow along on the projector.

## Troubleshooting

**Airflow UI doesn't load (`localhost:8080`):**
```bash
docker compose ps                                  # Are all services healthy?
docker compose logs airflow-apiserver --tail=50
docker compose logs airflow-scheduler --tail=50
```

**DAG doesn't appear in the UI:**
```bash
docker compose ps                                  # Is airflow-dag-processor running?
docker compose logs airflow-dag-processor --tail=50
docker compose exec airflow-scheduler airflow dags list-import-errors
```
In Airflow 3, DAG parsing is a separate service (`airflow-dag-processor`). If it is not running, DAGs never appear even if the file is correct.

**"DuplicateTaskIdFound" error:**
You forgot `.override(group_id=f"process_{buyer}")` on the `@task_group` inside the for-loop.
See the docstring in `dags/affidavit_dag.py`.

**Docker out of disk / low RAM:**
```bash
docker system df        # See what's using space
docker system prune     # Remove unused images/volumes (destructive)
```

**Full reset (wipes DB and volumes):**
```bash
docker compose down -v 
docker compose up -d
```

**`test_dag.py` skipped locally:**
Expected. Run DAG tests inside the container:
```bash
docker compose exec airflow-scheduler pytest /opt/airflow/tests/test_dag.py
```

## Live LLM Mode (Optional)

By default the workshop uses pre-recorded LLM responses (works offline, no API key needed).
If you want to watch a real LLM read the PDFs, you set **one** thing and it lights up
everywhere. No code changes, no flags to thread through.

**1. Install an SDK and set a key in `.env`** (see `.env.example`):

```bash
pip install openai        # covers OpenAI AND OpenRouter (OpenRouter speaks the OpenAI API)
# or: pip install anthropic   # for a direct Anthropic key
```

```bash
# .env  (set exactly one)
OPENROUTER_API_KEY=sk-or-v1-...   # routed through the openai SDK to a custom base_url
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
```

> An OpenRouter key is neither an OpenAI nor an Anthropic key: it is OpenRouter's own format
> (`sk-or-v1-...`), used through the `openai` SDK pointed at OpenRouter's OpenAI-compatible
> endpoint. The model it calls (`anthropic/claude-haiku-4.5` by default) is still Claude.

**2. Live mode is auto-detected.** With a key present, `extract_affidavit()` calls the real LLM;
with no key it uses canned responses. The same env var drives both local runs and the Airflow
DAG (Docker Compose forwards the key into the containers). Precedence when several are set:
Anthropic, then OpenRouter, then OpenAI.

### Where you actually see the LLM

The Brain only runs when the **regex shortcut misses** (Formats B-E). On clean Format A PDFs,
regex wins and no LLM is called, that is the point. Every extraction logs which path it took:

```
INFO workshop.pipeline.extract: Regex shortcut hit for acct_1234_standard.pdf (Brain skipped)
INFO workshop.pipeline.extract: Regex missed for acct_9012_narrative.pdf -> Brain fallback (live LLM)
INFO workshop.pipeline.llm_client: Brain: live extraction via OpenRouter (anthropic/claude-haiku-4.5)
```

- **Exercise 1 (extraction), no Docker:** once your tests pass, run the extractor on one PDF and
  watch the path it takes (the `INFO` log shows regex-shortcut vs Brain-fallback):
  ```bash
  python -m workshop.pipeline.extract        # a messy PDF (Formats B-E) -> live Brain
  python -m workshop.pipeline.extract data/pdfs/buyer_a/2026-07-01/acct_1234_standard.pdf  # clean -> regex, no LLM
  ```
  With a key set the Brain calls a real LLM; without one it uses canned responses. Real model
  output often varies from the source of truth (e.g. a name comes back as `GARCIA; MARIA L.`).
  That is exactly what the guardrails (Exercise 2) exist to catch.
- **Exercise 4 (orchestration):** with a key in `.env`, `docker compose up` runs the DAG against
  the real LLM automatically. Open a `parse_and_extract` task in the Airflow UI and read its
  logs to see the regex-vs-Brain line per PDF, then watch REVIEW verdicts appear downstream.

### `pytest` always stays canned (by design)

Grading never calls the live API, even with a key set. `tests/conftest.py` strips the three key
env vars for every test, so the suite stays offline, fast, and free, and a blank that
accidentally forces live mode fails loudly instead of silently spending your budget. This is
deliberate: live output is nondeterministic (that `GARCIA; MARIA L.` would fail an exact-match
assertion), so it is great for *seeing* the pipeline work but wrong for a pass/fail check. Use
`pytest` to grade, and the live snippet or the DAG to watch.

## About the Instructor

**Douglas Ardila**: Engineering Manager & Data Engineer at [Factored](https://factored.ai).
5+ years architecting pipelines with Snowflake, Airflow, dbt, and GCP. 4+ years as Engineering
Manager, mentoring 30+ engineers and growing a Data Engineering CoE to 100+ engineers. This
workshop is based on a real production pipeline that processes thousands of legal PDFs for
automated debt-sale affidavit review.

## License

MIT. See [LICENSE](./LICENSE). All data in `data/` is synthetic. No real consumer data,
account IDs, or dollar amounts appear in this repository.
