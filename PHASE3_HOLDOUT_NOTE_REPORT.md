# Phase 3 hold-out note report

## What was checked

After the V3 backward hookwrap run on `gemma2:2b` (DEV only, 6 secrets, 20 trials each
except fin-05 with 11), I inspected the 111 generated notes and their two gateway verdicts
(`redact_this_note_catches` vs `redact_note_catches`) directly, row by row, rather than only
looking at the totals.

## Result

- 0 slips out of 111 notes.
- `redact_this_note_catches = 111`, `redact_note_catches = 111`, disagree = 0.
- Every note is a near-verbatim restatement of the secret sentence.
  - `med-03` and `fin-05` produced the identical sentence on every single trial.
  - The rest produced small surface paraphrases ("disclosed this status" vs "disclosed this
    information" vs "has not informed their employer"), but none of them escaped the lexical
    or cosine branch at `threshold 0.78`.

## Interpretation

This is a hold-out sanity check on the **instrumentation**, not on the defended channel:

1. The two-gate hookwrap is working as intended: both calls receive the same note, both verdicts
   are recorded per note, and the file is checkpointed by `(secret_id, model, trial_index)` so a
   kill/resume does not duplicate rows.
2. The deterministic L2 gateway (lexical 0.60 + nomic-embed cosine 0.78) catches the obvious
   restatements.  That is expected and is not, by itself, the persistence claim.
3. `gemma2:2b` is not a strong enough parole source to produce slips in this probe.  The notes
   it generates are too close to the secret text for the gateway to miss them, so this run cannot
   supply the slip budget that the persistence claim needs.

## Conclusion and next step

The correct conclusion from this probe is: **this DEV-only gemma2:2b slice is the first
instrumented diagnostic of the two-gate comparison and the zero-slip result is a property of the
probe, not of the defended channel**.

The actual hop-1 slip observations for H3 must come from a stronger parole source.  Before
spending the `slip_target_n = 300` slip budget on the full Tier-A run, the next step is to
re-run the V3 pipeline on `llama3.2:3b` and `qwen2.5:3b` with the same prompt and checkpoint
scheme, and only then collect the slip candidates that the new `redact_note` gate must be
evaluated on.

## Artifacts

- `results/slip_gen_v3_dev.jsonl` — 111 rows, one per generated note, both verdicts stored.
- `results/embed_cache_slipgen.jsonl` — nomic-embed-text cache used by the L2 cosine rule in
  this run.
- `PHASE3_SLIP_GATE_NOTES.txt` — the raw notes + verdicts listing that this report summarizes.
- `slip_gen.py` — the V3 hookwrapped hop-1 slip pipeline used to produce these notes.
