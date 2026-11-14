"""Run the network simulation using YOUR measured T (from results_T.csv).
For every model / defense / pressure / secret-type cell it prints:
  T (measured), then for 3 network shapes: theoretical R0 and the chance the leak becomes an outbreak.
Saves sim_results.csv and fig_outbreak_by_model.png.   Run: python sim_measured.py
"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sim import topologies, theory_R0, stats

d = pd.read_csv(__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "results_v2r.csv", names=["model","defense","pressure","kind","hop","leaked"])
d = d[d.model != "qwen2.5:7b"]                       # incomplete model, excluded
cells = d[d.hop == 1].groupby(["model","defense","pressure","kind"]).leaked.mean().reset_index(name="T")
topo = {k: v for k, v in topologies().items() if k in ("ring (k=4)", "random (ER)", "scale-free (BA)")}
rows = []
for _, c in cells.iterrows():
    for name, G in topo.items():
        att, p_out = stats(G, c["T"], runs=200)
        rows.append({**c, "topology": name, "R0": round(theory_R0(G, c["T"]), 2),
                     "attack_size": round(att, 3), "P_outbreak": round(p_out, 2)})
out = pd.DataFrame(rows); out.to_csv("sim_results.csv", index=False)
print(out.to_string(index=False))

# headline figure: outbreak probability per DEFENSE on each topology (averaged over models/cells)
order = [x for x in ["none", "warning", "gateway_l1", "gateway"] if x in set(out.defense)]
g = out.groupby(["defense", "topology"]).P_outbreak.mean().unstack().loc[order]
g.plot(kind="bar", figsize=(7, 4)); plt.ylabel("P(outbreak)"); plt.xticks(rotation=0)
plt.title("Leak outbreak probability by defense (measured T)"); plt.tight_layout()
plt.savefig("fig_outbreak_by_defense.png", dpi=200)
print("\nmean R0 by defense and topology:\n", out.groupby(["defense", "topology"]).R0.mean().unstack().loc[order].round(2))
print(g.round(2))
