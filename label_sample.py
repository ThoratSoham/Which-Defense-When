"""Select the blinded human-labelling sample (300 notes) from the detector pool.

Stratified by defense x secret kind x model, with:
  * the gateway condition oversampled (25% of the sample, since it carries the
    headline claim),
  * notes where D1 and D2 disagree oversampled (that is where the definition is
    actually tested),
  * notes already labelled in label_sheet*.csv excluded (fresh labels),
  * redaction markers stripped so the annotator cannot see the condition.

Writes:
  results/label_sample.csv      BLIND: sample_id, secret, note   <- what you label
  results/label_sample_key.csv  metadata + detector verdicts     <- do not open
"""
import csv, glob, json, os, random, re, sys
from collections import defaultdict

TARGET = 300
GATEWAY_SHARE = 0.25          # oversample the defense the paper leans on
DISAGREE_SHARE = 0.40         # oversample detector disagreements
SEED = 20261025

STRIP = re.compile(r"\s*\[(?:REDACTED|ID)[^\]]*\]")


def strip_markers(t):
    return STRIP.sub("", t or "").strip()


def already_labelled():
    seen = set()
    for f in glob.glob("label_sheet*.csv") + glob.glob("results/label_sheet*.csv"):
        try:
            for r in csv.DictReader(open(f, encoding="utf-8")):
                note = (r.get("note_sent_to_next_agent") or "").strip()
                if note and (r.get("human_leaked") or "").strip() != "":
                    seen.add(re.sub(r"\s+", " ", note))
        except Exception as e:
            print(f"  (could not read {f}: {e})")
    return seen


def main():
    if not os.path.exists("results/detector_pool.jsonl"):
        sys.exit("run: python run_detectors.py first")
    pool = [json.loads(l) for l in open("results/detector_pool.jsonl", encoding="utf-8")]
    labelled = already_labelled()
    fresh = [r for r in pool
             if re.sub(r"\s+", " ", strip_markers(r["note"])) not in labelled]
    print(f"pool {len(pool)} - already labelled {len(pool) - len(fresh)} -> fresh {len(fresh)}")

    for r in fresh:
        r["disagree"] = int(r["verdicts"]["d1"] != r["verdicts"]["d2"])
        r["blind_note"] = strip_markers(r["note"])

    # ---- disagreement quota first (they are the informative ones)
    rng = random.Random(SEED)
    for r in fresh:
        r["blind_note"] = strip_markers(r["note"])
    disagree = [r for r in fresh if r["disagree"]]
    rng.shuffle(disagree)
    n_dis_target = min(int(TARGET * DISAGREE_SHARE), len(disagree))

    # ---- stratified fill: equal quota per defense, then kind x model inside it
    by_cell = defaultdict(list)
    for r in fresh:
        by_cell[(r["defense"], r["kind"], r["model"])].append(r)
    for v in by_cell.values():
        rng.shuffle(v)
    defenses = sorted({k[0] for k in by_cell})
    per_defense = {d: round(TARGET / len(defenses)) for d in defenses}
    # gateway keeps its oversample share
    over = TARGET - sum(per_defense.values())
    per_defense["gateway"] += over

    picked, used = [], set()
    dis_used = 0
    for d in defenses:
        cells = sorted([k for k in by_cell if k[0] == d])
        totals = {k: len(by_cell[k]) for k in cells}
        n_total = sum(totals.values()) or 1
        alloc = {k: max(3, round(per_defense[d] * totals[k] / n_total)) for k in cells}
        # round to the defense quota
        while sum(alloc.values()) > per_defense[d]:
            k = max(alloc, key=lambda x: alloc[x]); alloc[k] -= 1
        while sum(alloc.values()) < per_defense[d]:
            k = max(cells, key=lambda x: totals[x] - alloc.get(x, 0))
            if alloc[k] >= totals[k]:
                break
            alloc[k] += 1
        # fill each cell: disagreements first, up to the global disagreement cap
        for k in cells:
            avail = by_cell[k]
            dis = [r for r in avail if r["disagree"]]
            reg = [r for r in avail if not r["disagree"]]
            take_dis = min(len(dis), max(0, n_dis_target - dis_used), alloc[k])
            take = [r for r in dis[:take_dis]] + [r for r in reg[:alloc[k] - take_dis]]
            dis_used += take_dis
            for r in take:
                if id(r) not in used:
                    used.add(id(r)); picked.append(r)
        # top up this defense if short (cells smaller than their quota)
        if sum(1 for r in picked if r["defense"] == d) < per_defense[d]:
            need = per_defense[d] - sum(1 for r in picked if r["defense"] == d)
            extra = [r for r in sum((by_cell[k] for k in cells), []) if id(r) not in used]
            rng.shuffle(extra)
            for r in extra[:need]:
                used.add(id(r)); picked.append(r)

    # trim / top up to exactly TARGET
    rng.shuffle(picked)
    if len(picked) > TARGET:
        keep = [r for r in picked if r["disagree"]]
        extra = [r for r in picked if not r["disagree"]]
        keep += extra[:max(0, TARGET - len(keep))]
        picked = keep[:TARGET]
    elif len(picked) < TARGET:
        pool_extra = [r for r in fresh if id(r) not in used]
        rng.shuffle(pool_extra)
        picked += pool_extra[:TARGET - len(picked)]

    assert len(picked) == TARGET, len(picked)
    os.makedirs("results", exist_ok=True)
    with open("results/label_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "secret", "note"])
        for i, r in enumerate(sorted(picked, key=lambda r: (r["defense"], r["kind"], r["model"]))):
            r["sample_id"] = i
            w.writerow([i, r["secret"], r["blind_note"]])
    with open("results/label_sample_key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "src", "model", "defense", "pressure", "kind",
                    "topology", "episode", "d1", "d2", "d2_p", "disagree", "pool_id"])
        for i, r in enumerate(sorted(picked, key=lambda r: (r["defense"], r["kind"], r["model"]))):
            w.writerow([i, r["src"], r["model"], r["defense"], r["pressure"], r["kind"],
                        r["topology"], r["episode"], r["verdicts"]["d1"], r["verdicts"]["d2"],
                        r.get("d2_p"), r["disagree"], r["pool_id"]])

    from collections import Counter
    print(f"wrote {len(picked)} notes -> results/label_sample.csv (blind) + key")
    print("by defense:", dict(Counter(r["defense"] for r in picked)))
    print("by kind:", dict(Counter(r["kind"] for r in picked)))
    print("by model:", dict(Counter(r["model"] for r in picked)))
    print("D1/D2 disagreements included:", sum(r["disagree"] for r in picked))


if __name__ == "__main__":
    main()
