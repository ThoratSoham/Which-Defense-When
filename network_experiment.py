#!/usr/bin/env python
"""Phase 6.3 / 6.4 — real 10–12-agent network runs on the new corpus (PREREG H5).

Design, fixed BEFORE any TEST run (logged in PREREG.md Amendments):

  6.3 (H5b, H5a fit/validation)  3 held-out topologies (ring12, er12, ba12) x
      2 defenses (none, gateway) x 30 episodes x 11 calls = 1 980 calls,
      1 model (llama3.2:3b), 1 source position (fixed random position per
      topology — Tier B adds the hub position).  The simulator is fitted ONLY
      on ladder chains (and star runs if approved); these topologies are never
      seen by the fit, which is what "held-out" means in H5b.
  6.4 (H5a)  partial protection on ba12 (scale-free): 4 protected fractions
      (0.25 / 0.5 / 0.75 / 1.0) x 2 placements (hub-first / random) x 30
      episodes x 11 calls = 2 640 calls.  The EGRESS of a protected agent is
      gated; unprotected egress passes unchanged.  Random placement draws one
      per-episode ordering, so levels are nested (paired design); hub-first is
      nested by construction (original-graph degree order).

Episode structure (mirrors network_run.py, corpus from jobs.py): BFS tree of 12
agents rooted at the source; every edge parent->child is one LLM call (the
parent writes that child's handoff), so an episode is exactly 11 calls.  The
source's context carries the secret (tasks.context); every other agent sees only
the note it received.  Rows carry `from`, `to`, `hop` (BFS depth; source edges =
hop 1), `topology`, `secret_id` and both D1 verdicts, so run_detectors.py ->
run_d3.py -> build_ensemble.py score them with the SAME stack as the ladder;
the endpoint is the ensemble, `auto_leaked` is diagnostic only.

TEST discipline: every split="test" episode is refused until the PREREG §5
freeze marker exists (jobs._safe_job guard).  Smoke tests use split="dev".

Run (only after the freeze):
  python runner.py --job network_test    --max-minutes 300
  python runner.py --job network_partial --max-minutes 300

No-LLM checks:  python network_experiment.py --self-test
DEV smoke (1 episode, 11 calls):  python network_experiment.py --smoke
"""
from __future__ import annotations

import json
import random
import re
import sys

import networkx as nx

import jobs as J

NET_MODEL = J.MODELS_CORE[0]            # llama3.2:3b (Tier A: 1 model)
NET_TASK = "customer_service"           # original task; networks test topology
NET_KIND = "semantic"                   # headline content-leak endpoint
NET_PRESSURE = "high"                   # matches the ladder cells the sim is fitted on
TOPOS_63 = ("ring12", "er12", "ba12")   # held-out for H5b
TOPO_64 = "ba12"                        # scale-free graphs (H5a)
FRACS = (0.25, 0.5, 0.75, 1.0)
PLACEMENTS = ("hub", "random")
N_AGENTS = 12
CALLS_PER_EPISODE = 11                  # edges of the BFS tree


# ---------------------------------------------------------------- topology
def _graph(name: str):
    """Fixed-seed graph + source.  Constructions match sim.py's topologies
    (ring = WS k=4 p=0, ER = gnm(n, 2n), BA = m=2) so the simulated held-out
    networks and the real ones are literally the same graphs at n=12."""
    m = re.fullmatch(r"(ring|ws|er|ba|chain|star)(\d+)([hlr]?)", name)
    if not m:
        raise KeyError(f"unknown topology {name!r}")
    kind, n, src = m.group(1), int(m.group(2)), m.group(3) or "r"
    if kind == "ring":
        G = nx.watts_strogatz_graph(n, 4, 0.0, seed=1)
    elif kind == "ws":
        G = nx.connected_watts_strogatz_graph(n, 4, 0.1, seed=1)
    elif kind == "er":
        for sd in range(1, 200):
            G = nx.gnm_random_graph(n, 2 * n, seed=sd)
            if nx.is_connected(G):
                break
    elif kind == "ba":
        G = nx.barabasi_albert_graph(n, 2, seed=1)
    elif kind == "chain":
        G = nx.path_graph(n)
    else:  # star
        G = nx.star_graph(n - 1)
    if not nx.is_connected(G):
        raise RuntimeError(f"{name}: graph is not connected")
    deg = dict(G.degree())
    root = (max(deg, key=lambda v: (deg[v], -v)) if src == "h"
            else min(deg, key=lambda v: (deg[v], v)) if src == "l"
            else random.Random(7).choice(sorted(G)))
    return G, root


