# PREREG_v2.md
## Pre-Registration Protocol: Round 2 Confirmatory and Exploratory Suite

**Date:** 2026-11-13  
**Status:** Pre-specified before execution (Round 2)  
**Branch:** `v2-revision`  
**Git Tag:** `prereg-v2`  
**Master Random Seed:** `20261113`  

> [!IMPORTANT]
> All experiments, hypotheses, sample sizes, and analysis plans detailed below are designated as **Round 2, pre-specified before execution**. None of these protocols are retroactive to the original pre-registration (`PREREG.md`).

---

### 1. Frozen Baseline and Separation of Splits
1. **Corpus:** 52 synthetic secrets across 10 domains (`corpus/secrets_corpus.json`).
   - 20 DEV semantic secrets, 6 DEV identifier secrets.
   - 20 TEST semantic secrets, 6 TEST identifier secrets (total 26 TEST secrets).
2. **Strict Split Discipline:** Zero hyperparameter tuning or threshold calibration is conducted on TEST secrets. Any tuning or exploratory threshold sweep is restricted to DEV secrets.
3. **Gateway Thresholds:** Frozen study gateway thresholds remain locked at:
   - Lexical content word overlap: $\ge 0.60$
   - Embedding cosine similarity (`nomic-embed-text`): $\ge 0.78$

---

### 2. Job 1 (J1): Free-Text Entangled Secrets Evaluation (Primary New Experiment)

#### 2.1 Design & Secret Stratification
* **Secret Selection:** 16 held-out TEST secrets stratified by category and kind using fixed random seed `20261113`:
  - **Verbatim / Identifiers (all 6 TEST identifiers):** `id-acct-02`, `id-acct-04`, `id-case-01`, `id-case-02`, `id-email-03`, `id-email-04`.
  - **Semantic Facts (10 TEST semantic secrets):** `cred-01`, `cred-04`, `fin-02`, `fin-03`, `leg-01`, `leg-03`, `ma-04`, `ops-02`, `per-01`, `per-05`.
  - *(Total: 16 TEST secrets: 6 identifier, 10 semantic).*
* **Tasks:** `customer_service` (refund request) and `hr_onboarding` (background check).
* **Models:** `llama3.2:3b`, `qwen2.5:3b`, `gemma2:2b` (temperature $0.7$, low pressure).
* **Sample Size:** $16$ secrets $\times$ $2$ tasks $\times$ $3$ models = **$96$ paired episodes per defense**.
* **Entangled Secret Prompting:** The confidential secret and required task facts sit together inside a single unstructured incoming free-text email without separate dictionary or database fields.
* **Defenses Evaluated (strictly paired on seeds):**
  1. `B0` (No defense)
  2. `B2` (Generic privacy warning)
  3. `L1` (Exact match / lexical ID token filter)
  4. `L1+L2` (Two-layer semantic gateway)
  5. `B1` (Prompted summary-only)
  6. `B3` (Provenance tagging with `<CONFIDENTIAL>` strip)
  7. `B4-schema` (Static ACL stripping separate columns; ineffective on free text)
  8. `B4-taint` (Static ACL field-level taint withholding the entire email)
  9. `B6` (Secret-blind LLM judge filter)
  10. `B7` (Secret-blind PII regex)
  11. `B8` (Sentence-level offline regex/heuristic PII sanitization)

#### 2.2 Primary Endpoints & Hypotheses
* **Primary Leak Endpoint:** Hop-1 leak rate $T$ evaluated by the three-detector Ensemble (with 100% of ties resolved by Google Gemini $D_3$), co-reported with $D_1$ and $D_3$ alone.
* **Primary Utility Endpoint:** 5-item task checklist retention $U \in [0, 1]$.
* **Hypotheses:**
  - **HA1 (Leakage reduction):** `L1+L2` lowers $T$ relative to `B0` under the Ensemble, $D_1$, and $D_3$ with Holm-adjusted permutation $p < 0.05$.
  - **HA2 (Utility retention):** `L1+L2` is TOST-equivalent to `B0` within equivalence margin $\Delta = \pm 0.05$ (90% bootstrap CI).
  - **HA3 (Superiority over secret-blind baselines):** No secret-blind baseline (`B6`, `B7`, `B3`, `B8`) achieves both lower-or-equal $T$ and TOST-equivalent $U$ relative to `L1+L2`.

---

### 3. Job 2 (J2): Live Multi-Hop Chain with Gateway on Every Edge

#### 3.1 Design
* **Topology:** 6-agent linear communication chain ($0 \to 1 \to 2 \to 3 \to 4 \to 5$) using natural role-named prompts across the 16 stratified TEST secrets and the 3 local model families ($16 \times 3 = 48$ episodes per condition).
* **Conditions:**
  1. `B0` (Unfiltered baseline on all edges)
  2. `G-all` (`L1+L2` gateway filtering every edge $0\to 1, 1\to 2, \dots$)
  3. `G-first` (`L1+L2` on edge $0\to 1$ only; downstream unfiltered)
  4. `ROT` (`L1+L2` on edge $0\to 1$, cross-family `B6` judge on edges $\ge 2$)
* **Endpoints:**
  - Per-hop leak frequency $P(\text{secret in note } k)$.
  - **Live Persistence:** $P(\text{secret at hop 2} \mid \text{slipped hop 1})$ vs. control $P(\text{secret at hop 2} \mid \text{caught hop 1})$.
  - Mean infection size out of 5 downstream agents.
  - Final hop utility $U$.
* **Hypothesis HB:** Live rewrite persistence of slips under `G-all` exceeds caught controls, and filter rotation (`ROT`) reduces downstream persistence below `G-all`.
* **Stopping / Power Rule:** If fewer than 20 slips occur across conditions, explicitly state that statistical power is low.

---

### 4. Job 3 (J3): Statistics, Detector Hygiene & Automated Double Annotation
* Recompute all permutation tests using 100,000 resamples.
* Calculate secret-clustered bootstrap 95% CIs for all fold-changes.
* Implement **Automated Double Annotation** on all 300 blinded benchmark notes using two distinct local model families (`llama3.2:3b` and `qwen2.5:3b`) under the identical written human rubric at temperature 0. Compute pairwise Cohen's $\kappa$ and agreement with the human gold standard, explicitly labeled "Automated local judge validation".

---

### 5. Jobs 4–9: Secondary Probes & Profiling
* **J4 (Threshold Sweep):** Generate 10 hard negatives and 10 positives per secret across all 52 secrets; validate with cross-family agreement; evaluate precision-recall curves across cosine ($0.60\text{--}0.90$) and lexical thresholds.
* **J5 (Error Taxonomy of Slips):** Two cross-family judges assign standardized categories (paraphrase, negation/antonym, bullet/header repetition, abbreviation, identifier-only, translation/encoding, other) to all slipped notes; report inter-judge $\kappa$ and representative examples.
* **J6 (Adaptive Attacker):** Up to 20 query iterations per TEST semantic secret attempting to bypass `L1+L2` while preserving semantics; test against `L1+L2` and `ROT`.
* **J7 (Theory Check):** Formalize closed-form full-coverage outbreak floor $P_{\text{outbreak}} \approx 1 - (1 - T_{\text{gw}})^k$ and compare against 500-agent Monte Carlo simulations.
* **J8 (Gateway Profiling):** Measure CPU latency (ms/note), RAM, and API overhead across 200 notes for `L1`, `L2`, and `B6`.
* **J9 (Rubric-Based Usefulness v2):** Evaluate 1–5 scale LLM rubric usefulness on J1 episodes; test Spearman correlation with 5-item checklist $U$.

