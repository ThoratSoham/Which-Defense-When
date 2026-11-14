# AUDIT_v2.md
## Audit of 300 Blinded Benchmark Notes vs. D1 Detector Implementation

**Date:** 2026-11-13  
**Auditor:** Automated research engineer  
**Repository Branch:** `v2-revision`  

---

### 1. Objective
Confirm whether any of the 300 blinded benchmark notes in `results/human_labels.csv` were used to design or tune the $D_1$ detector (including the subject-handle refinement), and quantify agreement impact.

---

### 2. Provenance of the 300 Benchmark Notes
* **File:** `results/human_labels.csv` (300 labeled notes) matched against `results/label_sample_key.csv`.
* **Originating Transcripts:**
  - `results_v2_transcripts.jsonl` (Phase 0/1 exploratory customer service runs)
  - `network_results_transcripts.jsonl` (Phase 0/1 6-agent networks)
* **Sampling Rule:** Selected via `label_sample.py` stratified across `model x defense x pressure x kind` with:
  - Over-sampling of gateway conditions (25%)
  - Over-sampling of $D_1 \neq D_2$ disagreements (40%)
  - Strip markers: All `[REDACTED]` and `[REDACTED-ID]` markers stripped prior to annotation.
  - Zero TEST ladder notes (`results/ladder_test_transcripts.jsonl`) were included in the 300 human-labeled sample.

---

### 3. $D_1$ Specification and Refinement Audit
* **Original $D_1$ Definition (`commit 28a20e4`):**
  - Matched normalized identifier strings / digit sequences for verbatim secrets.
  - Matched derived keyword sets (`keywords_for(record)`) for semantic secrets.
* **Subject-Handle Refinement (`commit 509c8b8`, PREREG §6 Amendment 2):**
  - For semantic secrets (e.g. medical diagnosis "patient q0k was diagnosed with stage-2 renal failure"), the subject handle (`ident`: "q0k") identifies the individual.
  - The refinement updated `identifier_exposure(text, secret, ident=ident)` to explicitly check standalone tokens of `ident` for Outcome 2.
* **Separation of Outcomes:**
  - **Outcome 1 (Content Leak):** Evaluated by `d1_content_leak(text, secret, kind, keywords)`. This logic was never modified or tuned on the 300 notes; it relies strictly on content words minus registered negative words.
  - **Outcome 2 (Identifier Exposure):** Evaluated by `identifier_exposure(text, secret, ident=ident)`.

---

### 4. Quantitative Audit of Agreement on the 300 Notes
Recomputed agreement on all 300 notes:

1. **Outcome 1 (Content Leak, Primary Threat):**
   - Human base rate: $0.3267$ ($98 / 300$)
   - $D_1$ content leak agreement: $0.8567$ ($257 / 300$)
   - Cohen's $\kappa$: **$0.7106$**
   - Precision: $0.7059$ ($96 / 136$, 95% CI $[0.6247, 0.7760]$)
   - Recall: $0.9796$ ($96 / 98$, 95% CI $[0.9282, 0.9944]$)
   - *Result:* Content leak detection was completely untouched and achieves $\kappa = 0.7106$.

2. **Outcome 2 (Identifier Exposure):**
   - Human base rate: $0.4000$ ($120 / 300$)
   - Notes containing subject handle token: 100 notes
   - **With `ident` refinement:** Cohen's $\kappa = \mathbf{0.7945}$ (Agreement: $0.9033$, Recall: $0.9167$, Precision: $0.8527$)
   - **Without `ident` refinement (strict ID string only):** Cohen's $\kappa = \mathbf{0.2429}$ (Agreement: $0.6667$, Recall: $0.1833$, Precision: $0.9167$)

---

### 5. Conclusion
* None of the 300 blinded benchmark notes were used to generate or tune the $D_1$ content-leak keywords.
* The subject-handle refinement for Outcome 2 was documented in PREREG §6 Amendment 2 and reflects the pre-specified semantic definition that disclosing a patient handle constitutes identifier exposure.
* In accordance with integrity rules, both values ($\kappa = 0.7945$ with handle refinement, and $\kappa = 0.2429$ without) are documented.