def topology(name: str):
    """(tree, depth, hub_order) with agents renumbered in BFS order from the source.

    tree      {parent: [children]}  — CALLS_PER_EPISODE edges
    depth     {agent: bfs depth}    — the source's children are hop 1
    hub_order every agent sorted by ORIGINAL-graph degree, descending
              (the hub-first placement rule, matching sim_final.py)
    """
    G, root = _graph(name)
    order, parent, depth = [root], {root: None}, {root: 0}
    for u in order:
        for v in sorted(G[u]):
            if v not in parent:
                parent[v] = u
                depth[v] = depth[u] + 1
                order.append(v)
    if len(order) != G.number_of_nodes():
        raise RuntimeError(f"{name}: BFS reached {len(order)}/{G.number_of_nodes()} nodes")
    idx = {v: i for i, v in enumerate(order)}
    tree: dict = {}
    for v, p in parent.items():
        if p is not None:
            tree.setdefault(idx[p], []).append(idx[v])
    tree = {k: sorted(v) for k, v in sorted(tree.items())}
    # depth must be keyed by the RENUMBERED ids, like the tree
    depth = {idx[v]: d for v, d in depth.items()}
    deg = dict(G.degree())
    hub_order = sorted(range(len(order)), key=lambda i: (-deg[order[i]], i))
    return tree, depth, hub_order


def _protected(cell: dict, hub_order, ep: int) -> set:
    """Agents whose EGRESS is gated in this episode."""
    n = len(hub_order)
    defense = cell["defense"]
    if defense == "none":
        return set()
    if defense == "gateway":
        return set(range(n))
    frac = float(cell["frac"])
    m = int(round(frac * n))
    if cell["placement"] == "hub":
        return set(hub_order[:m])
    # one random ordering per episode (independent of frac) -> levels are
    # nested, i.e. the 25% set is inside the 50% set: a paired design
    rng = random.Random(J._stable("protect", cell["topology"], ep))
    perm = rng.sample(range(n), n)
    return set(perm[:m])


# ---------------------------------------------------------------- episode
def episode(cell: dict, ep: int) -> list[dict]:
    model = cell["model"]
    task = cell["task"]
    defense = cell["defense"]
    kind = cell["kind"]
    pressure = cell["pressure"]
    split = cell.get("split", "test")
    topo_name = cell["topology"]

    rec = J._secret_for(split, kind, ep)
    ck = J._corpus_kind(rec)
    tree, depth, hub_order = topology(topo_name)
    protected = _protected(cell, hub_order, ep)

    # pairing: same secret + same facts for every cell at this episode index
    seed0 = (J._stable("net", split, task, kind, topo_name, ep) + J.MASTER) % (2 ** 31)
    facts_seed = (J._stable("facts", task, ep)) % (2 ** 31)
    sys0, user, _facts = J.tasks.context(task, rec["text"], facts_seed,
                                         include_secret=True, pressure=pressure)
    dprompt = "" if defense == "partial" else J._defense_prompt(defense)
    sys0 = sys0 + dprompt
    gate = J._make_gate("gateway" if defense in ("gateway", "partial") else defense,
                        rec, kind, model)
    roles = J.tasks.TASKS[task]["roles"]
    client = J._client()

    rows = []
    incoming: dict = {}
    for a in sorted(tree):
        for c in tree[a]:
            if a == 0:                     # source writes from its own context
                sys, usr, seed = sys0, user, seed0 + c
            else:                          # everyone else only saw ONE note
                sys_n, usr_t = J.tasks.downstream(task, roles[a % len(roles)],
                                                  dprompt, pressure)
                sys = sys_n
                usr = usr_t.format(note=incoming[a])
                seed = seed0 + 10 * a + c
            r = client.complete(model, sys, usr, seed=seed)
            raw = r["text"]
            sent = gate(raw) if a in protected else raw
            lk, idn = J._d1_verdicts(sent, rec)
            incoming[c] = sent
            rows.append({
                "model": model, "defense": defense, "pressure": pressure,
                "kind": ck, "topology": topo_name, "hop": depth[c],
                "episode": ep, "task": task, "split": split,
                "secret_id": rec["id"], "secret": rec["text"],
                "ident": rec.get("ident"),
                "from": a, "to": c, "source": 0,
                "protect_frac": len(protected) / len(hub_order),
                "placement": cell.get("placement", ""),
                "raw": raw, "sent": sent,
                "auto_leaked": lk, "auto_ident": idn,
                "seed": seed, "cached": int(bool(r.get("cached", False))),
                "seed_supported": r.get("seed_supported"),
            })
    if ep % 10 == 0:
        try:
            J._embedder().save()
        except Exception:
            pass
    return rows


