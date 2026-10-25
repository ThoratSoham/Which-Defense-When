"""Herd-immunity / partial protection with MEASURED T.  Run: python sim_protect.py results_v2.csv
A fraction p of agents sit behind the gateway (their outgoing notes leak with T_gateway, others with T_none).
Compares protecting hub agents first vs random agents.  Outputs fig_partial_protection.png + p_c table.
"""
import sys, numpy as np, pandas as pd, networkx as nx, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sim import topologies, theory_R0
F = sys.argv[1] if len(sys.argv) > 1 else "results_v2.csv"
N, RUNS, rng = 500, 150, np.random.default_rng(5)
d = pd.read_csv(F, names=["model","defense","pressure","kind","hop","leaked"]); d = d[(d.hop == 1) & (d.model != "qwen2.5:7b")]
T_gw = d[d.defense == "gateway"].leaked.mean(); T_none = d[d.defense == "none"].groupby("model").leaked.mean()
print(f"T with gateway = {T_gw:.3f}\n")
topo = {k: v for k, v in topologies().items() if k in ("random (ER)", "scale-free (BA)")}
PS = [0, .02, .05, .1, .15, .2, .3, .4, .5, .6, .8, 1.0]
def outbreak(G, tv):
    s = int(rng.integers(N)); inf, fr = {s}, [s]
    while fr:
        nx_ = []
        for u in fr:
            for v in G[u]:
                if v not in inf and rng.random() < tv[u]: inf.add(v); nx_.append(v)
        fr = nx_
    return len(inf) / N > 0.05
def curve(G, T, strategy):
    order = [v for v, _ in sorted(G.degree(), key=lambda x: -x[1])]; out = []
    for p in PS:
        m, hits = int(p * N), 0
        for _ in range(RUNS):
            prot = order[:m] if strategy == "hub-first" else rng.choice(N, m, replace=False)
            tv = np.full(N, T); tv[list(prot)] = T_gw; hits += outbreak(G, tv)
        out.append(hits / RUNS)
    return out
fig, ax = plt.subplots(len(topo), len(T_none), figsize=(4 * len(T_none), 3.4 * len(topo)), squeeze=False)
print(f"{'model':13s}{'network':16s}{'T':>6s}{'R0':>6s}{'1-1/R0':>8s}{'p_c random':>12s}{'p_c hub-first':>15s}")
for j, (model, T) in enumerate(T_none.items()):
    for i, (name, G) in enumerate(topo.items()):
        res = {s: curve(G, T, s) for s in ("random", "hub-first")}
        pc = lambda c: next((p for p, v in zip(PS, c) if v < 0.05), float("nan"))
        R0 = theory_R0(G, T)
        print(f"{model:13s}{name:16s}{T:6.2f}{R0:6.2f}{max(0, 1 - 1 / R0):8.2f}{pc(res['random']):12.2f}{pc(res['hub-first']):15.2f}")
        for s, c in res.items(): ax[i][j].plot(PS, c, marker="o", ms=3, label=s)
        ax[i][j].axhline(0.05, ls=":", c="gray"); ax[i][j].set_title(f"{model} | {name}", fontsize=9)
        ax[i][j].set_xlabel("fraction of agents behind gateway"); ax[i][j].set_ylabel("P(outbreak)"); ax[i][j].legend(fontsize=7)
plt.tight_layout(); plt.savefig("fig_partial_protection.png", dpi=200)
