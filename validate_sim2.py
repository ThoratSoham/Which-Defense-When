"""Why does the simulation miss on some cells?   Run: python validate_sim2.py network_results_transcripts.jsonl
Measures T separately for the SOURCE hop (agent 0 writes from its own context) and DOWNSTREAM hops (a later agent relays a note
that already contains the secret), then re-simulates with those two numbers.  Also predicts the star from the chain."""
import sys, json, collections, numpy as np
from network_run import TOPO
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "network_results_transcripts.jsonl", encoding="utf-8")]
eps = collections.defaultdict(list)
for r in rows: eps[(r["model"], r["defense"], r["pressure"], r["kind"], r["topology"], r["episode"])].append(r)
st = collections.defaultdict(lambda: {"src": [], "down": [], "size": []}); rng = np.random.default_rng(4)
for k, notes in eps.items():
    inc = {n["to"]: n["auto_leaked"] for n in notes}; c = k[:5]; st[c]["size"].append(sum(inc.values()))
    for n in notes:
        if n["from"] == 0: st[c]["src"].append(n["auto_leaked"])
        elif inc.get(n["from"]) == 1: st[c]["down"].append(n["auto_leaked"])
def sim(topo, ts, td, runs=4000):
    out = []
    for _ in range(runs):
        inf = {0}
        for a in sorted(TOPO[topo]):
            for c in TOPO[topo][a]:
                if a in inf and rng.random() < (ts if a == 0 else td): inf.add(c)
        out.append(len(inf) - 1)
    return float(np.mean(out))
print(f"{'model':13s}{'defense':9s}{'kind':9s}{'topo':7s}{'T_src':>7s}{'T_down':>8s}{'(n)':>6s}{'real':>7s}{'sim(T_src,T_down)':>19s}")
gaps = []; cell = {}
for c, v in sorted(st.items()):
    m, d, p, k, t = c; ts = np.mean(v["src"]); td = np.mean(v["down"]) if v["down"] else float("nan"); real = np.mean(v["size"]); cell[c] = (ts, td)
    s = sim(t, ts, td) if v["down"] else sim(t, ts, 0.0)
    gaps.append(abs(real - s)); print(f"{m:13s}{d:9s}{k:9s}{t:7s}{ts:7.2f}{td:8.2f}{len(v['down']):6d}{real:7.2f}{s:19.2f}")
print(f"\nmean absolute gap, in-sample (two-parameter model): {np.mean(gaps):.2f} agents")
print("\nPredict STAR from CHAIN (T_src and T_down fitted on chain6 only):")
g2 = []
for c in sorted(st):
    m, d, p, k, t = c
    if t != "star6" or (m, d, p, k, "chain6") not in cell: continue
    ts, td = cell[(m, d, p, k, "chain6")]
    if np.isnan(td): continue
    s = sim("star6", ts, td); real = np.mean(st[c]["size"]); g2.append(abs(real - s)); print(f"  {m:13s}{d:9s}{k:9s} real {real:5.2f}  predicted {s:5.2f}")
if g2: print(f"mean absolute gap, chain -> star: {np.mean(g2):.2f} agents")
