"""Agreement and detector-accuracy analysis (Phase 2, runs AFTER human labels exist).

  python analyze_labels.py

Reports, for BOTH outcomes (content leak, identifier exposure):
  * per detector (D1, D2, D3-google, ensemble): confusion vs human labels,
    precision / recall / specificity with Wilson 95% CIs
  * Cohen's kappa AND Gwet's AC1 between each detector and the human labels
    (AC1 is reported because kappa is unstable when the positive rate is extreme —
    which it is here: the gateway arm is ~2% positive)
  * intra-annotator consistency where the same note was labelled twice
    (label_sheet vs annotator2_sheet are the same person — see AUDIT §10)
  * a disagreement list for adjudication

Writes results/agreement.json and prints a table.
"""
import csv, glob, hashlib, json, math, os, sys
from collections import Counter


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def kappa(a, b, ac1=False):
    n = len(a)
    if n == 0:
        return float("nan"), float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    p1 = sum(a) / n
    if ac1:                                   # Gwet's AC1 chance agreement
        pe = 2 * p1 * (1 - p1)
    else:                                     # Cohen's kappa
        q1 = sum(b) / n
        pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po, (po - pe) / (1 - pe) if pe != 1 else float("nan")), po


def metrics(human, pred):
    tp = sum(h == 1 and p == 1 for h, p in zip(human, pred))
    tn = sum(h == 0 and p == 0 for h, p in zip(human, pred))
    fp = sum(h == 0 and p == 1 for h, p in zip(human, pred))
    fn = sum(h == 1 and p == 0 for h, p in zip(human, pred))
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    (pl, ph) = wilson(tp, tp + fp)
    (rl, rh) = wilson(tp, tp + fn)
    (k, kk), po = kappa(human, pred)
    (ka, kka), _ = kappa(human, pred, ac1=True)
    return {"n": len(human), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": prec, "precision_ci": [pl, ph],
            "recall": rec, "recall_ci": [rl, rh],
            "agreement": po, "kappa": kk, "gwet_ac1": kka,
            "positive_rate_human": sum(human) / len(human) if human else float("nan"),
            "positive_rate_pred": sum(pred) / len(pred) if pred else float("nan")}


def sha(note):
    return hashlib.sha256(note.strip().encode()).hexdigest()[:16]


def load_key():
    return {r["pool_id"]: r for r in
            csv.DictReader(open("results/label_sample_key.csv", encoding="utf-8"))}


def load_pool():
    return {r["pool_id"]: r for r in
            (json.loads(l) for l in open("results/detector_pool.jsonl", encoding="utf-8"))}


def load_human():
    rows = list(csv.DictReader(open("results/human_labels.csv", encoding="utf-8")))
    # keep the latest label per sample_id
    out = {}
    for r in rows:
        if r["content_leak"].strip() == "":
            continue
        out[int(r["sample_id"])] = {"content": int(r["content_leak"]),
                                    "ident": int(r["identifier_exposure"]),
                                    "annotator": r["annotator"],
                                    "note_sha": r.get("note_sha", "")}
    return out


def load_d3(path):
    d = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            d[r["pool_id"]] = r.get("leak")
    return d


