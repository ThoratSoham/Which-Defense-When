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
