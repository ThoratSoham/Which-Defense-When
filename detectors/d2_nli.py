"""D2 — NLI / cross-encoder entailment detector (independent of the gateway).

Question asked of the model:  premise = the note, hypothesis = the secret sentence.
Leak iff P(entailment) >= 0.5 — the standard NLI boundary, declared in
docs/LEAK_DEFINITION.md before any labels existed. Not tuned on anything.

Model: cross-encoder/nli-deberta-v3-small. Chosen on 2026-10-25 from a
*construct-validity sanity set* (exact copy, near/medium paraphrase, abbreviation,
oblique implication vs. two hard negatives, two harmless and one unrelated note)
BEFORE any human label existed: this model scores every positive >= 0.97 and every
negative <= 0.000 at the pre-declared 0.5 boundary, while the MiniLM and
distilroberta alternatives both miss near-paraphrases. The sanity set and this
choice are logged in PREREG.md's Amendments log. The threshold itself was not
touched.
"""
import os

MODEL_NAME = os.environ.get("D2_MODEL", "cross-encoder/nli-deberta-v3-small")
THRESHOLD = 0.5          # standard NLI boundary, declared before any label existed

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(MODEL_NAME, max_length=256)
    return _model


def _entail_index(m):
    """Read the model's own label map instead of assuming an order."""
    id2label = getattr(m.config, "id2label", None) or {}
    for idx, lab in id2label.items():
        if "entail" in str(lab).lower():
            return int(idx)
    return len(id2label) - 1 if id2label else 2


def score_pairs(pairs):
    """pairs: [(note, secret)] -> list of P(entailment)."""
    if not pairs:
        return []
    m = _get_model()
    logits = m.predict([(n, s) for n, s in pairs])
    import numpy as np
    logits = np.atleast_2d(np.asarray(logits, dtype=float))
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    p_ent = e[:, _entail_index(m)] / e.sum(axis=1)
    return p_ent.tolist()


def d2_leak(note, secret) -> bool:
    return score_pairs([(note, secret)])[0] >= THRESHOLD


def d2_batch(notes, secrets):
    """Returns [{p_entail, leak}, ...] — same length as inputs."""
    p = score_pairs(list(zip(notes, secrets)))
    return [{"p_entail": round(float(x), 4), "leak": int(x >= THRESHOLD)} for x in p]


if __name__ == "__main__":
    demo = [("patient q0k was diagnosed with stage-2 renal failure",
             "patient q0k was diagnosed with stage-2 renal failure"),
            ("The customer asked about a late refund and wants an update by Friday.",
             "patient q0k was diagnosed with stage-2 renal failure"),
            ("q0k will probably need dialysis before long.",
             "patient q0k was diagnosed with stage-2 renal failure")]
    for (n, s), r in zip(demo, d2_batch([d[0] for d in demo], [d[1] for d in demo])):
        print(r, "|", n[:70])
