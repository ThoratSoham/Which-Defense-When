"""OUT-OF-SAMPLE test of the simulation on bigger networks.   Run: python validate_sim3.py network_results_transcripts.jsonl
Origination rate T_src and relay rate T_down are fitted ONLY on chain6 and star6 (per model / defense / pressure / secret type), then used to predict
the mean number of agents infected on every OTHER topology in the file (e.g. ba12, ws16). Predictions are made before looking at those results.
Reports real mean with a 95% bootstrap interval, the prediction, and whether the prediction falls inside the interval."""
import sys, json, collections, numpy as np
from network_run import TOPO
FIT = {"chain6", "star6"}; rng = np.random.default_rng(11)
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "network_results_transcripts.jsonl", encoding="utf-8")]
eps = collections.defaultdict(list)
for r in rows: eps[(r["model"], r["defense"], r["pressure"], r["kind"], r["topology"], r["episode"])].append(r)
src, down, size = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
for k, notes in eps.items():
    inc = {n["to"]: n["auto_leaked"] for n in notes}; cell = k[:5]; size[cell].append(sum(inc.values()))
    for n in notes:
        if n["from"] == 0: src[cell].append(n["auto_leaked"])
        elif inc.get(n["from"]) == 1: down[cell].append(n["auto_leaked"])
def predict(topo, ts_l, td_l, draws=150, sims=150):
    """Mean attack size predicted from the fitted rates, with a 95% interval that carries the uncertainty of the fitted rates
    (each draw samples T_src and T_down from Beta posteriors of the chain/star data)."""
    ks, ns, kd, nd = sum(ts_l), len(ts_l), sum(td_l), len(td_l); means = []
    for _ in range(draws):
        ts, td = rng.beta(ks + 1, ns - ks + 1), rng.beta(kd + 1, nd - kd + 1); out = []
        for _ in range(sims):
            inf = {0}
            for a in sorted(TOPO[topo]):
                if a in inf:
                    for c in TOPO[topo][a]:
                        if rng.random() < (ts if a == 0 else td): inf.add(c)
            out.append(len(inf) - 1)
        means.append(np.mean(out))
    return float(np.mean(means)), np.percentile(means, [2.5, 97.5])
def boot(x, n=2000): b = [np.mean(rng.choice(x, len(x))) for _ in range(n)]; return np.percentile(b, [2.5, 97.5])
fit = {}
for (m, d, p, k, t), v in src.items():
    if t in FIT: fit.setdefault((m, d, p, k), [[], []]); fit[(m, d, p, k)][0] += v; fit[(m, d, p, k)][1] += down[(m, d, p, k, t)]
print(f"{'model':13s}{'defense':9s}{'press':6s}{'kind':9s}{'topology':9s}{'agents':>7s}{'T_src':>7s}{'T_down':>7s}{'real mean [95% CI]':>22s}{'predicted [95% PI]':>22s}{'consistent':>11s}")
gaps, inside, total = [], 0, 0
for (m, d, p, k, t) in sorted(size):
    if t in FIT or (m, d, p, k) not in fit: continue
    ts_l, td_l = fit[(m, d, p, k)]
    if not ts_l: continue
    ts = float(np.mean(ts_l)); td = float(np.mean(td_l)) if td_l else 0.0
    if not td_l: td_l = [0]
    nodes = set(TOPO[t]) | {c for v in TOPO[t].values() for c in v}; real = size[(m, d, p, k, t)]; lo, hi = boot(real); pr, (pl, ph) = predict(t, ts_l, td_l)
    ok = lo <= ph and pl <= hi; inside += ok; total += 1; gaps.append(abs(np.mean(real) - pr) / (len(nodes) - 1))     # consistent = the two intervals overlap
    print(f"{m:13s}{d:9s}{p:6s}{k:9s}{t:9s}{len(nodes):7d}{ts:7.2f}{td:7.2f}{np.mean(real):8.2f} [{lo:4.1f},{hi:4.1f}]{pr:9.2f} [{pl:4.1f},{ph:4.1f}]{'yes' if ok else 'NO':>11s}")
if total: print(f"\nout-of-sample cells: {total}; real and predicted intervals overlap in {inside} ({inside / total:.0%}); mean absolute gap = {np.mean(gaps):.1%} of the maximum possible attack size")
