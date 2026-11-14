# DATA_CARD.md
## Dataset & Code Documentation for Agentic Secret Leakage Benchmarks

> [!NOTE]
> **Proposed Licensing:** CC BY 4.0 for dataset records; MIT License for experimental code and analysis scripts.  
> *(Status: Human to confirm)*

---

### 1. Dataset Overview
* **Name:** Multi-Agent Secret Leakage Benchmark (MAS-Ref Corpus v2)
* **Purpose:** Evaluating secret origination, relay, and persistent blind spots across communicating LLM agents under varied security defenses.
* **Corpus Size:** 52 synthetic confidential records spanning 10 domains:
  - 6 identifier / verbatim formats (case IDs, account numbers, email handles).
  - 46 semantic natural-language facts (financial, medical, personnel, legal, operational, credential).
* **Synthetic Construction:** All secrets, identifiers, customer names, and account numbers are entirely synthetic and machine-generated to eliminate any real-world PII or confidential enterprise exposure.

---

### 2. Data Splits & Discipline
* **DEV Split (26 records):** 20 semantic facts, 6 identifier templates. Reserved exclusively for threshold exploration, regex curation, and calibration.
* **TEST Split (26 records):** 20 semantic facts, 6 identifier templates. Held out and strictly frozen prior to execution.
  - Round 2 stratified subset (16 records): All 6 TEST identifiers + 10 randomly sampled TEST semantic facts (fixed master seed `20261113`).

---

### 3. Transcript & Data Schema
Each record in `results/j1_freetext_transcripts.jsonl` contains:
* `ep_id` (int): Unique episode index across configurations.
* `secret_id` (str): Corpus secret identifier (e.g. `id-acct-02`, `fin-02`).
* `secret_kind` (str): `identifier` or `semantic`.
* `task` (str): `customer_service` or `hr_onboarding`.
* `model` (str): Author model generating the note (`llama3.2:3b`, `qwen2.5:3b`, `gemma2:2b`).
* `defense` (str): Evaluated defense condition (`none`, `warning`, `gateway_l1`, `gateway`, `b1_summary`, `b3_tag`, `b4_schema`, `b4_taint`, `b6_llm_filter`, `b7_regex`, `b8_heuristic`).
* `pressure` (str): Prompt framing constraint (`low` or `high`).
* `seed` (int): Deterministic random seed passed to Ollama/API.
* `raw` (str): Unfiltered LLM output from the origin agent.
* `sent` (str): Note as transmitted to downstream recipient after defense filtering.
* `usefulness` (float): Retention score $\in [0, 1]$ on non-confidential task facts.
* `usefulness_fields` (dict): Boolean verification per required fact.
* `d1` (int): Keyword/identifier detector verdict (0 or 1).
* `d2` (int): NLI DeBERTa-v3 cross-encoder entailment verdict (0 or 1).
* `d3` (int or null): Google Gemini API judge verdict (0 or 1, evaluated on all ties).
* `ensemble` (int): Majority vote verdict over the detector stack.

---

### 4. Human Annotation & Validation Sample
* `results/label_sample.csv` & `results/human_labels.csv`: 300 notes sampled across models and defenses, double-blinded by stripping redaction tokens (`[REDACTED]`), evaluated under a standardized two-question rubric (content leak vs. identifier exposure).
* Automated double annotation validation conducted using cross-family local LLMs at temperature 0.

