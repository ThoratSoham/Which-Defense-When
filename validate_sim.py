"""Does the simulation predict the real multi-agent runs?  Run: python validate_sim.py results_v2.csv network_results.csv
Uses the measured per-hop T from the 3-agent chain (results_v2.csv) to simulate chain6/star6, then compares attack sizes."""
import sys, numpy as np, pandas as pd
from network_run import TOPO
R, N = pd.read_csv(sys.argv[1], names=["model","defense","pressure","kind","hop","leaked"]), pd.read_csv(sys.argv[2], names=["model","defense","pressure","kind","topology","episode","attack","n"])
R = R[R.hop == 1]; Tm = R.groupby(["model", "defense", "pressure", "kind"]).leaked.mean(); rng = np.random.default_rng(3)
def sim(topo, T, runs=4000):
    sizes = []
    for _ in range(runs):
        inf = {0}; 
        for a in sorted(TOPO[topo]):
            if a in inf: [inf.add(c) for c in TOPO[topo][a] if rng.random() < T]
        sizes.append(len(inf) - 1)
    return np.mean(sizes)
print(f"{'model':13s}{'defense':9s}{'press':6s}{'kind':9s}{'topology':9s}{'T(1 hop)':>9s}{'real mean':>10s}{'sim mean':>9s}{'gap':>7s}")
gaps = []
for (m, d, p, k, t), g in N.groupby(["model", "defense", "pressure", "kind", "topology"]):
    if (m, d, p, k) not in Tm.index: continue
    T = Tm[(m, d, p, k)]; s = sim(t, T); r = g.attack.mean(); gaps.append(abs(r - s))
    print(f"{m:13s}{d:9s}{p:6s}{k:9s}{t:9s}{T:9.2f}{r:10.2f}{s:9.2f}{r - s:7.2f}")
print(f"\nmean absolute gap (in agents infected): {np.mean(gaps):.2f}")
