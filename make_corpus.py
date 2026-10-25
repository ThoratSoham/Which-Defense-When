"""Build corpus/secrets_corpus.json and the FROZEN DEV/TEST split corpus/splits.json.

Split rules (deterministic, seeded, written once and never regenerated):
  * 40 semantic secrets -> DEV 20 / TEST 20, stratified by category (8 x 5):
    every category contributes 2 to DEV; 4 randomly chosen categories contribute a
    3rd, so the split is balanced and category-preserving.
  * 12 identifier secrets -> DEV 6 / TEST 6, exactly 2 per format.
  * The split file stores sha256 of the corpus it was made from; analysis code
    refuses to run if the hash no longer matches (prevents silent corpus edits
    after tuning).

Run:  python make_corpus.py            (only if corpus/splits.json does not exist)
      python make_corpus.py --force    (DANGEROUS: only before any tuning happens)
"""
import hashlib, json, os, random, sys

CORPUS = "corpus/secrets_corpus.json"
SPLITS = "corpus/splits.json"
MASTER_SEED = 20261025


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_splits(records):
    rng = random.Random(MASTER_SEED)
    sem = [r for r in records if r["kind"] == "semantic"]
    ident = [r for r in records if r["kind"] == "identifier"]

    by_cat = {}
    for r in sem:
        by_cat.setdefault(r["cat"], []).append(r["id"])
    cats = sorted(by_cat)
    assert len(cats) == 8 and all(len(by_cat[c]) == 5 for c in cats), "expected 8 categories x 5"
    extra = set(rng.sample(cats, 4))                 # 4 categories contribute 3 to DEV
    dev_sem, test_sem = [], []
    for c in cats:
        ids = sorted(by_cat[c]); rng.shuffle(ids)
        n_dev = 3 if c in extra else 2
        dev_sem += ids[:n_dev]; test_sem += ids[n_dev:]

    by_fmt = {}
    for r in ident:
        by_fmt.setdefault(r["fmt"], []).append(r["id"])
    dev_id, test_id = [], []
    for fmt in sorted(by_fmt):
        ids = sorted(by_fmt[fmt]); rng.shuffle(ids)
        dev_id += ids[:2]; test_id += ids[2:]

    assert len(dev_sem) == len(test_sem) == 20, (len(dev_sem), len(test_sem))
    assert len(dev_id) == len(test_id) == 6
    assert not (set(dev_sem) & set(test_sem)) and not (set(dev_id) & set(test_id))
    return {"master_seed": MASTER_SEED, "created": "2026-10-25",
            "semantic": {"dev": sorted(dev_sem), "test": sorted(test_sem)},
            "identifier": {"dev": sorted(dev_id), "test": sorted(test_id)},
            "tuning_rule": "gateway thresholds and all analysis choices are tuned on DEV only; "
                           "TEST is evaluated once, after freezing."}


def main():
    force = "--force" in sys.argv
    os.makedirs("corpus", exist_ok=True)
    if os.path.exists(SPLITS) and not force:
        print(f"{SPLITS} already exists — split is frozen; not regenerating. "
              f"(use --force only before any tuning)")
        return
    if os.path.exists(SPLITS) and force:
        print("WARNING: regenerating a frozen split with --force. "
              "This is only legitimate before any tuning has happened.")

    import corpus_data
    recs, meta = corpus_data.build_corpus()
    with open(CORPUS, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "records": recs}, f, indent=2, ensure_ascii=False)

    split = make_splits(recs)
    split["corpus_sha256"] = sha256_file(CORPUS)
    with open(SPLITS, "w", encoding="utf-8") as f:
        json.dump(split, f, indent=2)

    print(f"corpus: {len(recs)} records ({meta})")
    print(f"DEV  semantic={len(split['semantic']['dev'])} "
          f"identifier={len(split['identifier']['dev'])}")
    print(f"TEST semantic={len(split['semantic']['test'])} "
          f"identifier={len(split['identifier']['test'])}")
    print(f"corpus sha256: {split['corpus_sha256'][:16]}… -> {SPLITS}")


if __name__ == "__main__":
    main()
