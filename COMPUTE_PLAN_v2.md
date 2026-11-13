# COMPUTE_PLAN_v2.md
## Round 2 Pre-Specified Compute and Scheduling Plan

**Date:** 2026-11-13  
**Branch:** `v2-revision`  
**Total Allocated Hours Budget:** 72.0 hours  
**Inference Hardware:** Local CPU inference via Ollama v0.40.16 + Google Gemini API (`gemini-2.5-flash` / `gemini-3.5-flash-lite`)  

---

### 1. Empirical Latency Measurements (3 Trials Per Model)
Measured via `http://localhost:11434/api/generate` at temperature 0.7:
- **`llama3.2:3b`:** $[14.13\text{s}, 3.94\text{s}, 3.89\text{s}]$ $\to$ warm mean: **$3.92\text{s}$** per call (cold start $14.13\text{s}$)
- **`qwen2.5:3b`:** $[13.14\text{s}, 3.85\text{s}, 5.87\text{s}]$ $\to$ warm mean: **$4.86\text{s}$** per call (cold start $13.14\text{s}$)
- **`gemma2:2b`:** $[12.02\text{s}, 4.45\text{s}, 4.24\text{s}]$ $\to$ warm mean: **$4.35\text{s}$** per call (cold start $12.02\text{s}$)
- **Overall local warm average:** $\approx \mathbf{4.38\text{s}}$ per LLM call.
- **Google Gemini API latency:** $\approx \mathbf{0.85\text{s}}$ per evaluation call.

---

### 2. Job Priority, Workload, and Time Estimates

| Job ID | Priority & Description | Episodes / Units | LLM Calls | Estimated Time | Time Box | Status |
|---|---|---|---|---|---|---|
| **J1** | **Free-text Entangled Secrets (Primary)**<br>16 stratified TEST secrets $\times$ 2 tasks $\times$ 3 models $\times$ 10 defenses | $96$ episodes / defense = $960$ episodes | $\approx 960$ LLM calls | $\approx 1.2$ hours | **4.0 hours** | Pending |
| **J2** | **Live Multi-Hop with Gateway on Every Edge**<br>6-agent chain $\times$ 4 conditions (B0, G-all, G-first, ROT) $\times$ 16 TEST secrets $\times$ 3 models | $192$ multi-hop episodes | $192 \times 5 = 960$ LLM calls | $\approx 1.2$ hours | **4.0 hours** | Pending |
| **J3** | **Statistics, Detector Hygiene & Automated Annotation**<br>100k permutations, clustered CIs, automated double-judge of 300 notes | 300 notes $\times$ 2 local judges + 100k bootstrap | $600$ judge calls + CPU stats | $\approx 0.8$ hours | **2.5 hours** | Pending |
| **J4** | **Threshold Curves & 52-Secret Hard Negatives**<br>10 hard negs + 10 positives per secret $\times$ 52 secrets | 1,040 sentences | Embeddings + fast sweep | $\approx 0.5$ hours | **2.0 hours** | Pending |
| **J5** | **Error Analysis of Slips**<br>Taxonomy labeling of slips across pools by 2 cross-family judges | $\approx 350$ slipped notes $\times$ 2 judges | $700$ judge calls | $\approx 0.9$ hours | **3.0 hours** | Pending |
| **J6** | **Adaptive Attacker (Exploratory)**<br>Up to 20 rewrites on TEST semantic secrets (black-box & white-box) | $16$ secrets $\times$ 2 modes $\times$ 10 queries | $\approx 320$ LLM calls | $\approx 0.5$ hours | **2.0 hours** | Pending |
| **J7** | **Theory Check (Closed-form vs. Monte Carlo)**<br>Closed-form floor derivation vs. 500-agent grid | Simulation grid | Pure NumPy / Math | $\approx 0.2$ hours | **1.0 hour** | Pending |
| **J8** | **Gateway Cost & Latency Profiling**<br>ms per note for L1, L2 embedding, B6 across 200 notes | 200 notes | Local CPU + Profiler | $\approx 0.3$ hours | **1.0 hour** | Pending |
| **J9** | **Usefulness v2 (Rubric LLM Scoring)**<br>1-5 scale rubric on J1 episodes by cross-family judge | $960$ notes | $960$ judge calls | $\approx 1.2$ hours | **3.0 hours** | Pending |
| **J10** | **Optional Extensions (if budget permits)**<br>(a) 7B-8B model, (b) code review task, (c) dense network | Subsets | Contingent | TBD | **8.0 hours** | Optional |

**Total Estimated Primary Time (J1–J9):** $\approx 6.8$ hours (well within the 72.0 hour budget).

---

### 3. Execution & Checkpointing Strategy
1. All local generations use the established SQLite call cache (`results/llm_cache_v2.sqlite3`) keyed by `(provider, model, prompt, temperature, seed)`.
2. All primary headline detector tie-breaking and evaluations requiring Gemini use Google Gemini API with automated exponential backoff and persistent resume logging (`results/d3_google_v2.jsonl`).
3. If an API quota is reached, the runner writes an intermediate checkpoint, records the timestamp, and waits for quota recovery rather than falling back to local models for primary headline metrics.
