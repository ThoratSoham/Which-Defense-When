#!/usr/bin/env python
"""Phase 3 / H3 heterogeneity — beta-binomial random-effects analysis of slip
incidence over secrets, with per-model pools (PREREG §1 H3 "heterogeneity"
clause and §4 statistics plan).

For every pool (one pool = one parole-source model):

  * per-secret slip counts (n_s, k_s)
  * beta-binomial MLE (a, b) over secrets  ->  mean slip rate, ICC = 1/(a+b+1)
    (the beta-binomial ICC is the between-secret overdispersion; with >=2 pools
    the same fit is done per model and the model-level dispersion is reported)
  * leave-one-secret-out: fit on all but one secret, predict the held-out
    secret's slip count -> prediction error (log score + absolute rate error),
    the pre-registered LOO check
  * Clopper-Pearson interval on the aggregate rate

Honesty rule: with one pool the model-level ICC is undefined and the script
says so instead of printing a number. Nothing here is tuned; the only inputs
are the pool files.

Run:
  python heterogeneity.py                       # every boundary pool on disk
  python heterogeneity.py --pools a.jsonl b.jsonl

Writes results/heterogeneity.json and prints a readout.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import betabinom


def pool_rows(path: str):
    rows = {}
    p = Path(path)
    if not p.exists():
        return []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows[(r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))] = r
    return list(rows.values())


def model_of(path: str) -> str:
    rows = pool_rows(path)
    models = {r.get("model") for r in rows}
    if len(models) == 1:
        return next(iter(models))
    return Path(path).stem


def per_secret(rows, field="slip"):
    out = {}
    for r in rows:
        sid = r.get("secret_id")
        n, k = out.get(sid, (0, 0))
        out[sid] = (n + 1, k + int(bool(r.get(field))))
    return out


def fit_betabinom(counts):
    """MLE of (a, b) for beta-binomial with per-secret n from counts dict."""
    ns = np.array([n for n, k in counts.values()], dtype=float)
    ks = np.array([k for n, k in counts.values()], dtype=float)

    def nll(theta):
        a, b = np.exp(theta)
        if not np.isfinite(a + b):
            return 1e12
        try:
            return -float(np.sum(betabinom.logpmf(ks, ns, a, b)))
        except (ValueError, FloatingPointError):
            return 1e12

    # method-of-moments start
    rates = ks / np.maximum(ns, 1)
    m = rates.mean()
    v = rates.var() if len(rates) > 1 else m * (1 - m)
    if 0 < m < 1 and 0 < v < m * (1 - m):
        common = m * (1 - m) / v - 1
        start = np.log([max(m * common, 0.5), max((1 - m) * common, 0.5)])
    else:
        start = np.log([1.0, 1.0])
    res = minimize(nll, start, method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-8, "fatol": 1e-8})
    a, b = np.exp(res.x)
    return float(a), float(b), float(res.fun)


def clopper(k, n, alpha=0.05):
    from scipy.stats import beta as beta_dist
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def _fit_summary(counts):
    """Beta-binomial fit + LOO + Clopper-Pearson for one per-secret count map."""
    n_total = sum(n for n, k in counts.values())
    k_total = sum(k for n, k in counts.values())
    a, b, nll = fit_betabinom(counts)
    icc = 1.0 / (a + b + 1.0)
    lo, hi = clopper(k_total, n_total)

    secrets = sorted(counts)
    loo_abs, loo_log = [], []
    for s in secrets:
        train = {k_: v for k_, v in counts.items() if k_ != s}
        if len(train) < 3:
            continue
        a_t, b_t, _ = fit_betabinom(train)
        n_s, k_s = counts[s]
        pred_mean = a_t / (a_t + b_t)
        loo_abs.append(abs(pred_mean - k_s / n_s))
        loo_log.append(float(-betabinom.logpmf(k_s, n_s, a_t, b_t)))

    return {
        "n_notes": n_total, "n_slips": k_total,
        "rate": k_total / n_total if n_total else float("nan"),
        "ci": [lo, hi],
        "beta_a": a, "beta_b": b, "icc_secret": icc,
        "nll": nll,
        "loo_mean_abs_error": float(np.mean(loo_abs)) if loo_abs else None,
        "loo_mean_neglogscore": float(np.mean(loo_log)) if loo_log else None,
        "n_secrets": len(secrets),
        "per_secret": {s: {"n": counts[s][0], "slips": counts[s][1],
                           "rate": counts[s][1] / counts[s][0]}
                       for s in secrets},
    }


def analyze_pool(path: str) -> dict:
    rows = pool_rows(path)
    out = {"pool": str(path), "model": model_of(path),
           **_fit_summary(per_secret(rows, "slip"))}
    # H3 conditions on leak-survived (slip_survived, written by slip_rescore);
    # report its ICC/LOO alongside the plain gate-pass rates.
    if any("slip_survived" in r for r in rows):
        out["survived"] = {
            "conditioning": "slip_survived (gate-pass AND D1 leak)",
            **_fit_summary(per_secret(rows, "slip_survived"))}
    else:
        out["survived"] = None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", nargs="*", default=None)
    a = ap.parse_args()
    pools = a.pools or sorted(
        glob.glob("results/slip_gen_v3_boundary*_dev.jsonl"))
    pools = [p for p in pools if Path(p).exists()]
    if not pools:
        raise SystemExit("no pool files found")

    out = {"pools": [analyze_pool(p) for p in pools], "model_level": None}
    print(f"{'model':16s} {'n':>5s} {'slips':>6s} {'rate':>6s} "
          f"{'95% CI':>16s} {'ICC(secret)':>12s} {'LOO err':>8s}")
    for r in out["pools"]:
        ci = f"[{r['ci'][0]:.3f},{r['ci'][1]:.3f}]"
        looe = ("  n/a" if r["loo_mean_abs_error"] is None
                else f"{r['loo_mean_abs_error']:.3f}")
        print(f"{r['model'][:16]:16s} {r['n_notes']:5d} {r['n_slips']:6d} "
              f"{r['rate']:6.3f} {ci:>16s} {r['icc_secret']:12.3f} {looe:>8s}")
        sv = r.get("survived")
        if sv:
            svci = f"[{sv['ci'][0]:.3f},{sv['ci'][1]:.3f}]"
            svloo = ("  n/a" if sv['loo_mean_abs_error'] is None
                     else f"{sv['loo_mean_abs_error']:.3f}")
            # ASCII only: the console codepage (cp1252) cannot encode the box
            # character and crashed this step with UnicodeEncodeError.
            print(f"{'' :16s}   - survived: {sv['n_notes']:5d} "
                  f"{sv['n_slips']:6d} {sv['rate']:6.3f} {svci:>16s} "
                  f"{sv['icc_secret']:12.3f} {svloo:>8s}")

    if len(out["pools"]) >= 2:
        rates = [r["rate"] for r in out["pools"]]
        m = float(np.mean(rates))
        var = float(np.var(rates, ddof=1))
        # crude between-model dispersion on the logit scale, reported as-is
        logits = [math.log(x / (1 - x)) for x in rates if 0 < x < 1]
        out["model_level"] = {
            "n_models": len(rates),
            "rates": rates,
            "between_model_var_logit": float(np.var(logits, ddof=1)) if len(logits) > 1 else None,
            "note": "with n_models=2 this is a descriptive dispersion, not a fitted random effect",
        }
        print(f"\nbetween-model rates: {rates}  "
              f"var(logits)={out['model_level']['between_model_var_logit']}")

        # Do the SAME secrets stay hard under the second model?
        # Pearson r on per-secret rates + Spearman rho on their ranks
        # (midranks for ties: qwen has 7 zero-slip secrets).
        ps = [r["per_secret"] for r in out["pools"]]
        keys = sorted(set(ps[0]) & set(ps[1]))
        if len(keys) >= 3:
            xs = [ps[0][k]["rate"] for k in keys]
            ys = [ps[1][k]["rate"] for k in keys]

            def _midranks(v):
                order = sorted(range(len(v)), key=lambda i: v[i])
                rk = [0.0] * len(v)
                i = 0
                while i < len(order):
                    j = i
                    while (j < len(order)
                           and v[order[j]] == v[order[i]]):
                        j += 1
                    avg = (i + j - 1) / 2.0 + 1.0
                    for t in range(i, j):
                        rk[order[t]] = avg
                    i = j
                return rk

            def _corr(u, v):
                mu, mv = float(np.mean(u)), float(np.mean(v))
                du = [x - mu for x in u]
                dv = [x - mv for x in v]
                den = math.sqrt(sum(d * d for d in du) * sum(d * d for d in dv))
                return (sum(a * b for a, b in zip(du, dv)) / den
                        if den else None)

            agree = {
                "n_secrets": len(keys),
                "pearson_r": _corr(xs, ys),
                "spearman_rho": _corr(_midranks(xs), _midranks(ys)),
                "zero_slip_secrets": {
                    out["pools"][i]["model"]: sum(1 for x in
                        (xs if i == 0 else ys) if x == 0)
                    for i in range(len(out["pools"]))},
            }
            out["model_level"]["per_secret_agreement"] = agree
            print(f"per-secret cross-model: pearson r={agree['pearson_r']:.3f} "
                  f"spearman rho={agree['spearman_rho']:.3f} "
                  f"({agree['n_secrets']} secrets)")
    else:
        out["model_level"] = {"n_models": len(out["pools"]),
                              "note": "model-level ICC undefined with a single pool; "
                                      "run the qwen2.5:3b replication pool first"}
        print("\nmodel-level ICC: UNDEFINED (single pool) — qwen replication needed")

    Path("results/heterogeneity.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote results/heterogeneity.json")


if __name__ == "__main__":
    main()
