# Which Defense, When? Origination, Relay and Blind Spots in Secret Leakage Between LLM Agents

Research code, pre-registration records, transcripts, verification scripts, and manuscript sources studying accidental secret leakage and defense trade-offs across multi-agent LLM workflows.

---

## Key Takeaways (No Single Defense Wins)

Which confidentiality defense works best depends on **where the secret lives**, **model scale**, and **workflow depth**:

| Regime | Best Defense | Measured Result | Caveat / Scope |
| :--- | :--- | :--- | :--- |
| **Schema-segregated column** (local 2B–3B, customer service TEST) | **Static ACL (`B4`)** | Eliminates leakage (`T = 0.000`) and improves utility (`U = 0.844`, `ΔU = +0.065`) | Assumes confidential fields are separated from task fields in a structured schema |
| **Entangled free-text email** (local 2B–3B, secret mixed into body) | **L1+L2 Semantic Gateway** | Cuts leakage from `T = 0.958` (`B0` / `B4-schema`) to `T = 0.125` (`0.292` under `D1`) while retaining utility (`U = 0.760` vs. `0.771`, `ΔU = -0.010`, 90% CI `[-0.073, +0.060]`) | **Preliminary:** post hoc follow-up, `n = 24` paired TEST episodes; `B4-taint` drops utility to `0.000` |
| **Small local models (`2B–3B`) vs. API model (`gemini-3.5-flash-lite`)** | **L1+L2 Gateway** (local) / **Prompt warning (`B2`)** (API) | On local 2B–3B pooled TEST (`n = 768` notes), `L1+L2` cuts hop-1 origination `11.2×` (`0.641 → 0.057` Ensemble; `0.672 → 0.224` `D1`), while `B2` fails; on `gemini-3.5-flash-lite`, `B2` cuts `T` from `0.500` to `0.025` (gateway: `0.000`) | API tier evaluated at hop 1 only; `gemini-3.5-flash-lite` also served as external `D3` judge (local rotation for self-ties) |
| **Multi-hop propagation & single-family filtering** | **Cross-family / multi-hop mitigation** | Separating origination `o` from downstream relay `r` cuts 6-agent held-out star prediction MAE from `1.00` to `0.30`; gateway slips survive rewrites (`0.873` Llama, `0.913` Qwen), leaving a `15–68%` 500-agent outbreak floor | Persistence pools use exploratory DEV boundary prompts; 500-agent outbreak floors are Monte Carlo simulations (`J7`); `12`-agent broadcast probe is inconclusive (`D1` single-`T` MAE `0.81` vs. `(o,r)` `0.98`) |

- **Measurement transparency:** On a 300-note blinded human benchmark (single annotator), the Gemini-adjudicated majority-vote Ensemble reached `κ = 0.68` (recall `0.90`), while lexical/ID detector `D1` reached `κ = 0.71` (recall `0.98`, adjusted after inspecting those 300 labels for subject-handle matching—making its benchmark agreement in-sample and optimistic). Both Ensemble and `D1` are co-reported throughout.
- **No unmeasured runtime claims:** Runtime CPU/RAM latency profiling (`run_j8_profiling.py` in `PREREG_v2.md`) was not executed (`INCOMPLETE.md`), so no runtime latency numbers are claimed.

---

## Repository Tags & Snapshots

| Tag | Branch | Purpose |
| :--- | :--- | :--- |
| **`prereg-v2`** | `v2-revision` (`3631432`) | Round 2 pre-registration lock (`PREREG_v2.md`, `AUDIT_v2.md`, `COMPUTE_PLAN_v2.md`) prior to Round 2 runs |
| **`v2-submission`** | `v2-revision` / `main` | Complete submission snapshot containing `PREREG.md`, `REPRODUCE.md`, `results/freeze.ok`, Elsevier & TMLR manuscripts, verification scripts, figures, and results |

---

## Repository Structure

- **Pre-registration, Governance & Reproduction**
  - `PREREG.md` — Primary pre-registration specification, §5 freeze checklist, and timestamped §6 protocol deviations
  - `results/freeze.ok` — Cryptographic parameter & corpus split freeze marker (`2026-10-29`, SHA-256 split lock + frozen DEV thresholds `0.60` lexical / `0.78` cosine)
  - `PREREG_v2.md`, `RESULTS_DELTA.md`, `INCOMPLETE.md` — Round 2 pre-registration, observed deltas, and honest status of completed (`J7`) vs. incomplete/queued extensions
  - `REPRODUCE.md` — Exact commands to reproduce primary analyses, Round 2 `J7` theory simulations, figures, macro audits, and LaTeX builds
- **Manuscripts & Automated Number Integrity**
  - `main_elsevier.tex`, `main_elsevier.pdf`, `supplementary_elsevier.tex`, `supplementary_elsevier.pdf` — Elsevier manuscript and supplementary material
  - `main_tmlr.tex`, `main_tmlr.pdf` — TMLR double-blind manuscript + appendix
  - `make_macros.py` → `macros.tex` — Generates every manuscript result macro directly from JSON outputs
  - `check_numbers.py`, `verify_ledger.py`, `knowledge_ledger.csv`, `number_audit.csv` — Machine-checked checks ensuring zero un-macroed numbers and 75/75 knowledge parity across both submission formats
- **Code, Corpus & Results (`corpus/`, `detectors/`, `results/`, `tests/`)**
  - `pipeline.py`, `jobs.py`, `gateway.py`, `llm_client.py`, `network_experiment.py`, `network_calibrate.py`, `paper_numbers.py`
  - `run_j7_theory.py` → `results/j7_theory_results.json`, `compile_numbers_v2.py` → `results/numbers_v2.json`
  - `results/numbers.json`, `results/agreement.json`, `results/network_calibration.json`, `results/freetext_entangled_summary.json`, and anonymized synthetic transcripts across `52` synthetic secrets (`20` DEV, `6` sanity, `26` TEST)

---

## Quick Verification

```powershell
# Verify corpus split & freeze marker
python -c "import os, json; assert os.path.exists('results/freeze.ok'); s=json.load(open('corpus/splits.json')); print('DEV:', len(s['semantic']['dev']), 'TEST:', len(s['semantic']['test']))"

# Regenerate macros and run automated paper checks
python make_macros.py
python check_numbers.py
python verify_ledger.py
```

See [REPRODUCE.md](REPRODUCE.md) for the full pipeline and LaTeX compilation instructions.
