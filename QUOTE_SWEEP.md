# 0.95-quote sweep inventory (Phase 8)

Correction 2026-10-29: the WORKING manuscript is `main_draft.tex` (701 lines,
6 PENDINGs, compiled to main_draft.pdf). `main.tex` (603 lines, 0 PENDINGs)
is the frozen original — do not revise it. Re-check line numbers after the
persistence splice (main_draft lines 323-424 move).

Relay rate replacement: rho_rewrite = 0.873 (158 relays, CI 0.813-0.917),
in place of 0.95 (20 relays). Simulation floors after the re-run:
per-edge slip 0.02-0.09 (correlated 0.04-0.09); per-model at full coverage
0.00 gemma / 0.09-0.12 llama / 0.27-0.38 qwen (legacy rho re-run reproduces
the published 0.09-0.14 / 0.24-0.32 exactly).

## main_draft.tex — edit these

| line | current | action |
|---|---|---|
| 64  | abstract: "relayed past it again 19 times out of 20"; "2 to 12% remains" | rewrite relay as 138/158 = 0.87; reconcile floor range with sim re-run |
| 82  | contributions: "0.95, from 20 relays" | 0.873 from 158 relays, cite sec:persist |
| 448 | fig:herd caption: "gateway bar ... 0.02 to 0.12 at full coverage" | new floor 0.02-0.09 (slip) / 0.04-0.09 (correlated) |
| 456 | method: "per-edge slip ... (relay rate 0.95)", "probability 0.065" | relay 0.873; re-derive q_ev if sim re-run changed it |
| 475 | results: floors "0.02 to 0.12 and 0.03 to 0.11"; per-model "up to 0.32" | reconcile with sim_final re-run numbers |
| 524 | conclusions: "0.95, 20 relays" | 0.873, 158 relays |

Lines 327/386/390/393 (relay 0.95 / PENDING markers) are INSIDE the
persistence subsection 323-424 and are removed by the sec_persist_draft
splice itself.

## Do NOT touch

- line 220 (kappa 0.95), 258 (ladder "0.95 / 1.26 / 2.78"), 430 (Monte-Carlo
  variance 0.02), any `\figbox{...}{0.95}` width argument.
- `main.tex` entirely (frozen original).