# ---------------------------------------------------------------- cells
def network_test_cells():
    """H5b: 3 held-out topologies x 2 defenses x 30 episodes = 180 episodes
    (x 11 calls = 1 980)."""
    eps = J._cfg()["experiment"]["episodes_primary"]
    return [dict(split="test", model=NET_MODEL, task=NET_TASK, defense=d,
                 kind=NET_KIND, pressure=NET_PRESSURE, topology=t, episodes=eps)
            for t in TOPOS_63 for d in ("none", "gateway")]


def network_partial_cells():
    """H5a: 4 fractions x 2 placements x 30 episodes = 240 episodes
    (x 11 calls = 2 640), all on ba12."""
    eps = J._cfg()["experiment"]["episodes_primary"]
    return [dict(split="test", model=NET_MODEL, task=NET_TASK, defense="partial",
                 kind=NET_KIND, pressure=NET_PRESSURE, topology=TOPO_64,
                 frac=f, placement=p, episodes=eps)
            for f in FRACS for p in PLACEMENTS]


# ---------------------------------------------------------------- checks
def _self_test():
    """CPU-only: topology determinism, edge counts, placement logic, pairing."""
    ok = True
    for t in TOPOS_63 + (TOPO_64, "chain12", "star12"):
        tree, depth, hub = topology(t)
        t2, d2, h2 = topology(t)
        edges = sum(len(v) for v in tree.values())
        nodes = set().union(*[set(v) for v in tree.values()] + [{0}])
        checks = {
            "edges==11": edges == CALLS_PER_EPISODE,
            "nodes==12": len(nodes) == N_AGENTS,
            "deterministic": (tree, depth, hub) == (t2, d2, h2),
            "source hop1": all(depth[c] == 1 for c in tree[0]),
        }
        ok &= all(checks.values())
        print(f"{t:8s} edges={edges} maxdepth={max(depth.values())} "
              f"hub_order={hub} {'OK' if all(checks.values()) else checks}")
        if t in (TOPO_64,):
            for f in FRACS:
                counts = {p: len(_protected(dict(defense="partial", topology=t,
                                                 frac=f, placement=p), hub, 0))
                          for p in PLACEMENTS}
                want = int(round(f * N_AGENTS))
                good = all(v == want for v in counts.values())
                ok &= good
                print(f"    frac={f} protected={counts} want={want} "
                      f"{'OK' if good else 'FAIL'}")
            for p in PLACEMENTS:
                sets = [_protected(dict(defense="partial", topology=t, frac=f,
                                        placement=p), hub, 0) for f in FRACS]
                nested = all(sets[i] <= sets[i + 1] for i in range(len(sets) - 1))
                ok &= nested
                print(f"    placement={p} nested={'OK' if nested else 'FAIL'}")
    # same secret for the same episode across cells (pairing)
    a = J._secret_for("dev", "semantic", 3)["id"]
    b = J._secret_for("dev", "semantic", 3)["id"]
    pair_ok = a == b
    ok &= pair_ok
    print(f"pairing stable: {a} {'OK' if pair_ok else 'FAIL'}")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _smoke():
    """1 real episode on a DEV secret (11 calls); writes results/network_smoke.jsonl
    so no TEST secret is ever touched and no job checkpoint is consumed."""
    cell = dict(split="dev", model=NET_MODEL, task=NET_TASK, defense="gateway",
                kind=NET_KIND, pressure=NET_PRESSURE, topology="er12", episodes=1)
    rows = episode(cell, 0)
    out = "results/network_smoke.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"job": "smoke", "cell": cell, "episode": 0,
                                 **r}, ensure_ascii=False) + "\n")
    leaks = sum(r["auto_leaked"] for r in rows)
    print(f"smoke: {len(rows)} rows (want {CALLS_PER_EPISODE}), "
          f"D1 leaks={leaks}, secret={rows[0]['secret_id']}, wrote {out}")
    return 0 if len(rows) == CALLS_PER_EPISODE else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    if "--smoke" in sys.argv:
        sys.exit(_smoke())
    for spec_fn, calls in ((network_test_cells, 11), (network_partial_cells, 11)):
        cells = spec_fn()
        n = sum(c["episodes"] for c in cells)
        print(f"{spec_fn.__name__:24s} {len(cells):2d} cells x "
              f"{cells[0]['episodes']} eps = {n:3d} episodes "
              f"({n * calls} calls)")
        for c in cells:
            print("   ", json.dumps({k: v for k, v in c.items()}))
