# RUNLOG.md
## Round 2 Execution Log

**Branch:** `v2-revision`  
**Master Random Seed:** `20261113`  
**Ollama Version:** `0.40.16`  

---

### Step 0: Initial Setup and Auditing (2026-11-13 07:10 UTC+5:30)
* Created git branch `v2-revision`.
* Saved package locks to `requirements.lock`.
* Saved Ollama model digests to `MODEL_DIGESTS.txt`.
* Completed benchmark audit and documented in `AUDIT_v2.md`:
  - Confirmed Outcome 1 ($D_1$ content leak) was never tuned on the 300 blinded benchmark notes ($\kappa = 0.7106$).
  - Evaluated Outcome 2 ($D_1$ identifier exposure) with subject handle refinement ($\kappa = 0.7945$) vs without refinement ($\kappa = 0.2429$).
* Measured empirical LLM inference latency: warm mean $\approx 4.38$s/call on CPU; Gemini API latency $\approx 0.85$s/call.
* Formulated and committed `COMPUTE_PLAN_v2.md`.
* Tagged pre-registration baseline: `git tag prereg-v2` at commit `3631432`.

---

### Job 7 (J7): Theory Check & 500-Agent Outbreak Simulation Re-run
* **Script:** `run_j7_theory.py`
* **Execution:** Ran closed-form comparison and 200 Monte Carlo simulation runs on 500-agent networks (Erdos-Renyi and Barabasi-Albert, $\langle k \rangle = 4$) under both exploratory ($T_{\text{gw}} = 0.017$) and TEST ($T_{\text{gw}} = 0.073$, $T_{\text{src}} = 0.346$) parameter regimes.
* **Findings:**
  - Closed-form outbreak floor $P_{\text{floor}} = 1 - (1 - T_{\text{gw}})^k$ at degree $k=4$:
    - Early exploratory ($T=0.017$): $6.63\%$ (matches the 2–9% early range).
    - TEST headline ($T=0.073$): $26.16\%$ (explains why the floor moves from ~7% to ~26%).
    - Detector $D_1$ ($T=0.292$): $74.87\%$.
  - 500-Agent Monte Carlo Outbreak Floor at full protection ($p=1.0$):
    - Early parameter regime ($T=0.017$): $P(\text{outbreak}) = 0.085$ ($8.5\%$).
    - TEST parameter regime ($T=0.073$): $P(\text{outbreak}) = 0.250$ ($25.0\%$).
* **Output:** Saved full dataset and degree grid to `results/j7_theory_results.json`.

---

### Job 1 (J1): Free-Text Entangled Evaluation (Execution in Progress)
* **Script:** `run_j1_freetext.py`
* **Design:** 16 held-out TEST secrets (6 identifiers, 10 semantic) $\times$ 2 tasks (`customer_service`, `hr_onboarding`) $\times$ 3 models (`llama3.2:3b`, `qwen2.5:3b`, `gemma2:2b`) = 96 paired base episodes.
* **Defenses (11 arms):** `none`, `warning`, `gateway_l1`, `gateway`, `b1_summary`, `b3_tag`, `b4_schema`, `b4_taint`, `b6_llm_filter`, `b7_regex`, `b8_heuristic`.
* **Endpoints:** Task checklist usefulness $U$, $D_1$ keyword/ID, $D_2$ NLI DeBERTa-v3, $D_3$ Google Gemini API judge, majority-vote Ensemble.
* **Checkpoints:** Appending to `results/j1_freetext_transcripts.jsonl`.
