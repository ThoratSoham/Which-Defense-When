"""Summarise grid_results.csv: leak rate T (hop 1) overall and by secret, task, framing, pressure and model, for each defense.   Run: python grid_summary.py grid_results.csv"""
import sys, numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "grid_results.csv", names=["model", "defense", "secret", "task", "framing", "pressure", "episode", "hop", "leaked"]); d = d[d.hop == 1]; rng = np.random.default_rng(0)
def ci(x): b = [rng.choice(x, len(x)).mean() for _ in range(2000)]; return np.percentile(b, [2.5, 97.5])
order = [x for x in ["none", "gateway_l1", "gateway", "gateway_id", "gateway_auto"] if x in set(d.defense)]
print("overall T per defense:"); [print(f"  {o:13s} n={len(d[d.defense == o]):5d}  T={d[d.defense == o].leaked.mean():.3f}  95% CI [{ci(d[d.defense == o].leaked.values)[0]:.3f}, {ci(d[d.defense == o].leaked.values)[1]:.3f}]") for o in order]
for f in ("model", "secret", "task", "framing", "pressure"):
    t = d.groupby([f, "defense"]).leaked.mean().unstack()[order]; print(f"\nT by {f}:\n{t.round(3).to_string()}")
    nn = t["none"]; print(f"  spread of T without defense across {f}: min {nn.min():.2f}, max {nn.max():.2f}")
