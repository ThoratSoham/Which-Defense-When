#!/usr/bin/env python
"""
Live progress + slip-rate + Clopper-Pearson readout for
results/slip_gen_v3_boundary_dev.jsonl.
"""
from __future__ import annotations
import json, pathlib
from collections import Counter
from math import lgamma, exp, log

p = pathlib.Path("results/slip_gen_v3_boundary_dev.jsonl")
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
if not rows:
    print("no rows yet")
    raise SystemExit

n = len(rows)
slips = [r for r in rows if r.get("slip")]
ns = len(slips)
by_variant = Counter(r["prompt_variant"] for r in rows)
by_variant_slips = Counter(r["prompt_variant"] for r in slips)

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
        # derivative = x^{a-1} (1-x)^{b-1} / B(a,b)
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
    """Exact one-sided Clopper-Pearson upper bound using the F-distribution,
    which is exact for integer x, n.  No scipy needed."""
    if x == 0:
        return 1 - alpha ** (1 / n)
    if x == n:
        return 1.0
    d1 = 2 * (x + 1)
    d2 = 2 * (n - x)
    # F_{1-alpha}(d1, d2) = 1 / F_{alpha}(d2, d1); invert the regularized
    # incomplete beta at alpha with a=d2/2, b=d1/2.
    beta_q = _inv_reg_inc_beta(alpha, d2 / 2, d1 / 2)
    f_val = (d2 / d1) * (beta_q / (1 - beta_q))
    return 1 / (1 + (n - x) / ((x + 1) * f_val))

print(f"n = {n}, slips = {ns}")
print(f"slip rate = {ns/n:.4f}  ({ns}/{n})")
ub = clopper_upper(ns, n)
print(f"95% one-sided Clopper-Pearson upper bound on slip probability: {ub:.5f}  ({ub*100:.3f}%)")
print(f"by variant: {dict(by_variant)}")
print(f"by variant slips: {dict(by_variant_slips)}")
print()
print("=== slip rows ===")
for r in slips:
    print(f"  {r['secret_id']}  {r['prompt_variant']}  t{r['trial_index']}  "
          f"l2={r['l2_hit']} lex={r['lexical_hit']} slip={r['slip']} "
          f"len={len(r['note'])}  err={r['err']}")

print()
print(f"jsonl bytes: {p.stat().st_size}")
