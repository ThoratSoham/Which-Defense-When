# Phase 3 status (transient work log, not a committed deliverable)

Date: 2026-10-25.

## What ran successfully

- `replay_fp.py results_v2_transcripts.jsonl` — replayed the existing 351 unique
  no-defense verbatim handoff notes through the live gateway (L2 threshold sweep
  0.70/0.75/0.78/0.80/0.85) with a registered medical secret + unrelated ID.
  Result: 0/351 over-blocked at every threshold; Wilson 95% CI upper bound 0.011
  at all of them. This is the Phase-3 "mechanical persistence" piece minus the
  enriched slip pool: the authoritative gateway with `threshold=0.78` did not
  over-block any harmless note in this sample.

- `analyze_labels.py` — re-ran the Phase-2 agreement analysis on the 300 human
  labels. Re-confirmed before starting Phase 3:
    - content leak: D1 0.71/0.98 (κ 0.71), D2 0.47/0.21 (κ 0.11),
      local D3 0.43/0.45 (κ 0.15), ensemble 0.70/0.63 (κ 0.51),
      google D3 n=37 0.63/1.00 (κ 0.63, biased subset).
    - identifier exposure (D1 only): 0.85/0.92 (κ 0.79, AC1 0.81).
    - intra-annotator: 7 overlapping notes, κ 1.00 (reported as intra, not inter).
    - writes results/agreement.json.

- `rescore.py` + `stats_ladder.py` — re-derived hop-1 T on the existing transcripts:
    - none 0.695 [0.647,0.744], warning 0.644 [0.594,0.694],
      gateway_l1 0.317 [0.269,0.364], gateway 0.017 [0.006,0.031].
    - all pairwise Holm-corrected p ≤ 0.0012 except none-vs-warning (p=0.1538).
    - This is the same ladder from the prior turn, reproduced from the transcripts
      (not recalled).

- `results/human_labels.csv` — verified 300 labelled rows present, two columns
  (content_leak, identifier_exposure), annotator tag A1.

## What blocked / timed out

- `gateway_eval2.py --llm llama3.2:3b --trials 12` timed out twice at the
  120-second tool limit. A minimal 3-trial, single-threshold, single-config run
  (`base`, thr=0.70, trials=3, with a tiny harmless file written to disk) was
  started under a 180-second wrapper and **returned empty** (no stdout captured,
  no pr_table.csv / fig_pr_curve.png / embed_cache written). The return code was
  0, but nothing was produced, so it is more likely the process still blocked on
  the first embedding/LLM call than that it completed silently.

  Likely cause is not the math: it is that `gateway_eval2.py` builds a fresh
  `OllamaEmbedder` and a fresh llama3.2:3b judge for every config × threshold
  × trial, and on this machine each llama3.2:3b call is ~10–15 s and each batch
  embedding call has fixed overhead. With the default 6 configs × 6 thresholds ×
  12 trials that is far more than a 2-minute slice. This is exactly the
  "checkpoint each ≤6 h slice" situation from COMPUTE_PLAN §4, not a code error.

- The long-running background jobs from the prior turn (full-pool local D3 judging,
  Google free-tier D3) were not re-launched here. The existing partial verdict set
  is enough for the agreement table; the full D3 run is Tier A/B work, not a
  Phase-3 dependency.

## What that means for the persistence claim

The part of H3 that can be built from existing transcripts plus the live gateway
is now done:

- Mechanical persistence baseline: existing harmless verbatim notes do **not** get
  over-blocked by the L2 gateway at the frozen threshold. That is the "gateway is
  not just censoring the whole channel" check.
- The definitional split required by PREREG §1 H3 is already documented:
  deterministic re-pass of identical text vs next-agent rewrite then gateway must
  be reported separately, because the deterministic case is partly mechanical.

What is **not** done and is the actual Phase-3 deliverable still missing:

1. The enriched slip pool (40 secrets × graded paraphrase notes) and the ≥300
   slip observations at hop 1, with the secret/model random effects and the
   leave-one-secret-out check.
2. Hop-2: deterministic re-pass of identical post-gateway text, then gateway
   again, separately from the LLM-rewrite-then-gateway condition.
3. Gateway-variant miss correlation (heterogeneous gateways, H4), which depends on
   having multiple gateway variants actually run and judged.
4. Free-API replication of the defense ladder (the small-n OpenRouter/Gemini run
   that gives the frontier-class evidence early).

## Recommended next move

The honest state is: Phase 3's computing-intensive pieces (enriched slip pool,
hop-2 rewrite judging, gateway-variant correlation, free-API ladder replication)
all need real model calls and will not finish in a 2-minute interactive slice.
Before launching any of them, I would re-confirm two things that the audit left
open and that Phase 3's design depends on:

1. The 40-secret corpus already exists in `corpus/secrets_corpus.json` and
   `corpus/splits.json` (Phase 1), and the DEV/TEST split is frozen. Phase 3's
   slip pool and the hop-2 persistence estimate both need a defined secret set to
   generalise across, so I should re-read those files and confirm the split before
   generating paraphrases against it.
2. Whether to run `gateway_eval2.py` as a real checkpointed job (write
   pr_table.csv per config/threshold slice, resume by reading the existing CSV)
   or to skip the full sweep for now and only use the single-threshold replay
   result we already have (0/351 over-blocked at 0.78).

If you want, I can:
- re-read `corpus/secrets_corpus.json` / `corpus/splits.json` and report the
  actual secret count, kind split, and DEV/TEST boundary before building the slip
  pool; or
- start the enriched slip pool as a checkpointed 6-hour slice against the frozen
  DEV secrets only, which is the fail-early version (if the paraphrase+rewrite
  pipeline has a bug, it shows up on DEV before any TEST slip is spent).

I have not edited any Phase-3 source files yet; nothing above wrote new experiment
code, only ran existing scripts and wrote this status note.
