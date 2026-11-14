"""Re-score the headline leak rate T under EVERY detector (Phase 2 deliverable).

  python recompute_T.py

For the original chain experiment T is measured at hop 1 (the source hop), as in
the paper. For the network runs the equivalent is the source edge (from == 0).

Reports, per detector: T by defense with Wilson 95% CIs and n, for
  (a) chain hop-1 notes, (b) network source notes,
plus the ladder ordering under each detector. Writes results/t_by_detector.json.

This is the number that answers W3: is the headline T robust to the detector?
"""
import json, math, os, sys
from collections import defaultdict


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def load(path="results/detector_final.jsonl"):
    if not os.path.exists(path):
        sys.exit("run: python run_detectors.py && python run_d3.py && python build_ensemble.py")
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def source_hop_chain(r):
    return r["src"] == "results_v2" and r.get("hop") == 1


def network_source(r):
    return r["src"] == "network_results" and r.get("topology") and r.get("hop") is None


def t_table(rows, det_key):
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        v = r["verdicts"].get(det_key) if det_key != "ensemble" else r.get("ensemble")
        if v not in (0, 1):
            continue
        agg[r["defense"]][0] += v
        agg[r["defense"]][1] += 1
    out = {}
    for d, (k, n) in agg.items():
        lo, hi = wilson(k, n)
        out[d] = {"n": n, "T": k / n if n else float("nan"),
                  "ci": [lo, hi], "k": k}
    return out


def main():
    rows = load()
    detectors = ["d1", "d2", "d3", "ensemble"]
    report = {"chain_hop1": {}, "network_source": {}}
    order = ["none", "warning", "gateway_l1", "gateway"]

    for scope, sel in (("chain_hop1", source_hop_chain),
                       ("network_source", network_source)):
        subset = [r for r in rows if sel(r)]
        print(f"\n=== {scope}  ({len(subset)} notes) ===")
        print(f"{'detector':10s}" + "".join(f"{d:>28s}" for d in order))
        for det in detectors:
            table = t_table(subset, det)
            report[scope][det] = table
            cells = []
            for d in order:
                c = table.get(d)
                cells.append(f"  " if not c else
                             f"{c['T']:.3f} [{c['ci'][0]:.3f},{c['ci'][1]:.3f}]")
            present = [table[d]["T"] for d in order if d in table]
            monotone = all(a > b for a, b in zip(present, present[1:])) if len(present) > 1 else None
            print(f"{det:10s}" + "".join(f"{c:>28s}" for c in cells) +
                  ("" if monotone is None else f"   ladder strictly decreasing: {monotone}"))

    os.makedirs("results", exist_ok=True)
    json.dump(report, open("results/t_by_detector.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote results/t_by_detector.json")


if __name__ == "__main__":
    main()
