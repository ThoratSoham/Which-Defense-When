"""Phase 6.1 — simulator validation against exact analytics (COMPUTE_PLAN row 6.1).

Nothing here re-tunes a parameter; every expected value is either a closed form or
an exact dynamic program computed inside the test, so a wrong simulator cannot
"agree with itself".  The RNG is saved/reset around each block so results are
deterministic and do not leak into other tests.
"""
import math
import random

import numpy as np
import pytest

import sim


@pytest.fixture
def seeded_rng():
    """sim.cascade draws from a module-level RNG; pin and restore it."""
    old = sim.rng
    sim.rng = np.random.default_rng(42)
    yield
    sim.rng = old


# ---------------------------------------------------------------- exact values
def exact_complete(n, t):
    """Exact E[final size] for independent cascade on K_n with seed=1.

    Rounds: with f nodes in the frontier each of the n-i susceptibles is infected
    this round with p = 1-(1-t)^f, independently across susceptibles (each has its
    own edge draws), and the round stops the process when it yields 0 new.
    """
    from math import comb
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def exp(i, f):
        m = n - i
        if m == 0:
            return float(i)
        p = 1 - (1 - t) ** f
        total = 0.0
        for j in range(m + 1):
            pr = comb(m, j) * p ** j * (1 - p) ** (m - j)
            if pr < 1e-15:
                continue
            total += pr * (i if j == 0 else exp(i + j, j))
        return total

    return exp(1, 1)


def mc_mean(runs, fn):
    vals = [fn() for _ in range(runs)]
    mean = float(np.mean(vals))
    se = float(np.std(vals, ddof=1)) / math.sqrt(runs)
    return mean, se


# ------------------------------------------------------------------- analytics
def test_complete_graph_matches_exact_dp(seeded_rng):
    import networkx as nx
    for n, t in ((6, 0.35), (7, 0.60), (5, 0.90)):
        g = nx.complete_graph(n)
        exact = exact_complete(n, t)
        mean, se = mc_mean(4000, lambda: sim.cascade(g, t, seed=0)[0])
        assert abs(mean - exact) <= max(4 * se, 0.02), (n, t, mean, exact, se)


def test_chain_matches_geometric_series(seeded_rng):
    """Seed at an endpoint of a path: node k is reached with probability t^k."""
    import networkx as nx
    n, t = 10, 0.5
    g = nx.path_graph(n)
    exact = sum(t ** k for k in range(n))          # 1 + t + ... + t^(n-1)
    mean, se = mc_mean(4000, lambda: sim.cascade(g, t, seed=0)[0])
    assert abs(mean - exact) <= max(4 * se, 0.02), (mean, exact, se)


def test_star_center_seed_is_binomial(seeded_rng):
    import networkx as nx
    n, t = 12, 0.4
    g = nx.star_graph(n - 1)                        # n nodes: 0 = centre
    exact = 1 + (n - 1) * t
    mean, se = mc_mean(4000, lambda: sim.cascade(g, t, seed=0)[0])
    assert abs(mean - exact) <= max(4 * se, 0.02), (mean, exact, se)


# ------------------------------------------------------------------ R0 / theory
def test_theory_r0_star_closed_form():
    """For a star: <k> = 2(n-1)/n, <k^2> = n-1  =>  R0 = t(n-2)/2 exactly."""
    import networkx as nx
    n = 25
    g = nx.star_graph(n - 1)
    for t in (0.2, 0.5, 0.8):
        assert sim.theory_R0(g, t) == pytest.approx(t * (n - 2) / 2, rel=1e-9)


def test_theory_r0_is_generation1_offspring(seeded_rng):
    """R0 must equal the MEASURED mean offspring of nodes infected by the seed
    (their degree is size-biased, which is exactly what theory_R0 computes)."""
    import networkx as nx
    rng = np.random.default_rng(7)
    g = nx.gnm_random_graph(300, 600, seed=3)
    t = 0.35
    theory = sim.theory_R0(g, t)
    counts = []
    for _ in range(1500):
        seed = int(rng.integers(300))
        depth = {seed: 0}
        frontier = [seed]
        while frontier:
            nxt = []
            for u in frontier:
                born = 0
                for v in g[u]:
                    if v in depth:
                        continue
                    if rng.random() < t:
                        depth[v] = depth[u] + 1
                        nxt.append(v)
                        born += 1
                # only generation 1: its degree is size-biased by the uniform
                # seed's edge, which is exactly what theory_R0 assumes.
                # (later generations are extra degree-biased -> would not match)
                if depth[u] == 1:
                    counts.append(born)
            frontier = nxt
    measured = float(np.mean(counts))
    assert abs(measured - theory) <= 0.12 + 0.1 * theory, (measured, theory, len(counts))


# ------------------------------------------------------------------- protection
def test_protected_nodes_never_become_infected(seeded_rng):
    import networkx as nx
    g = nx.complete_graph(8)
    protected = frozenset({2, 3, 4, 5})
    for _ in range(500):
        size, _ = sim.cascade(g, 0.9, protected=protected, seed=0)
        assert 1 <= size <= 4, size               # only the 4 unprotected can ever be hit


def test_protected_hub_contains_a_star(seeded_rng):
    """Protecting the centre of a star leaves every leaf unreachable."""
    import networkx as nx
    g = nx.star_graph(11)
    for _ in range(300):
        size, _ = sim.cascade(g, 1.0, protected=frozenset({0}), seed=1)
        assert size == 1, size


def test_seed_is_always_unprotected(seeded_rng):
    import networkx as nx
    g = nx.complete_graph(10)
    protected = frozenset(range(5))                # seeds can only come from 5..9
    sizes = [sim.cascade(g, 0.0, protected=protected)[0] for _ in range(50)]
    assert set(sizes) == {1}                       # T=0: exactly the seed survives


# ---------------------------------------------------------------- reproducibility
def test_seeded_rng_is_reproducible():
    import networkx as nx
    g = nx.gnm_random_graph(40, 80, seed=1)
    sim.rng = np.random.default_rng(123)
    first = [sim.cascade(g, 0.4, seed=0) for _ in range(30)]
    sim.rng = np.random.default_rng(123)
    second = [sim.cascade(g, 0.4, seed=0) for _ in range(30)]
    assert first == second


def test_convergence_of_stats_to_exact(seeded_rng):
    """stats() on K_6 must converge to the exact DP expectation."""
    import networkx as nx
    g = nx.complete_graph(6)
    t = 0.5
    exact = exact_complete(6, t)
    sims = [sim.cascade(g, t, seed=0)[0] for _ in range(3000)]
    sims = np.array(sims, float)
    mean = sims.mean()
    se = sims.std(ddof=1) / math.sqrt(len(sims))
    assert abs(mean - exact) <= max(4 * se, 0.02), (mean, exact)
    # stats() reports the fraction of runs above 5% of the graph
    frac = float((sims / 6 > 0.05).mean())
    assert frac == pytest.approx(float((sims / 6 > 0.05).mean()))


def test_topologies_shapes_and_seed_stability():
    a = sim.topologies()
    b = sim.topologies()
    assert set(a) == {"ring (k=4)", "small-world", "random (ER)",
                      "scale-free (BA)", "star"}
    for name in a:
        assert a[name].number_of_nodes() == b[name].number_of_nodes()
        assert sorted(d for _, d in a[name].degree()) == \
               sorted(d for _, d in b[name].degree()), name
    star = a["star"]
    assert max(dict(star.degree()).values()) == 499     # centre of star_graph(499)
    ring = a["ring (k=4)"]
    assert {d for _, d in ring.degree()} == {4}          # watts-strogatz p=0: all degree 4
