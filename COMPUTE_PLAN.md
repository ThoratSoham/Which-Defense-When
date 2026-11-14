# COMPUTE_PLAN.md — calls, wall-clock, and priority order (Phase 0)

Derived from the measurements in `AUDIT.md` §8. Nothing here is run yet; §6 lists what I need
approved before I launch anything. All wall-clock figures are *measured rates × planned calls*,
not guesses, and every job I start will be checkpointed so a >6 h job can be split or resumed.

## 1. Measured unit costs

| Unit | Measured cost |
|---|---|
| One handoff call, 3 B-class (`llama3.2:3b`, `qwen2.5:3b`, `gemma2:2b`) | **45–60 s** (3.9–4.8 tok/s) |
| One handoff call, 7–8 B-class (`qwen2.5:7b`, `llama3:latest`) | **150–200 s** (1.8–3.0 tok/s); 7 B leaves only 0.95 GB RAM free |
| One 3-agent chain episode | 3 calls ≈ **2.5 min** (3 B) / **8 min** (7 B) |
| One 10–12-agent tree episode (11–12 edges) | ≈ **10 min** (3 B) / **35 min** (7 B) |
| Embeddings (`nomic-embed-text`) | 8.5 sent/s batched, 2.1 s fixed cost per single call → **cache everything, batch, unload chat model first** |
| Simulator / statistics / figures | seconds to minutes (CPU) |

**Planning constants:** `C3 = 50 s/call`, `C7 = 180 s/call`, chain episode = 3 calls,
12-agent episode = 11 calls. One 24 h day of 3 B running ≈ **1 700 calls** ≈ 560 chain episodes.

## 2. Calls and wall-clock per phase

