"""Summarise downstream_results.csv: accuracy, leakage and note quality per model and defense, with 95% bootstrap intervals.   Run: python downstream_summary.py downstream_results.csv"""
import sys, numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "downstream_results.csv", names=["model", "defense", "episode", "correct", "leak1", "leak2", "quality"]); rng = np.random.default_rng(0)
def ci(x): x = np.asarray(x, float); b = [rng.choice(x, len(x)).mean() for _ in range(2000)]; return np.percentile(b, [2.5, 97.5])
d["leak"] = ((d.leak1 + d.leak2) > 0).astype(int); order = [x for x in ["none", "gateway", "gateway_id", "gateway_auto", "gateway_l1"] if x in set(d.defense)]
print(f"{'defense':13s}{'n':>5s}{'answer accuracy [95% CI]':>28s}{'diagnosis leaked [95% CI]':>29s}{'note quality (1-5)':>20s}")
for o in order:
    s = d[d.defense == o]; a, l = ci(s.correct), ci(s.leak); q = pd.to_numeric(s.quality, errors="coerce")
    print(f"{o:13s}{len(s):5d}{s.correct.mean():12.3f} [{a[0]:.2f},{a[1]:.2f}]{s.leak.mean():13.3f} [{l[0]:.2f},{l[1]:.2f}]{(q.mean() if q.notna().any() else float('nan')):17.2f}")
print("\nby model:"); print(d.groupby(["model", "defense"]).agg(accuracy=("correct", "mean"), leaked=("leak", "mean")).round(3).unstack().to_string())
