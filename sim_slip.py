"""Does a persistent gateway blind spot weaken containment?   Run: python sim_slip.py network_results_transcripts.jsonl
Parameters are measured from the real 6-agent runs:
  T_src_none / T_down_none : origin-hop and relay leak rates without defense
  T_src_gw                 : leak rate of a clear secret through a protected agent (per model)
  T_slip                   : relay rate of a note that has ALREADY slipped past a gateway (pooled; small n!)
Two models are compared on 500-agent networks:
  independent : every protected edge leaks with T_src_gw, every unprotected edge with T_src_none (what sim_protect.py assumed)
  slip        : a note that slipped past one gateway keeps slipping (relay rate T_slip); clear notes are re-caught at T_src_gw."""
import sys, json, collections, numpy as np
from sim import topologies, phase3_rho
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "network_results_transcripts.jsonl", encoding="utf-8")]
eps = collections.defaultdict(list)
for r in rows: eps[(r["model"], r["defense"], r["pressure"], r["kind"], r["topology"], r["episode"])].append(r)
src, down = collections.defaultdict(list), collections.defaultdict(list)
for k, notes in eps.items():
    inc = {n["to"]: n["auto_leaked"] for n in notes}
    for n in notes:
        if n["from"] == 0: src[(k[0], k[1])].append(n["auto_leaked"])
        elif inc.get(n["from"]) == 1: down[(k[0], k[1])].append(n["auto_leaked"])
slip_obs = [x for (m, d), v in down.items() if d == "gateway" for x in v]
RHO3 = phase3_rho()                                  # Phase 3 rho (n >= 100) replaces the n=20 relay estimate
if RHO3:
    T_slip = RHO3[0]
    print(f"T_slip = {T_slip:.3f}  <- Phase 3 rewrite persistence, n = {RHO3[1]}, 95% CI [{RHO3[2][0]:.3f}, {RHO3[2][1]:.3f}]")
else:
    T_slip = float(np.mean(slip_obs)) if slip_obs else 0.9
    print(f"T_slip (relay of a note that already slipped past a gateway) = {T_slip:.2f}  from n = {len(slip_obs)} relays  <- small sample; Phase 3 rho not available\n")
N, RUNS, rng = 500, 200, np.random.default_rng(8)
topo = {k: v for k, v in topologies().items() if k in ("random (ER)", "scale-free (BA)")}
PS = [0, .05, .1, .2, .3, .5, .8, 1.0]
def run(G, prot, ps_none, pd_none, ps_gw, slip_on):
    s = int(rng.integers(N)); inf = {s: 0}; fr = [s]
    while fr:
        nxt = []
        for u in fr:
            f = inf[u]
            if u == s: p, nf = (ps_gw, 1) if prot[u] else (ps_none, 0)
            elif prot[u]:
                p, nf = (T_slip, 1) if (slip_on and f == 1) else (ps_gw, 1)
            else: p, nf = (pd_none if slip_on else ps_none), f
            for v in G[u]:
                if v not in inf and rng.random() < p: inf[v] = nf; nxt.append(v)
        fr = nxt
    return len(inf) / N > 0.05
def curve(G, strategy, prm, slip_on):
    order = [v for v, _ in sorted(G.degree(), key=lambda x: -x[1])]; out = []
    for p in PS:
        m, hits = int(p * N), 0
        for _ in range(RUNS):
            prot = np.zeros(N, bool); prot[order[:m] if strategy == "hub-first" else rng.choice(N, m, replace=False)] = True
            hits += run(G, prot, *prm, slip_on)
        out.append(hits / RUNS)
    return out
pc = lambda c: next((p for p, v in zip(PS, c) if v < 0.05), float("inf"))
print(f"{'model':13s}{'network':16s}{'strategy':10s}{'P(outbreak) at p=1.0':>26s}{'p_c':>16s}\n{'':39s}{'indep / slip':>26s}{'indep / slip':>16s}")
for m in sorted({k[0] for k in src}):
    if (m, "none") not in src or (m, "gateway") not in src: continue
    ps_none, ps_gw = np.mean(src[(m, "none")]), np.mean(src[(m, "gateway")]); pd_none = np.mean(down[(m, "none")]) if down[(m, "none")] else ps_none
    for name, G in topo.items():
        for strat in ("random", "hub-first"):
            a, b = curve(G, strat, (ps_none, pd_none, ps_gw), False), curve(G, strat, (ps_none, pd_none, ps_gw), True)
            f = lambda x: "never" if x == float("inf") else f"{x:.2f}"
            print(f"{m:13s}{name:16s}{strat:10s}{a[-1]:13.2f} /{b[-1]:6.2f}{f(pc(a)):>10s} /{f(pc(b)):>6s}")
