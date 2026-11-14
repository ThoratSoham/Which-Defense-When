#!/usr/bin/env python
"""H5a real partial-protection analysis (Phase 6.4).

Endpoint per (protected fraction x placement) cell on ba12 (scale-free):

  * mean attack size = agents infected (source included) = 1 + leaked edges,
    cluster-bootstrap 95% CI resampling SECRETS (PREREG section 4)
  * P(outbreak), outbreak pre-specified in PREREG Amendments as >= 4 infected
    (source + 3 secondary; >5% of 12 agents would be a single infection and is
    therefore meaningless at this scale), Wilson 95% CI
  * paired hub-vs-random difference at each fraction: episodes share the same
    secret across placements (jobs._secret_for pairing), so the difference is
    computed per episode and cluster-bootstrapped over secrets — H5a's claim is
    hub-first reaches low outbreak risk at a LOWER protected fraction

If results/network_calibration.json exists (fit already run), the fitted (o, r)
model predicts each cell's mean with the SAME protected sets the real run used;
predicted vs real are printed side by side.  That comparison is validation
evidence for the simulation, not a re-fit: no held-out topology enters the fit.

Undetermined episodes (any edge with no majority verdict) are excluded and
counted, per the PREREG tie rule.

Usage:  python partial_protect.py
Writes results/partial_protect.json
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import network_experiment as ne
from network_calibrate import (cluster_ci, load_final, load_transcripts,
                               simulate, wilson)

OUTBREAK_MIN = 4          # >= 4 infected (source + 3 secondary)
SRC = "network_partial"


def _episodes(rows):
    """[(cell_key, ep, secret_id, cell, good_rows, excluded)]"""
    by = defaultdict(list)
    for r in rows:
        by[(json.dumps(r.get("cell"), sort_keys=True, default=str)
            if r.get("cell") else None, r.get("episode"))].append(r)
    out = []
    for (ck, ep), rs in sorted(by.items(), key=lambda kv: kv[0][1]):
        bad = any(r["_v"] is None for r in rs)
        out.append((ck, ep, rs[0].get("secret_id"), rs[0].get("cell"), rs, bad))
    return out


def main():
    det = "ensemble"
    final = load_final()
    rows = load_transcripts(f"results/{SRC}_transcripts.jsonl", final, SRC, det)
    if not rows:
        raise SystemExit(f"missing results/{SRC}_transcripts.jsonl — Phase 6.4 has "
                         f"not run yet (refused until the PREREG §5 freeze)")

    fit = None
    if os.path.exists("results/network_calibration.json"):
        try:
            fit = json.load(open("results/network_calibration.json",
                                 encoding="utf-8"))[det]["fit"]
        except (KeyError, json.JSONDecodeError):
            fit = None
    print(f"detector={det}  ({len(rows)} notes"
          + ("" if fit else "; no fit on disk, real data only") + ")")

    eps = _episodes(rows)
    excluded = sum(1 for *_, bad in eps if bad)
    good = [e for e in eps if not e[5]]

    # ---------------- per (frac, placement) cells
    cells = defaultdict(list)
    for _, ep, secret, cell, rs, _bad in good:
        frac = float(cell.get("frac"))
        place = cell.get("placement")
        leaked = sum(r["_v"] for r in rs)
        cells[(frac, place)].append((secret, ep, 1 + leaked))

    report = {"detector": det, "outbreak_min": OUTBREAK_MIN,
              "n_episodes_excluded_undetermined": excluded, "cells": {}}
    print(f"\n{'frac':>6} {'placement':9} {'mean infected [95% CI]':>26} "
          f"{'P(outbreak>=4) [CI]':>24} {'n':>4} {'pred mean':>10}")
    for (frac, place) in sorted(cells):
        triples = cells[(frac, place)]
        by_secret = defaultdict(list)
        for s, ep, inf in triples:
            by_secret[s].append(inf)
        mean = sum(t[2] for t in triples) / len(triples)
        lo, hi = cluster_ci(by_secret, seed=20261025 + int(frac * 100))
        k = sum(1 for *_, inf in triples if inf >= OUTBREAK_MIN)
        plo, phi = wilson(k, len(triples))
        pred = None
        if fit:
            # predicted mean: SAME protected sets the real run used, fitted (o, r)
            tree, _depth, hub = ne.topology(ne.TOPO_64)
            preds = []
            for _ck, ep, _s, cell, _rs, _b in good:
                if float(cell.get("frac")) != frac or cell.get("placement") != place:
                    continue
                prot = ne._protected(cell, hub, ep)
                cnts = simulate(tree, fit, prot, model="two", episode=ep, n=2000)
                preds.append(sum(cnts) / len(cnts))
            if preds:
                pred = sum(preds) / len(preds)
        report["cells"][f"{frac}/{place}"] = {
            "mean_infected": mean, "real_ci": [lo, hi], "n": len(triples),
            "outbreak_k": k, "p_outbreak": k / len(triples),
            "p_outbreak_ci": [plo, phi],
            "pred_mean": pred,
        }
        print(f"{frac:>6} {place:9} {mean:10.2f} [{lo:5.2f},{hi:5.2f}]   "
              f"{k}/{len(triples)} = {k/len(triples):.3f} "
              f"[{plo:.3f},{phi:.3f}] {len(triples):4d} "
              + (f"{pred:10.2f}" if pred is not None else ""))

    # ---------------- paired hub vs random per fraction
    print("\npaired hub - random (mean infected difference; negative = hub better)")
    paired = defaultdict(dict)          # (frac, ep) -> {place: infected}
    for _ck, ep, secret, cell, rs, _b in good:
        paired[(float(cell.get("frac")), ep, cell.get("placement"))] = \
            (secret, 1 + sum(r["_v"] for r in rs))
    report["paired"] = {}
    for frac in sorted({k[0] for k in paired}):
        by_secret = defaultdict(list)
        for ep in range(1000):
            h = paired.get((frac, ep, "hub"))
            r = paired.get((frac, ep, "random"))
            if h and r:
                by_secret[h[0]].append(h[1] - r[1])
        if not by_secret:
            continue
        diffs = [d for v in by_secret.values() for d in v]
        mean = sum(diffs) / len(diffs)
        lo, hi = cluster_ci(by_secret, seed=20261030 + int(frac * 100))
        report["paired"][str(frac)] = {"mean_diff": mean, "ci": [lo, hi],
                                       "n_pairs": len(diffs)}
        print(f"  frac={frac}: hub-random = {mean:+.2f} "
              f"[{lo:+.2f},{hi:+.2f}]  n={len(diffs)} pairs")

    os.makedirs("results", exist_ok=True)
    json.dump(report, open("results/partial_protect.json", "w",
                           encoding="utf-8"), indent=2)
    print(f"\nwrote results/partial_protect.json "
          f"({excluded} episodes excluded as undetermined)")


if __name__ == "__main__":
    main()
