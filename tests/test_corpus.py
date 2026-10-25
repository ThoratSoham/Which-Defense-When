"""Corpus integrity + frozen split tests (Phase 1)."""
import hashlib, json, os, collections, pytest

CORPUS = "corpus/secrets_corpus.json"
SPLITS = "corpus/splits.json"


@pytest.fixture(scope="module")
def corpus():
    if not os.path.exists(CORPUS):
        pytest.skip("corpus not built yet — run: python make_corpus.py")
    return json.load(open(CORPUS, encoding="utf-8"))


@pytest.fixture(scope="module")
def splits():
    if not os.path.exists(SPLITS):
        pytest.skip("split not built yet — run: python make_corpus.py")
    return json.load(open(SPLITS, encoding="utf-8"))


def test_counts(corpus):
    recs = corpus["records"]
    sem = [r for r in recs if r["kind"] == "semantic"]
    ident = [r for r in recs if r["kind"] == "identifier"]
    assert len(sem) == 40, "need >=40 semantic secrets (spec: 40)"
    assert len(ident) == 12
    cats = collections.Counter(r["cat"] for r in sem)
    assert len(cats) == 8 and set(cats.values()) == {5}, cats
    fmts = collections.Counter(r["fmt"] for r in ident)
    assert set(fmts.values()) == {4} and len(fmts) == 3, fmts


def test_per_secret_material(corpus):
    for r in corpus["records"]:
        rid = r["id"]
        if r["kind"] == "semantic":
            assert len(r["paraphrases"]) == 4, rid
            assert len(set(r["paraphrases"])) == 4, rid
            assert r["abbr"] and r["vague"], rid
            assert len(r["hard_negatives"]) >= 3, rid
            assert len(r["harmless"]) >= 3, rid
            assert len(r["unrelated"]) >= 20, rid
            assert r["ident"] and r["ident"] not in ("", None), rid
            # paraphrases must differ from the secret itself
            for p in r["paraphrases"]:
                assert p.strip().rstrip(".") != r["text"].strip().rstrip("."), rid
        else:
            assert len(r["variants"]) >= 4, rid
            assert len(r["hard_negatives"]) >= 3, rid
            assert len(r["harmless"]) >= 3, rid
            assert len(r["unrelated"]) >= 20, rid


def test_hard_negatives_are_not_the_secret(corpus):
    for r in corpus["records"]:
        for h in r["hard_negatives"]:
            assert h.strip() != r["text"].strip(), (r["id"], h)


def test_split_sizes_and_disjoint(corpus, splits):
    s, i = splits["semantic"], splits["identifier"]
    assert len(s["dev"]) == 20 and len(s["test"]) == 20
    assert len(i["dev"]) == 6 and len(i["test"]) == 6
    assert not set(s["dev"]) & set(s["test"])
    assert not set(i["dev"]) & set(i["test"])
    all_ids = {r["id"] for r in corpus["records"]}
    assert set(s["dev"]) | set(s["test"]) | set(i["dev"]) | set(i["test"]) == all_ids


def test_split_stratified(corpus, splits):
    by_id = {r["id"]: r for r in corpus["records"]}
    per_cat = collections.Counter(by_id[x]["cat"] for x in splits["semantic"]["dev"])
    assert set(per_cat.values()) <= {2, 3} and sum(per_cat.values()) == 20
    per_fmt = collections.Counter(by_id[x]["fmt"] for x in splits["identifier"]["dev"])
    assert set(per_fmt.values()) == {2}


def test_split_bound_to_corpus_hash(corpus, splits):
    h = hashlib.sha256(open(CORPUS, "rb").read()).hexdigest()
    assert splits["corpus_sha256"] == h, (
        "corpus changed after the split was frozen — this is exactly the "
        "tuning-on-TEST hazard the split exists to prevent")
