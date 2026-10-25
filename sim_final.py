"""Herd immunity, done honestly.   Run: python sim_final.py results_v2r.csv network_results_transcripts.jsonl
Three ways a protected agent's gateway can behave (unprotected agents are identical in all three):
  independent : every note leaks through with the gateway's measured rate T_gw, independently          (the optimistic assumption)
  slip        : the origin's note slips through with T_gw per edge; once a note has slipped, later gateways pass it too (relay rate T_slip)
  correlated  : with probability q_ev per episode the secret is 'evasive': every gateway passes it at T_slip; otherwise gateways pass it at T_gw
Three protection strategies:  random  |  hub-first (needs the whole graph)  |  acquaintance (protect a random NEIGHBOUR of a random agent: needs no graph)
Reports P(outbreak) at full protection (the floor) and the smallest protected fraction p_c with P(outbreak) < 5%.   Writes fig_herd_models.png."""
import sys, json, collections, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sim import topologies
N = 500
RUNS = int(sys.argv[sys.argv.index('--runs') + 1]) if '--runs' in sys.argv else 100
sys.argv = [x for i, x in enumerate(sys.argv) if x != '--runs' and (i == 0 or sys.argv[i - 1] != '--runs')]
PS = [0, .05, .1, .2, .3, .5, .8, 1.0]; MODELS = ("independent", "slip", "correlated"); STRATS = ("random", "hub-first", "acquaintance")
R = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "results_v2r.csv", names=["model", "defense", "pressure", "kind", "hop", "leaked"]); R = R[(R.hop == 1) & (R.model != "qwen2.5:7b")]
T_gw = R[R.defense == "gateway"].leaked.mean(); T_src = R[R.defense == "none"].groupby("model").leaked.mean()
rows = [json.loads(l) for l in open(sys.argv[2] if len(sys.argv) > 2 else "network_results_transcripts.jsonl", encoding="utf-8")]
eps = collections.defaultdict(list)
for r in rows: eps[(r["model"], r["defense"], r["pressure"], r["kind"], r["topology"], r["episode"])].append(r)
down, slip = collections.defaultdict(list), []
for k, notes in eps.items():
    inc = {n["to"]: n["auto_leaked"] for n in notes}
    for n in notes:
        if n["from"] != 0 and inc.get(n["from"]) == 1:
            if k[1] == "none": down[k[0]].append(n["auto_leaked"])
            elif k[1] == "gateway": slip.append(n["auto_leaked"])
T_slip = float(np.mean(slip)) if len(slip) >= 5 else 0.95; Q_EV = 1 - (1 - T_gw) ** 4          # chance that at least one of ~4 origin notes slips
print(f"T_gw = {T_gw:.3f} (hop 1, all models)   T_slip = {T_slip:.2f} (n = {len(slip)} relays)   q_ev = {Q_EV:.3f}\n")
topo = {k: v for k, v in topologies().items() if k in ("random (ER)", "scale-free (BA)")}
import random as _random
RND = _random.Random(21)
def acquaintance(adj, m):
    """Protect a random NEIGHBOUR of a random agent, repeated. Needs no map of the graph. For large m the last few agents are rarely reached
    (coupon-collector effect), so after 6*m draws the remainder is filled at random."""
    prot, tries = set(), 0
    while len(prot) < m and tries < 6 * m:
        tries += 1; nb = adj[RND.randrange(N)]
        if nb: prot.add(nb[RND.randrange(len(nb))])
    if len(prot) < m: prot.update(RND.sample([v for v in range(N) if v not in prot], m - len(prot)))
    return prot
def outbreak(adj, prot, ts, td, bm):
    s = RND.randrange(N); ev = bm == "correlated" and RND.random() < Q_EV; inf = [-1] * N; inf[s] = 0; fr = [s]; cnt = 1; rr = RND.random
    while fr:
        nxt = []
        for u in fr:
            f = inf[u]
            if u == s: p, nf = (((T_slip if ev else T_gw) if bm == "correlated" else T_gw), 1) if prot[u] else (ts, 0)
            elif prot[u]:
                if bm == "independent": p, nf = T_gw, f
                elif bm == "slip": p, nf = (T_slip if f == 1 else T_gw), 1
                else: p, nf = (T_slip if ev else T_gw), f
            else: p, nf = (ts if bm == "independent" else td), f
            for v in adj[u]:
                if inf[v] < 0 and rr() < p: inf[v] = nf; nxt.append(v); cnt += 1
        fr = nxt
    return cnt / N > 0.05
def curve(G, strat, ts, td, bm):
    adj = [list(G[u]) for u in range(N)]; order = [v for v, _ in sorted(G.degree(), key=lambda x: -x[1])]; out = []
    for p in PS:
        m, hits = int(p * N), 0
        for _ in range(RUNS):
            prot = [False] * N; sel = order[:m] if strat == "hub-first" else acquaintance(adj, m) if strat == "acquaintance" else RND.sample(range(N), m)
            for v in sel: prot[v] = True
            hits += outbreak(adj, prot, ts, td, bm)
        out.append(hits / RUNS)
    return out
pc = lambda c: next((p for p, v in zip(PS, c) if v < 0.05), None)
fmt = lambda x: "never" if x is None else f"{x:.2f}"
fig, axes = plt.subplots(len(topo), len(T_src), figsize=(4 * len(T_src), 3.3 * len(topo)), squeeze=False); res = {}
print(f"{'model':13s}{'network':16s}{'strategy':14s}" + "".join(f"{m + ' (floor / p_c)':>26s}" for m in MODELS))
for j, (model, ts) in enumerate(T_src.items()):
    td = float(np.mean(down[model])) if down[model] else ts
    for i, (name, G) in enumerate(topo.items()):
        for strat in STRATS:
            line = f"{model:13s}{name:16s}{strat:14s}"
            for bm in MODELS:
                c = curve(G, strat, ts, td, bm); res[(model, name, strat, bm)] = c; line += f"{c[-1]:14.2f} /{fmt(pc(c)):>8s}  "
                axes[i][j].plot(PS, c, ls={"independent": "--", "slip": "-", "correlated": ":"}[bm], c={"random": "C0", "hub-first": "C1", "acquaintance": "C2"}[strat], lw=1.4)
            print(line)
        axes[i][j].axhline(0.05, c="gray", lw=0.6); axes[i][j].set_title(f"{model} | {name}", fontsize=8); axes[i][j].set_xlabel("fraction of agents behind gateway"); axes[i][j].set_ylabel("P(outbreak)")
from matplotlib.lines import Line2D
axes[0][0].legend([Line2D([0], [0], c=c) for c in ("C0", "C1", "C2")] + [Line2D([0], [0], c="k", ls=s) for s in ("--", "-", ":")], list(STRATS) + list(MODELS), fontsize=6, ncol=2)
plt.tight_layout(); plt.savefig("fig_herd_models.png", dpi=200); print("\nwrote fig_herd_models.png (dashed = independent, solid = slip, dotted = correlated)")
