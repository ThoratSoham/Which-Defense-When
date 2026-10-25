"""Leak rate vs task success per defense.  Run: python pareto.py results_v2.csv"""
import sys, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, os
F = sys.argv[1] if len(sys.argv) > 1 else "results_T.csv"; stem = os.path.splitext(F)[0]
r = pd.read_csv(F, names=["model","defense","pressure","kind","hop","leaked"]); r = r[(r.hop == 1) & (r.model != "qwen2.5:7b")]
k = pd.read_csv(stem + "_task.csv", names=["model","defense","pressure","kind","episode","task_ok"])
t = pd.DataFrame({"T": r.groupby("defense").leaked.mean(), "task_success": k.groupby("defense").task_ok.mean()}).round(3)
print(t.to_string())
import numpy as np
rng = np.random.default_rng(0)
LAB = {"none": "no defense", "warning": "prompt warning", "gateway_l1": "L1 exact match", "gateway": "L1+L2 gateway"}
def ci(x, n=2000): b = [rng.choice(x, len(x)).mean() for _ in range(n)]; return np.percentile(b, [2.5, 97.5])
plt.figure(figsize=(5.4, 4.2))
for d in t.index:
    x, y = r[r.defense == d].leaked.values, k[k.defense == d].task_ok.values; (xl, xh), (yl, yh) = ci(x), ci(y)
    plt.errorbar(x.mean(), y.mean(), xerr=[[x.mean() - xl], [xh - x.mean()]], yerr=[[y.mean() - yl], [yh - y.mean()]], fmt="o", capsize=3)
    plt.annotate(LAB.get(d, d), (x.mean(), y.mean()), textcoords="offset points", xytext=(6, 6), fontsize=8)
plt.ylim(0.8, 1.0); plt.xlim(-0.03, 0.8)      # full-scale y-axis: the differences in task success are tiny
plt.xlabel("leak rate T (lower is better), 95% CI"); plt.ylabel("task-success proxy (higher is better), 95% CI")
plt.tight_layout(); plt.savefig("fig_pareto.png", dpi=220)
