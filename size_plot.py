"""Leak rate T against model size, no defense vs gateway.   Run: python size_plot.py results_v2r.csv results_v3r.csv     (any number of rescored files)
Edit SIZES (billions of parameters) for hosted models whose size is not public; points with an unknown size are skipped and listed."""
import re, sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
SIZES = {"gemma2:2b": 2, "llama3.2:3b": 3, "qwen2.5:3b": 3, "qwen2.5:7b": 7, "openrouter:meta-llama/llama-3.1-8b-instruct": 8, "openrouter:meta-llama/llama-3.1-70b-instruct": 70}
d = pd.concat([pd.read_csv(f, names=["model", "defense", "pressure", "kind", "hop", "leaked"]) for f in sys.argv[1:]]); d = d[d.hop == 1]; rng = np.random.default_rng(0)
def size(m):
    if m in SIZES: return SIZES[m]
    g = re.search(r"(\d+(?:\.\d+)?)b\b", m.lower()); return float(g.group(1)) if g else None
def ci(x): b = [rng.choice(x, len(x)).mean() for _ in range(2000)]; return np.percentile(b, [2.5, 97.5])
plt.figure(figsize=(5.6, 4.2)); skipped = set(); tab = []
for defense, c in (("none", "C3"), ("gateway", "C2")):
    xs, ys, lo, hi = [], [], [], []
    for m, g in d[d.defense == defense].groupby("model"):
        s = size(m)
        if s is None: skipped.add(m); continue
        v = g.leaked.values; l, h = ci(v); xs.append(s); ys.append(v.mean()); lo.append(v.mean() - l); hi.append(h - v.mean()); tab.append((defense, m, s, round(v.mean(), 3), len(v))); plt.annotate(m.split("/")[-1][:18], (s, v.mean()), fontsize=5, xytext=(3, 3), textcoords="offset points")
    o = np.argsort(xs); plt.errorbar(np.array(xs)[o], np.array(ys)[o], yerr=[np.array(lo)[o], np.array(hi)[o]], fmt="o-", c=c, capsize=2, label={"none": "no defense", "gateway": "L1+L2 gateway"}[defense], ms=4)
plt.xscale("log"); plt.xlabel("model size (billions of parameters, log scale)"); plt.ylabel("per-hop leak rate T (95% CI)"); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig("fig_size.png", dpi=200)
print(pd.DataFrame(tab, columns=["defense", "model", "size_B", "T", "n"]).to_string(index=False)); print("wrote fig_size.png" + (f"   (skipped, unknown size: {sorted(skipped)})" if skipped else ""))
