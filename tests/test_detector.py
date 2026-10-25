"""D1 detector tests: sensitivity on secrets/paraphrases, specificity on hard
negatives and unrelated notes. These pin down current behaviour — including the
places where D1 is blind — so Phase 2's independent detectors can be compared
against a fixed baseline.

D1's keyword set per secret is derived mechanically (secret content words minus
words that appear in that secret's negatives); see detector.keywords_for()."""
import json, os, pytest, detector

CORPUS = "corpus/secrets_corpus.json"


@pytest.fixture(scope="module")
def recs():
    if not os.path.exists(CORPUS):
        pytest.skip("corpus missing")
    return json.load(open(CORPUS, encoding="utf-8"))["records"]


def semantic(recs):
    return [r for r in recs if r["kind"] == "semantic"]


def identifiers(recs):
    return [r for r in recs if r["kind"] == "identifier"]


def test_keywords_derived_for_every_secret(recs):
    for r in semantic(recs):
        kw = detector.keywords_for(r)
        assert kw, f"{r['id']}: no discriminative keyword survives the negatives"
        # the derived set must not contain the subject identifier
        assert r["ident"].lower() not in kw


def test_original_renal_keywords_reproduced(recs):
    """Continuity: med-01 is the original secret; its derived keyword set must
    contain the paper's keyword family."""
    r = next(x for x in recs if x["id"] == "med-01")
    kw = detector.keywords_for(r)
    assert {"renal", "failure"} <= set(kw) or "renal" in kw


def test_exact_secret_is_caught(recs):
    for r in semantic(recs):
        kw = detector.keywords_for(r)
        assert detector.d1_content_leak(r["text"], r["text"], "semantic", keywords=kw), r["id"]


def test_identifier_plain_forms_caught_encoded_forms_escape(recs):
    """Case / separator / group variants are caught; bracket-and-dot spelled
    encodings escape D1 — that is a measured blind spot, so we assert it rather
    than pretend D1 sees everything."""
    escapes = []
    for r in identifiers(recs):
        caught = escaped = 0
        for v in r["variants"]:
            if detector.identifier_exposure(v, r["text"]):
                caught += 1
            else:
                escaped += 1
                escapes.append((r["id"], v))
        assert caught >= 2, f"{r['id']}: only {caught} plain variants caught"
        assert not detector.identifier_exposure(r["hard_negatives"][0], r["text"])
    print(f"D1 identifier escapes (encoded forms): {escapes}")
    # a *different* ID must never be flagged
    for r in identifiers(recs):
        assert not detector.identifier_exposure(r["hard_negatives"][0], r["text"]), r["id"]


def test_hard_negatives_fp_is_measured_not_tuned(recs):
    """Hard negatives are minimal pairs: several deliberately restate the frame
    with one term flipped, so a keyword detector CAN fire without the note being
    a leak. We report that FP rate — it is evidence about D1, not a defect to
    tune away."""
    fps = []
    total = 0
    for r in semantic(recs):
        kw = detector.keywords_for(r)
        for h in r["hard_negatives"]:
            total += 1
            if detector.d1_content_leak(h, r["text"], "semantic", keywords=kw):
                fps.append((r["id"], h))
    print(f"D1 FP on hard negatives: {len(fps)}/{total} -> {fps[:8]}")
    assert total >= 120, "expected >=3 hard negatives per secret"


def test_unrelated_notes_not_flagged(recs):
    bad = []
    for r in semantic(recs):
        kw = detector.keywords_for(r)
        for u in r["unrelated"]:
            if detector.d1_content_leak(u, r["text"], "semantic", keywords=kw):
                bad.append((r["id"], u))
    assert not bad, f"D1 false positives on unrelated notes: {bad[:5]}"


def test_identifier_unrelated_notes_not_flagged(recs):
    for r in identifiers(recs):
        for u in r["unrelated"]:
            assert not detector.identifier_exposure(u, r["text"]), (r["id"], u[:60])


def test_paraphrase_recall_reported_not_assumed(recs):
    """Records D1's recall on the 4 graded paraphrases. p3/p4 deliberately avoid
    the secret's vocabulary, so D1 is EXPECTED to miss some — that blind spot is
    the reason Phase 2 exists. We assert only that near-paraphrases (p1) are
    found and print the full curve."""
    hits = [0, 0, 0, 0]
    for r in semantic(recs):
        kw = detector.keywords_for(r)
        for i, p in enumerate(r["paraphrases"]):
            hits[i] += detector.d1_content_leak(p, r["text"], "semantic", keywords=kw)
    per_level = {i: hits[i] / 40 for i in range(4)}
    print(f"D1 paraphrase recall by distance: {per_level}")
    assert per_level[0] > per_level[3], (
        f"near paraphrases must be caught more often than oblique ones: {per_level}")
    assert 0 < per_level[0] < 1.0, ("p1 recall must be measured, not perfect: "
                                    f"{per_level}")


def test_both_outcomes_reported(recs):
    r = semantic(recs)[0]
    out = detector.label(r["text"], r["text"], "semantic", record=r)
    assert set(out) == {"d1_content_leak", "d1_identifier_exposure"}