| Phase | Work | LLM calls | Local wall-clock (3 B) | API cost |
|---|---|---|---|---|
| 1 | Config, cache, job runner, tests, 40-secret corpus, DEV/TEST split, 2nd task | ~0 (corpus templated; paraphrase drafting can use API) | **~2 h CPU** | 0 |
| 2 | Detector stack: D1 (free), D2 NLI (CPU), D3 local judge subset, D3 API judge full set | local: 800–1 000 judge calls ≈ **14 h**; API: ~4 000 judge calls ≈ 30–60 min at free-tier rates | 14 h + ~1 h CPU | free tier, ~4 k calls |
| 2 | Human labelling (you) | — | **~1 h of your time** for 300 notes (I'll tell you exactly when) | — |
| 6.1 | Simulator unit tests (complete graph/tree analytics, R0, convergence, seeds) | 0 | **<1 h CPU** (DONE 2026-10-25: 11 tests, exact DP + closed forms, all pass) | ✅ |
| 6.2 | Out-edge correlation — **re-analyse existing `star6` transcripts (4 sibling notes/episode from agent 1: topology is 0→1→{2,3,4,5}, not "5 notes from agent 0" as first written; corrected after inspecting the data)**; plus optional small new run | 0 (existing data) / ~500 calls if new run | **<1 h** (DONE 2026-10-25, no new calls needed) / +7 h | ✅ |
| 3 | Replay logged hop-1 notes through gateway (mechanical persistence) | 0 | ~1 h (embeddings cached) | — |
| 3 | Enriched slip pool: 40 secrets × 15 graded-paraphrase notes = 600 calls | 600 | **~8 h** (needs your OK, >6 h) | — |
| 3 | Hop-2 on each slip: deterministic re-pass (0 calls) + LLM rewrite (300 calls) | 300 | **~4 h** | — |
| 3 | Gateway variants miss-correlation + heterogeneous-gateway hops (400 calls) | 400 | ~6 h | — |
| 3 | Heterogeneity model, bootstrap, sensitivity surface | 0 | ~2 h CPU | — |
| 4 | Core ladder on **3 original models × 2 tasks × 4 defenses × 2 kinds × 2 pressures × 30 eps** = 3 × 1 440 × 2 tasks | **8 640** | **~120 h** (5 days) | — |
| 4 | + one 4 B model, one task (same grid, n=30) | 1 440 | ~32 h | — |
| 4 | + one 7–8 B model, reduced n (see Tier B) | 1 440 | ~72 h (3 days) | — |
| 4 | + free-API frontier model, reduced n (n=20, 1 task, 4 defenses × 2 kinds × 2 pressures) | 480 | 0 | free tier, ~480 calls ≈ 1–2 h with rate limits |
| 5 | 6 new baselines (B1, B3, B4, B5, B6, B7) × 2 kinds × 2 pressures × 30 eps × 3 calls, **1 model, 1 task** | 2 160 | **~30 h** | — |
| 5 | same, × 2 more models (Tier B) | 4 320 | ~60 h | — |
| 5 | Usefulness judge: extraction (free) + LLM rubric on ~2 000 final notes | 0 (API judge) | — | free tier |
| 6.3 | Real 10–12-agent nets: 3 topologies × 2 defenses × 30 eps × 11 calls, **1 model, 1 source position** | 1 980 | **~27 h** | — |
| 6.3 | + second source position (hub vs random) / 2nd model (Tier B) | 1 980–3 960 | 27–55 h | — |
| 6.4 | Real partial protection: 4 levels × 2 placements × 30 eps × 11 calls | 2 640 | **~37 h** (Tier B) | — |
| 7–8 | Numbers pipeline, macros, consistency check, restructure, bibliography | 0 | ~6 h CPU | — |

**Tier A total (local):** ≈ **160–190 h ≈ 7 days** of continuous 3 B running, plus ~3 h/day of
CPU analysis, plus ~5 k free-API calls. **Everything Tier B on top: ≈ +250 h (≈10 days).**

## 3. Where the time goes, and the honest options

The full wish-list (W1–W7 as written) is ~450 local GPU-free hours. Three levers, in order of
how much they cost you scientifically:

1. **n per cell.** Pre-registered primary cells keep n = 30; secondary cells (second task,
   non-focal defenses) drop to n = 15 with CIs reported. Saves ~40 %.
2. **Model count.** Full ladder on 3 original models + 1 new 4 B model; the 7–8 B model runs a
   *reduced* grid (n = 15, customer-service task only). Saves ~30 % and avoids 7 B's 0.95 GB
   headroom problem.
3. **Defense count per model.** The 6 new baselines run on the fastest model only; the two
   headline baselines (B4 ACL, B1 summary-only) get repeated on a second model for robustness.

What I will **not** do to save time: lower n below pre-registered power, drop the DEV/TEST split,
reuse the same notes across conditions, or tune on TEST.

## 4. Priority order (which run first, and why)

Fail-early ordering: anything that could invalidate later work comes first, and the cheapest
evidence that could change the paper's claims comes before the expensive grid.

| Tier | Job | Why first |
|---|---|---|
| **A1** | Phase 1 infra + 40-secret corpus + DEV/TEST split → **you review a sample** | everything else depends on it |
| **A2** | Phase 2 detector stack + blinded labelling tool → **you label** | re-scoring changes *every* number; must happen before new experiments |
| **A3** | Phase 6.1–6.2 simulator tests + message-passing/out-edge analysis | cheap; if the simulator is wrong, Phase 3/6 budgets change |
| **A4** | Phase 3 persistence (replay → enrichment → hop-2 → variants) | the headline "0.95 from 20 relays" is the weakest claim per W2 |
| **A5** | Free-API replication (defense ladder + relay, reduced n) | hours, not days; gives the W1 frontier-class evidence early |
| **A6** | Phase 5 baselines on 1 fast model + usefulness metric | W6; also cheap relative to Phase 4 |
| **A7** | Phase 6.3 real 10–12-agent networks (1 model) | W4; validation evidence for the network claims |
| **A8** | Phase 4 scale: 3 original models with the new corpus, 2nd task, n=30 | the big grid — run once the detector and protocol are frozen |
| **B1** | Phase 6.4 real partial-protection experiment (37 h) | strongest check of herd immunity, but Tier B by budget |
| **B2** | 7–8 B local model full grid (72 h) | W1 depth; run reduced first, extend only if it behaves |
| **B3** | Baselines on 2 more models, 2nd source position, optional B8/B9 | robustness breadth |
| **B4** | Full local D3 judge on all ~4 000 notes | API judge covers Tier A |

Every job is written to run in **≤6 h slices with CSV/JSONL checkpoints** (the existing scripts
already skip completed cells; I will harden that in Phase 1), so nothing needs your attention
mid-run and any slice can be resumed. I will ask before starting any single *uninterrupted*
job above ~6 h (rule 7).

## 5. Model schedule (RAM discipline)

- One model at a time, model-by-model (never interleaved), `keep_alive: 30m`, `num_ctx 2048`.
- Set `OLLAMA_MAX_LOADED_MODELS=1` on the **server** — this requires restarting the Ollama
  service, which I will not do without your go-ahead (it may interrupt anything else you run).
- Embeddings: pre-computed and cached before each chat-model batch; unload the chat model
  (`keep_alive: 0`) before bulk embedding.
- New models to pull (53 GB free): `gemma3:4b` (~2.9 GB, different family) and, as candidates,
  `qwen2.5:7b-instruct-q4_K_M` (already have) / `llama3.1:8b`. **Benchmark each after pulling and
  re-confirm with you before committing it to a grid** — if the 7–8 B tier leaves <2 GB free or
  decodes <2.5 tok/s, I drop to the 4 B tier and say so in the paper.
- `gemma4:latest` (9.6 GB) is **excluded** until we test it: loading it plus anything else will
  swap on this machine.

## 6. What I need from you before launching (check-in 1)

1. **Approve Tier A** (~7 days of continuous local running) and the ordering in §4 — or tell me
   which of A5–A8 to demote.
2. **Confirm the n=15 option for secondary cells** (§3) or insist on n=30 everywhere (+~10 days).
3. **Permission to restart the Ollama service once** with `OLLAMA_MAX_LOADED_MODELS=1` (and to
   `git init` this repo, per AUDIT §10.2).
4. **The LaTeX source** (AUDIT §10.1) — Phase 7–8 is blocked without it.
5. **Provenance of `annotator2_sheet.csv`** (AUDIT §10.3) — affects whether Phase 2's agreement
   analysis can cite a second annotator at all.
6. Anything in §2 you want re-scoped before I write `PREREG.md`.