def main():
    for f in ("results/human_labels.csv", "results/label_sample_key.csv",
              "results/detector_pool.jsonl"):
        if not os.path.exists(f):
            sys.exit(f"missing {f} — label first (label_app.py) or build the sample")
    key, pool, human = load_key(), load_pool(), load_human()
    ids = [pid for pid in key if int(key[pid]["sample_id"]) in human]
    if not ids:
        sys.exit("no human labels found in results/human_labels.csv")
    print(f"evaluating on {len(ids)} labelled notes\n")

    d3g = load_d3("results/d3_google.jsonl")
    d3o = load_d3("results/d3_openrouter.jsonl")
    d3l = load_d3("results/d3_local.jsonl")

    # D2/D3 implement Outcome 1 (content leak) ONLY — see docs/LEAK_DEFINITION.md.
    # Outcome 2 (identifier exposure) is implemented by D1 alone (d1_identifier),
    # so the identifier table evaluates only D1; scoring D2/D3 against identifier
    # labels would compare a content-leak verdict to a different question.
    content_detectors = {
        "D1 (keyword)": lambda p: pool[p]["verdicts"]["d1"],
        "D2 (NLI)": lambda p: pool[p]["verdicts"]["d2"],
        "D3 (google)": lambda p: d3g.get(p),
        "D3 (openrouter)": lambda p: d3o.get(p),
        "D3 (local)": lambda p: d3l.get(p),
    }
    ident_detectors = {
        "D1 (keyword/ID)": lambda p: pool[p].get("d1_identifier"),
    }
    # ensemble needs >=2 votes
    def ensemble(p):
        from detectors.ensemble import ensemble_vote
        v = {"d1": pool[p]["verdicts"]["d1"], "d2": pool[p]["verdicts"]["d2"],
             "d3": d3g.get(p, d3o.get(p, d3l.get(p)))}
        return ensemble_vote(v)["ensemble"]
    content_detectors["Ensemble"] = ensemble

    report = {"n_labelled": len(ids)}
    for outcome, hkey in (("content_leak", "content"), ("identifier_exposure", "ident")):
        report[outcome] = {}
        detectors = (content_detectors if outcome == "content_leak"
                     else ident_detectors)
        human_v = [human[int(key[p]["sample_id"])][hkey] for p in ids]
        print(f"=== {outcome}  (human positive rate "
              f"{sum(human_v)/len(human_v):.3f}) ===")
        if outcome == "identifier_exposure":
            print("  (only detectors implementing Outcome 2 are scored here; "
                  "D2/D3/ensemble answer Outcome 1 only)")
        print(f"{'detector':18s}{'n':>5s}{'prec':>14s}{'recall':>14s}"
              f"{'kappa':>8s}{'AC1':>8s}{'TP/FP/FN':>12s}")
        for name, fn in detectors.items():
            pred, hv = [], []
            for p in ids:
                v = fn(p)
                if v in (0, 1):
                    pred.append(v); hv.append(human[int(key[p]["sample_id"])][hkey])
            if not pred:
                print(f"{name:18s}  no verdicts yet")
                report[outcome][name] = {"n": 0, "note": "not measured"}
                continue
            m = metrics(hv, pred)
            report[outcome][name] = m
            print(f"{name:18s}{m['n']:5d}"
                  f"{m['precision']:.2f} [{m['precision_ci'][0]:.2f},{m['precision_ci'][1]:.2f}]"
                  f"{m['recall']:.2f} [{m['recall_ci'][0]:.2f},{m['recall_ci'][1]:.2f}]"
                  f"{m['kappa']:8.2f}{m['gwet_ac1']:8.2f}"
                  f"{m['tp']}/{m['fp']}/{m['fn']:>4d}")
        print()

    # ---- intra-annotator consistency (same person, two passes)
    intra = []
    for f1, f2 in (("label_sheet.csv", "annotator2_sheet.csv"),
                   ("label_sheet_22.csv", "label_sheet_33.csv")):
        if not (os.path.exists(f1) and os.path.exists(f2)):
            continue
        a = {sha(r["note_sent_to_next_agent"]): int(float(r["human_leaked"]))
             for r in csv.DictReader(open(f1, encoding="utf-8"))
             if str(r.get("human_leaked", "")).strip() not in ("", "nan")}
        b = {sha(r["note_sent_to_next_agent"]): int(float(r["human_leaked"]))
             for r in csv.DictReader(open(f2, encoding="utf-8"))
             if str(r.get("human_leaked", "")).strip() not in ("", "nan")}
        common = sorted(set(a) & set(b))
        if common:
            (k, kk), po = kappa([a[c] for c in common], [b[c] for c in common])
            (ka, kka), _ = kappa([a[c] for c in common], [b[c] for c in common], ac1=True)
            intra.append({"files": [f1, f2], "n_overlap": len(common),
                          "agreement": po, "kappa": kk, "gwet_ac1": kka})
            print(f"intra-annotator ({f1} vs {f2}): n={len(common)} "
                  f"agreement={po:.2f} kappa={kk:.2f} AC1={kka:.2f}")
    report["intra_annotator"] = intra

    # ---- disagreement list for adjudication
    dis = []
    for p in ids:
        sid = int(key[p]["sample_id"])
        hv = human[sid]["content"]
        verdicts = {"d1": pool[p]["verdicts"]["d1"], "d2": pool[p]["verdicts"]["d2"],
                    "d3": d3g.get(p, d3o.get(p, d3l.get(p)))}
        vals = [v for v in verdicts.values() if v in (0, 1)]
        if not vals or hv not in vals or len(set(vals + [hv])) > 1:
            dis.append({"sample_id": sid, "human": hv, "detectors": verdicts,
                        "note": pool[p]["note"][:400], "secret": pool[p]["secret"]})
    report["disagreements"] = dis
    print(f"\nhuman-vs-detector disagreements: {len(dis)} of {len(ids)}")

    os.makedirs("results", exist_ok=True)
    json.dump(report, open("results/agreement.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print("wrote results/agreement.json")


if __name__ == "__main__":
    main()
