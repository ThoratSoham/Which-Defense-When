"""Final statistics for the ablation ladder.  Run: python stats_ladder.py results_v2r.csv
Prints: T per defense with bootstrap 95% CI, T per model x defense, pairwise differences with effect size (Cohen's h),
permutation p-values and Holm-corrected p-values."""
import sys, itertools, numpy as np, pandas as pd
F = sys.argv[1] if len(sys.argv) > 1 else "results_v2r.csv"
d = pd.read_csv(F, names=["model","defense","pressure","kind","hop","leaked"]); d = d[(d.hop == 1) & (d.model != "qwen2.5:7b")]
order = [x for x in ["none", "warning", "gateway_l1", "gateway"] if x in set(d.defense)]; rng = np.random.default_rng(0)
def ci(x, n=5000): b = [rng.choice(x, len(x)).mean() for _ in range(n)]; return np.percentile(b, [2.5, 97.5])
print("Leak rate T per defense (hop 1, all models/pressures/secret types pooled):")
for o in order:
    x = d[d.defense == o].leaked.values; lo, hi = ci(x); print(f"  {o:11s} n={len(x):4d}  T={x.mean():.3f}  95% CI [{lo:.3f}, {hi:.3f}]")
print("\nT per model:"); print(d.groupby(["model", "defense"]).leaked.mean().unstack()[order].round(3).to_string())
print("\nT per secret type:"); print(d.groupby(["kind", "defense"]).leaked.mean().unstack()[order].round(3).to_string())
h = lambda a, b: 2 * np.arcsin(np.sqrt(a)) - 2 * np.arcsin(np.sqrt(b))
pairs = [p for p in itertools.combinations(order, 2)]; res = []
for a, b in pairs:
    x, y = d[d.defense == a].leaked.values, d[d.defense == b].leaked.values; obs = x.mean() - y.mean(); pool = np.concatenate([x, y]); cnt = 0
    for _ in range(5000):
        rng.shuffle(pool); cnt += abs(pool[:len(x)].mean() - pool[len(x):].mean()) >= abs(obs)
    res.append([a, b, obs, h(x.mean(), y.mean()), (cnt + 1) / 5001])
order_p = sorted(range(len(res)), key=lambda i: res[i][4]); m = len(res); adj = [0] * m; run = 0
for rank, i in enumerate(order_p): run = max(run, min(1, (m - rank) * res[i][4])); adj[i] = run
print(f"\n{'comparison':26s}{'diff in T':>10s}{'Cohen h':>9s}{'p (perm)':>10s}{'p (Holm)':>10s}")
for (a, b, df, ch, p), ap in zip(res, adj): print(f"{a + ' vs ' + b:26s}{df:10.3f}{ch:9.2f}{p:10.4f}{ap:10.4f}")
