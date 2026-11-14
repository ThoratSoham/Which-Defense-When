"""Layer 2: Monte Carlo leak-epidemic simulation on agent networks.
Independent-cascade model: each newly infectious agent passes the secret to each
susceptible neighbour with probability T (one task episode). Protected agents never transmit/receive.
Run: python sim.py   -> prints tables, saves fig_*.png
"""
import numpy as np, networkx as nx, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
rng = np.random.default_rng(42)
N, RUNS = 500, 400

def topologies(n=N):
    return {
        "ring (k=4)":      nx.watts_strogatz_graph(n, 4, 0.0, seed=1),
        "small-world":     nx.watts_strogatz_graph(n, 4, 0.1, seed=1),
        "random (ER)":     nx.gnm_random_graph(n, 2*n, seed=1),
        "scale-free (BA)": nx.barabasi_albert_graph(n, 2, seed=1),
        "star":            nx.star_graph(n-1),
    }

def cascade(G, T, protected=frozenset(), seed=None):
    """Returns (attack_size, offspring_of_seed). Seed = random unprotected node."""
    nodes = [v for v in G if v not in protected]
    s = seed if seed is not None else nodes[rng.integers(len(nodes))]
    infected, frontier, seed_off = {s}, [s], 0
    first = True
    while frontier:
        nxt = []
        for u in frontier:
            for v in G[u]:
                if v in infected or v in protected: continue
                if rng.random() < T:
                    infected.add(v); nxt.append(v)
                    if first: seed_off += 1
        first = False; frontier = nxt
    return len(infected), seed_off

def theory_R0(G, T):
    k = np.array([d for _, d in G.degree()], float)
    return T * ((k**2).mean() - k.mean()) / k.mean()


def phase3_rho(min_n=100):
    """Phase 3 rewrite persistence (rho) from results/numbers.json — the measured
    replacement for the old n=20 relay estimate ("0.95").

    Returns (rate, n, ci95) or None when the Phase 3 rewrite arm is absent or
    incomplete (fewer than min_n observations): callers then fall back to the
    legacy transcript-derived estimate so an unfinished run never silently
    replaces a paper number."""
    try:
        import json
        d = json.load(open("results/numbers.json", encoding="utf-8"))
        rw = d["persistence"]["rewrite"]["llama3.2:3b"]["slip"]
        if int(rw.get("n") or 0) >= min_n:
            return float(rw["rate"]), int(rw["n"]), [float(x) for x in rw["ci"]]
    except Exception:
        pass
    return None

def stats(G, T, protected=frozenset(), runs=RUNS):
    sizes = np.array([cascade(G, T, protected)[0] for _ in range(runs)]) / G.number_of_nodes()
    return sizes.mean(), (sizes > 0.05).mean()   # mean attack size, outbreak probability

if __name__ == "__main__":
    topo = topologies()
    # --- H1: R0 and attack size vs topology at T=0.3
    print("\n[H1] T=0.30 | topology | <k> | R0_theory | mean attack size | P(outbreak>5%)")
    for name, G in topo.items():
        k = np.mean([d for _, d in G.degree()])
        a, p = stats(G, 0.30)
        print(f"{name:16s} {k:5.2f} {theory_R0(G,0.30):7.2f} {a:8.3f} {p:8.2f}")
    # --- attack size vs T curves
    Ts = np.linspace(0.02, 0.8, 14)
    plt.figure(figsize=(6,4))
    for name, G in topo.items():
        plt.plot(Ts, [stats(G, t, runs=150)[0] for t in Ts], marker="o", ms=3, label=name)
    plt.xlabel("per-hop transmissibility T"); plt.ylabel("mean attack size (fraction)")
    plt.legend(); plt.tight_layout(); plt.savefig("fig_attack_vs_T.png", dpi=200)
    # --- H3: hub-first vs random protection, scale-free + ER
    print("\n[H3] protected fraction needed so P(outbreak)<5%  (T=0.35)")
    fig, ax = plt.subplots(1, 2, figsize=(9,3.6))
    for i, name in enumerate(["scale-free (BA)", "random (ER)"]):
        G = topo[name]; order = [v for v,_ in sorted(G.degree(), key=lambda x:-x[1])]
        ps = np.linspace(0, 0.6, 13); rnd, hub = [], []
        for p in ps:
            m = int(p*N)
            rnd.append(np.mean([stats(G, 0.35, frozenset(rng.choice(N, m, replace=False)), runs=60)[1] for _ in range(1)]))
            hub.append(stats(G, 0.35, frozenset(order[:m]), runs=60)[1])
        thr = lambda c: next((p for p, v in zip(ps, c) if v < 0.05), float("nan"))
        print(f"{name:16s} random: {thr(rnd):.2f}   hub-first: {thr(hub):.2f}   homogeneous 1-1/R0: {max(0,1-1/theory_R0(G,0.35)):.2f}")
        ax[i].plot(ps, rnd, label="random"); ax[i].plot(ps, hub, label="hub-first")
        ax[i].set_title(name); ax[i].set_xlabel("fraction protected"); ax[i].set_ylabel("P(outbreak)"); ax[i].legend()
    plt.tight_layout(); plt.savefig("fig_herd_threshold.png", dpi=200)
