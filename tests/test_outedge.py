"""Tests for the Phase 6.2 out-edge correlation statistic (synthetic data only:
the statistic must be right before it is pointed at real transcripts)."""
import random

import pytest

import outedge_correlation as oc


def _episodes(make_sib, n_eps=400, m=4, strata=(("cellA", 1),)):
    """n_eps episodes per stratum, each with m siblings."""
    eps = []
    rng = random.Random(0)
    for s in strata:
        for _ in range(n_eps):
            eps.append({"stratum": s, "sib": make_sib(rng, m)})
    return eps


def test_independent_draws_give_phi_near_zero():
    eps = _episodes(lambda rng, m: [1 if rng.random() < 0.3 else 0 for _ in range(m)])
    phi, num, den = oc.phi_stratified(eps)
    assert den > 0
    assert abs(phi) < 0.1, phi
    lo, hi = oc.bootstrap_ci(eps, n=500)
    assert lo < 0 < hi, (lo, hi)


def test_broadcast_gives_phi_near_one():
    def broadcast(rng, m):
        z = 1 if rng.random() < 0.4 else 0      # one shared coin for the episode
        return [z] * m
    eps = _episodes(broadcast)
    phi, _, _ = oc.phi_stratified(eps)
    assert phi > 0.9, phi
    lo, hi = oc.bootstrap_ci(eps, n=500)
    assert lo > 0.5, (lo, hi)
    pval, null = oc.permutation_pvalue(eps, phi, n=300)
    assert pval is not None and pval < 0.01, pval
    assert abs(sum(null) / len(null)) < 0.1     # null centers near 0


def test_partial_correlation_is_recovered_with_right_sign():
    """Each episode: sibling leaks are iid EXCEPT a shared 50% 'mood' factor that
    makes all four agree half the time -> phi should land between 0 and 1."""
    def moody(rng, m):
        if rng.random() < 0.5:
            z = 1 if rng.random() < 0.5 else 0
            return [z] * m
        return [1 if rng.random() < 0.3 else 0 for _ in range(m)]
    eps = _episodes(moody)
    phi, _, _ = oc.phi_stratified(eps)
    assert 0.3 < phi < 1.0, phi


def test_stratification_is_simpson_safe():
    """Siblings are iid WITHIN each stratum, but the two strata have very
    different marginals (0.05 vs 0.95). A naive pooled phi reports strong
    POSITIVE correlation from the mixture alone (E[p^2] >= E[p]^2); the
    stratified phi must stay near zero. This is why the real analysis is
    stratified by cell and parent state instead of pooled."""
    def iid_p(p):
        return lambda rng, m: [1 if rng.random() < p else 0 for _ in range(m)]
    eps = _episodes(iid_p(0.05), n_eps=400, strata=(("low", 1),)) + \
          _episodes(iid_p(0.95), n_eps=400, strata=(("high", 1),))
    phi, _, _ = oc.phi_stratified(eps)
    assert abs(phi) < 0.08, phi

    flat = [x for e in eps for x in e["sib"]]
    p_all = sum(flat) / len(flat)
    joint = sum(e["sib"][i] * e["sib"][j] for e in eps
                for i in range(4) for j in range(i + 1, 4))
    joint /= len(eps) * 6
    naive = (joint - p_all ** 2) / (p_all * (1 - p_all))
    assert naive > 0.3, naive         # pooled would fake strong *positive* correlation


def test_shuffle_preserves_marginals_and_sizes():
    eps = _episodes(lambda rng, m: [1 if rng.random() < 0.5 else 0
                                    for _ in range(m)], n_eps=60)
    import numpy as np
    rng = np.random.default_rng(3)
    sh = oc._shuffle_within(eps, rng)
    assert [len(e["sib"]) for e in sh] == [len(e["sib"]) for e in eps]
    assert sorted(x for e in sh for x in e["sib"]) == \
           sorted(x for e in eps for x in e["sib"])
