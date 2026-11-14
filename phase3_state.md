# Phase 3 artifact state (DEV, post-rescore)

Date: 2026-10-29.  Status: pipeline.py reports all 14 steps DONE, but "done" here
means the artifact exists and passes the pipeline predicate; it does **not** mean every
number in it is safe to cite in the manuscript.  Read this before touching
`sec_persist_draft.tex`, `paper_numbers.py`, or `phase3_figures.py`.

## What is genuinely done

### Slip pools (both models)
- `results/slip_gen_v3_boundary_dev.jsonl` — llama3.2:3b, 1,600 rows, 20 secrets x
  4 variants x 20 trials.  Rescored with the study gateway (`gate_impl == "study"`,
  1,600/1,600).  Slip rate 0.1306 (209/1600), 95% CP [0.1145, 0.1481].  Slip_survived
  (gate-passed AND D1 leak) = 158.  Verified: `src_slip` and `src_survived` on every
  downstream row key back to this pool, 0 mismatches.
- `results/slip_gen_v3_boundary_qwen2.5_3b_dev.jsonl` — qwen2.5:3b, same universe,
  rescored with study gateway.  Slip rate 0.0631 (101/1600), 95% CP [0.0517, 0.0762].
  Slip_survived = 69.  Same back-link verification, 0 mismatches.
- Dedup is clean: each pool has exactly one row per `(secret_id, prompt_variant,
  trial_index)`, 1,600 distinct keys, no dupes.

### Hop-2 persistence (both models)
- `results/hop2_repass.jsonl` — llama3.2:3b, 1,600 rows, deterministic re-pass.
  Verified universe matches llama pool (1,600/1,600 row keys present and matched).
- `results/hop2_repass_qwen2_5_3b.jsonl` — qwen2.5:3b, 1,600 rows, same universe
  verification.
- `results/hop2_rewrite.jsonl` — llama3.2:3b, 458 rows (158 slip + 300 control).
  Condition field consistent with llama pool slip_survived (0 mismatches), universe
  matched.
- `results/hop2_rewrite_qwen2_5_3b.jsonl` — qwen2.5:3b, 219 rows (69 slip + 150
  control).  Same consistency check, 0 mismatches.
- Reports: `results/hop2_report.md` (llama) and `results/hop2_report_qwen2_5_3b.md`.
  These are the numbers to use for the persistence paragraph, subject to the
  "which model's pool is the conditioning universe" question below.

### H4 variant correlation
- `results/variant_correlation.json` exists, 6 variants, v5 auto_judge only 400/1600
  (stratified sample of 200 slips + 200 catches, so its miss_rate is sample-conditional
  and **must not** be presented as a population estimate without that caveat).
- Pairwise phi / McNemar table present for all 15 pairs.  Rotation matrix present.
  Worth a reader check before citation: the v1_frozen `caught` column is 1391, which
  matches the llama pool's `gateway_filtered == 1` count (1391), so at least v1 is
  conditioned on the llama study-gateway verdict, not the replica.

### Heterogeneity
- `results/heterogeneity.json` exists.  Per-pool llama rate 0.1306, qwen rate 0.0631.
  Secret-level ICC ~0.115 (llama) / ~0.126 (qwen).  Model-level block says n_models=2
  is descriptive only.  Per-secret agreement: llama zero-slip secrets 0, qwen 7 — worth
  a sentence if the paper leans on cross-model robustness.

## Where "done" is NOT the same as "citable"

### 1. Llama-conditioned vs qwen-conditioned persistence universe
The two hop-2 reports condition on different slip pools:
- llama report conditions on llama pool slip_survived (158), rho = 138/158 = 0.873.
- qwen report says `pool: 1600 rows, 209 hop-1 slips (13.1%)` and then reports
  rho = 63/69.  The `209` in the qwen report is the **llama** slip count, not the
  qwen pool's 101.  That looks like a template copy-paste from the llama report; the
  rho numerator/denominator (63/69) is qwen-conditioned and looks right, but the
  header line is misleading.  Do not quote the qwen report's header line; quote its
  rho line and re-derive the header if you re-run it.

### 2. v5 auto_judge coverage is incomplete
v5 is 400 rows, not 1,600.  That is a stratified sample by design, not a full
population score.  Any sentence that treats v5 miss_rate (0.145) as comparable to the
other variant rates without the sample caveat is wrong.  Until a full v5 pass exists,
present it as a sampled diagnostic, or drop it from the main H4 comparison.

### 3. The old replica numbers still exist in the file names and in PREREG history
The slip boundary pools now carry `gate_impl == "study"` and the rescored `slip` column,
and the old replica columns are preserved as `replica_*`.  That is correct and honest.
What is **not** correct is any downstream report, figure, or manuscript line that was
generated from the replica verdicts and has not been regenerated.  The quarantine
marker `results/gatefix_v1_quarantined` exists, and `results/stale_gatefix_20261027_210641/`
holds the old hop2_repass (312 rows) that was regenerated from scratch after the fix.
Before citing any hop-2 number, confirm its artifact mtime is after the rescore and that
`gate_impl` on its source pool row is `"study"`.

### 4. Diagnostic files exist but are not the manuscript products
- `results/slip_boundary_report.md` and the two `hop2_report*.md` files are debrief
  artifacts, not final paper text.
- `results/slip_pool_report.md` and `results/slip_pool_dev.jsonl` are from the earlier
  V3 DEV build (400 rows, replica-gated, gate_impl MISSING).  Do **not** cite these as
  the Phase-3 slip rate; they predate the study-gateway rescore.  The citable slip rate
  is in `slip_gen_v3_boundary_dev.jsonl` (llama) and its qwen counterpart.

## Quick pre-citation checks

Before you paste any Phase-3 number into the paper:

1. Open the artifact and confirm its source pool rows all say `gate_impl == "study"`.
2. Confirm the number's conditioning universe (llama pool vs qwen pool) matches the
   sentence you are writing.
3. If the number is a variant miss rate, confirm whether it is population-wide (n=1600)
   or a stratified sample (v5, n=400) and state which.
4. If the number is a slip rate, use the boundary pool rate (13.06% llama, 6.31% qwen),
   not the older 400-row pool rate.

## What is left in Phase 3, honestly

- A decision on which model's persistence number is the primary claim and which is the
  replication/robustness number, plus a fix for the qwen report header if you keep both.
- A decision on v5: full pass or explicitly sampled.
- A pass over every downstream figure/script that reads these artifacts and a check that
  it reads `slip`/`slip_survived`/`gateway_filtered` from the rescored columns, not the
  replica columns or the old 400-row pool.
- The manuscript revision that actually uses these numbers honestly.
