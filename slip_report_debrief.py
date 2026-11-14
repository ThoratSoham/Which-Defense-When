#!/usr/bin/env python
"""
Debrief readout for the DEV slip boundary run.
Summarizes by secret, by variant, and by gate.
"""
from __future__ import annotations
import json, pathlib
from collections import Counter, defaultdict
from math import lgamma, exp, log

def _log_beta(a, b):
    return lgamma(a) + lgamma(b) - lgamma(a + b)

def _reg_inc_beta(x, a, b, maxit=200, tol=1e-12):
    """Regularized incomplete beta I_x(a,b) via Lentz's continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    if x > (a + 1) / (a + b + 2):
        return 1 - _reg_inc_beta(1 - x, b, a, maxit, tol)
    lbeta = _log_beta(a, b)
    front = exp(a * log(x) + b * log(1 - x) - lbeta - log(a)) if a > 0 else 0.0
    tiny = 1e-30
    f = 1.0
    C = 1.0
    D = tiny
    delta = C * D
    m = 1
    while abs(delta - 1.0) > tol and m <= maxit:
        if m % 2 == 0:
            k = m // 2
            num = -(a + k - 1) * (a + b + k - 1) * x
            den = (a + 2*k - 2) * (a + 2*k - 1)
            d = (num / den) if den != 0 else 0.0
        else:
            k = (m + 1) // 2
            num = (k - 1) * (b - k + 1)
            den = (a + 2*k - 3) * (a + 2*k - 2)
            d = (num / den) if den != 0 else 0.0
        if d == 0:
            D = tiny
        else:
            D = d + 1.0 / D
        if D == 0:
            D = tiny
        C = d + 1.0 / C
        if C == 0:
            C = tiny
        delta = C * D
        f *= delta
        m += 1
    return front * f

def _inv_reg_inc_beta(p, a, b, maxit=300, tol=1e-12):
    """Inverse: find x such that I_x(a,b) = p via Newton + CF forward."""
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    mean = a / (a + b)
    x = mean
    for _ in range(maxit):
        ib = _reg_inc_beta(x, a, b, maxit=80, tol=tol)
        diff = ib - p
        if abs(diff) < tol:
            return x
        if x <= 0 or x >= 1:
            return x
        deriv = exp((a - 1) * log(x) + (b - 1) * log(1 - x) - _log_beta(a, b))
        if deriv == 0:
            x = x + (0.5 if diff < 0 else -0.5) * 0.1
            continue
        step = diff / deriv
        if abs(step) > 0.5:
            step = 0.5 * (step / abs(step))
        x_new = x - step
        if x_new <= 0:
            x_new = x * 0.5
        if x_new >= 1:
            x_new = 1 - (1 - x) * 0.5
        if abs(x_new - x) < tol:
            return x_new
        x = x_new
    return x

def clopper_upper(x, n, alpha=0.05):
    """Upper limit of the exact two-sided (1-alpha) Clopper-Pearson interval.

    2026-10-27: the previous hand-rolled F-distribution/inverse-reg-inc-beta
    implementation was WRONG (it returned 0.8652 for x=209, n=1600 where the
    exact bound is ~0.147, and swapped bounds on per-secret lines).  Replaced
    by the exact scipy beta quantile — scipy is already a project dependency
    (heterogeneity.py)."""
    from scipy.stats import beta as _bd
    return 1.0 if x >= n else float(_bd.ppf(1 - alpha / 2, x + 1, n - x))

def clopper_lower(x, n, alpha=0.05):
    """Lower limit of the exact two-sided (1-alpha) Clopper-Pearson interval."""
    from scipy.stats import beta as _bd
    return 0.0 if x <= 0 else float(_bd.ppf(alpha / 2, x, n - x + 1))

p = pathlib.Path("results/slip_gen_v3_boundary_dev.jsonl")
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
if not rows:
    print("no rows yet")
    raise SystemExit

n = len(rows)
slips = [r for r in rows if r.get("slip")]
ns = len(slips)
by_secret = defaultdict(list)
by_variant = Counter()
by_variant_slips = Counter()
l2_caught = 0
lex_caught = 0
for r in rows:
    by_secret[r["secret_id"]].append(r)
    by_variant[r["prompt_variant"]] += 1
    if r.get("slip"):
        by_variant_slips[r["prompt_variant"]] += 1
    else:
        if r["l2_hit"]:
            l2_caught += 1
        if r["lexical_hit"]:
            lex_caught += 1

print(f"n = {n}, slips = {ns}")
_errs = [r for r in rows if r.get("err")]
_empt = [r for r in rows if not r.get("note") and not r.get("err")]
print(f"flow: {len(_errs)} failed generations (err set; kept as NON-leaks, PREREG "
      f"rule 2; retried on the next invocation)  {len(_empt)} empty notes without err")
print(f"n_valid = {n - len(_errs) - len(_empt)} notes with content ({len(_errs) + len(_empt)} excluded from content analysis but kept in n)")
print(f"slip rate = {ns/n:.4f}  ({ns}/{n})")
ub = clopper_upper(ns, n)
lb = clopper_lower(ns, n)
print(f"95% two-sided Clopper-Pearson CI on slip probability: [{lb:.4f}, {ub:.4f}]  ([{lb*100:.2f}%, {ub*100:.2f}%])")
print("by variant (notes / slips):")
for v in sorted(by_variant):
    vv = by_variant[v]
    sv = by_variant_slips.get(v, 0)
    if vv > 0:
        vr = sv / vv
        vub = clopper_upper(sv, vv)
        vlb = clopper_lower(sv, vv)
        print(f"  {v:10s}  {vv:4d}  slip {sv:2d}  rate {vr:.3f}  95%CI [{vlb:.3f},{vub:.3f}]")
    else:
        print(f"  {v:10s}  {vv:4d}  slip 0")
print(f"L2-caught (of all notes): {l2_caught}")
print(f"lexical-caught (of all notes): {lex_caught}")
print()
print("=== by secret ===")
for sid in sorted(by_secret):
    rs = by_secret[sid]
    ss = [r for r in rs if r.get("slip")]
    s = len(ss)
    n_s = len(rs)
    r_s = s / n_s if n_s else 0
    s_ub = clopper_upper(s, n_s)
    s_lb = clopper_lower(s, n_s)
    print(f"{sid:10s}  n={n_s:3d}  slip={s:2d}  rate {r_s:.3f}  95%CI [{s_lb:.3f},{s_ub:.3f}]  "
          f"l2_clear={sum(1 for r in rs if not r['l2_hit']):3d}  "
          f"lex_clear={sum(1 for r in rs if not r['lexical_hit']):3d}")
print()
print("=== slip rate by secret (where n>=1) ===")
for sid in sorted(by_secret):
    rs = by_secret[sid]
    ss = [r for r in rs if r.get("slip")]
    s = len(ss)
    n_s = len(rs)
    if n_s:
        print(f"{sid:10s}  {s}/{n_s}  {100*s/n_s:.1f}%")
    else:
        print(f"{sid:10s}  0/0  n/a")
print()
print("=== slip rows ===")
for r in slips:
    print(f"  {r['secret_id']}  {r['prompt_variant']}  t{r['trial_index']}  "
          f"l2={r['l2_hit']} lex={r['lexical_hit']} slip={r['slip']} "
          f"len={len(r['note'])}  err={r['err']}")
print()
print(f"jsonl bytes: {p.stat().st_size}")
