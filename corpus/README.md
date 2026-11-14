# Secret corpus (Phase 1)

Built by `python make_corpus.py` from the hand-authored `corpus_data.py`.
Outputs: `secrets_corpus.json` (52 records) and `splits.json` (the frozen DEV/TEST split).

## Contents

| | count | per record |
|---|---|---|
| semantic secrets | **40** (8 categories x 5: medical, financial, hr, legal, ma, personal, credentials, ops) | `text`, `ident` (subject identifier), 4 paraphrases at graded distance, 1 abbreviated, 1 vague, 3+ same-template **hard negatives**, 3+ same-topic **harmless** sentences, 28 **unrelated** typical notes |
| identifier secrets | **12** (3 formats x 4: `CASE-XXXXXXXX`, email-like, numeric account ID) | `text`, `ident`, 5 encoding **variants**, 3+ hard negatives, 3+ harmless, 28 unrelated notes |

Everything is synthetic: invented people, invented company names, `.example` email domains
(reserved by IANA, non-routable). Nothing here is a real person, account, case or company.

## Paraphrase grading (p1 = near ... p4 = oblique)

* **p1** near — same claim, reworded slightly
* **p2** medium — same claim, clearly different syntax
* **p3** far — avoids the secret's own vocabulary (no shared key terms)
* **p4** oblique — hint/implication only ("q0k will probably need dialysis before long")

Hard negatives share the *template frame* but state a **different** fact (several are minimal
pairs — one term flipped — which is exactly where a keyword detector should be challenged).
Harmless sentences are on the same topic but carry no confidential content. Unrelated notes are
instantiated per secret: for semantic secrets they mention the subject identifier (so the
identifier-exposure outcome is measurable everywhere); for identifier secrets they use a neutral
handle ("the customer") because they must contain no part of the secret.

## Frozen split (`splits.json`)

* 40 semantic -> DEV 20 / TEST 20, stratified by category (2–3 per category to DEV).
* 12 identifier -> DEV 6 / TEST 6 (2 per format).
* `corpus_sha256` binds the split to this exact corpus file; tests fail if the corpus is edited
  after the split is frozen (`tests/test_corpus.py::test_split_bound_to_corpus_hash`).
* **Tuning rule:** thresholds, prompts, filters and analysis choices may use DEV only. TEST is
  evaluated once, after freezing. The split has not been regenerated since first creation.

## Measured properties of the legacy keyword detector (D1) on this corpus

These are *measurements*, printed by the test suite (`pytest -s tests/test_detector.py`), not
targets:

* D1 paraphrase recall by distance: **p1 0.90, p2 0.625, p3 0.275, p4 0.15**
  → the keyword detector is nearly blind to far/oblique paraphrases. This is one of the
  motivations for the independent detector stack (Phase 2, W3).
* D1 false positives on the 120 hard negatives: **35/120** (minimal pairs share the frame
  vocabulary). Reported, not tuned away.
* D1 keyword derivation (`detector.keywords_for`) is mechanical: secret content words minus
  words appearing in that secret's negatives, with a documented two-step fallback (hard
  negatives are held out when they would erase all signal). The same algorithm runs for every
  DEV and TEST secret — no per-secret hand-picking.

## Known limitations (stated, not hidden)

1. Unrelated notes come from a 28-template pool instantiated per secret, rather than 20+
   hand-written unique notes per secret. They are unique per secret but share a common
   skeleton; this is documented here and in `AUDIT.md` rather than presented as 1 040
   independent hand-written notes.
2. The corpus is English-only; the original study's Spanish/German attack strings live in
   `gateway_eval.py` and remain an appendix experiment.
3. Identifier secrets make content leak and identifier exposure largely coincident; the two
   outcomes are only cleanly separable on the 40 semantic secrets.
