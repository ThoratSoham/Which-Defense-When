"""Phase 6.2 — out-edge correlation: broadcast vs independent per-child notes.

The independent-cascade simulator assumes a parent's notes to its children are
independent Bernoulli draws. The real runs generate ONE SEPARATE LLM CALL PER
CHILD (different seeds, shared parent context), so that assumption is empirical.
This script measures it on the only topology with siblings:

    star6 is routed as  0 -> 1 -> {2,3,4,5}   (network_run.TOPO)
    => agent 1 writes FOUR sibling notes per episode; agent 0 has no siblings.
    (COMPUTE_PLAN said "5 notes from agent 0"; the data says 4 from agent 1.)

Two distinct effects are separated by STRATIFYING on the parent's own state:
  parent_leak = 1  ->  relay case (parent was infected)
  parent_leak = 0  ->  origination case (parent was not infected)
A correlation that disappears after conditioning on the parent is common-cause,
not evidence of broadcast behaviour.

Statistic (stratified, Simpson-safe):
    phi = sum_s pairs_s * (J_s - p_s^2) / sum_s pairs_s * p_s * (1 - p_s)
where s = (model, defense, pressure, kind, parent_leak), J_s = mean pairwise
joint-leak rate among siblings within stratum, p_s = marginal. phi = 0 under
within-stratum independence, 1 under a perfect within-episode broadcast.

Null: outcomes are shuffled between episodes WITHIN stratum (marginals and
episode sizes preserved), so any remaining structure is the sibling coupling.

  python outedge_correlation.py            # all verdicts, writes results/outedge.json
"""
import collections
import json
import math
import os

import numpy as np

SEED = 20261025
PERMUTATIONS = 2000
BOOTSTRAPS = 2000

# ----------------------------------------------------------------- statistics
def strata_key(cell, parent_leak):
    return (tuple(cell), int(parent_leak))


def phi_stratified(episodes):
    """episodes: list of {stratum, sib:[0/1,...]} -> (phi, numerator, denominator)."""
    by = collections.defaultdict(list)
    for e in episodes:
        by[e["stratum"]].append(e["sib"])
    num = den = 0.0
    for s, vecs in by.items():
        flat = [x for v in vecs for x in v]
        p = sum(flat) / len(flat)
        pairs = sum(len(v) * (len(v) - 1) // 2 for v in vecs)
        if pairs == 0 or p in (0.0, 1.0):
            continue
        joint = sum(v[i] * v[j] for v in vecs
                    for i in range(len(v)) for j in range(i + 1, len(v)))
        joint /= pairs
        num += pairs * (joint - p * p)
        den += pairs * p * (1 - p)
    if den == 0:
        return float("nan"), num, den
    return num / den, num, den


def _shuffle_within(episodes, rng):
    """Reassign sibling outcomes between episodes inside each stratum
    (keeps marginals and each episode's sibling count exactly)."""
    by = collections.defaultdict(list)
    for e in episodes:
        by[e["stratum"]].extend(e["sib"])
    out = []
    for e in episodes:
        pool_keys = e["stratum"]
        # draw from this stratum's pool, refilled when exhausted
        need = len(e["sib"])
        if len(by[pool_keys]) < need:
            raise RuntimeError("stratum pool smaller than episode")
        take = [by[pool_keys].pop(rng.integers(len(by[pool_keys]))) for _ in range(need)]
        out.append({**e, "sib": take})
    return out


def permutation_pvalue(episodes, observed, n=PERMUTATIONS, seed=SEED):
    rng = np.random.default_rng(seed)
    # pre-drain pools deterministically by processing all strata at once
    null = []
    for _ in range(n):
        shuffled = _shuffle_within(episodes, rng)
        phi, _, _ = phi_stratified(shuffled)
        null.append(phi)
    null = np.array([z for z in null if not math.isnan(z)])
    if len(null) == 0 or math.isnan(observed):
        return float("nan"), null
    return float((np.abs(null) >= abs(observed)).mean()), null


def bootstrap_ci(episodes, n=BOOTSTRAPS, seed=SEED + 1):
    """Episode-level bootstrap (resample whole episodes within stratum)."""
    rng = np.random.default_rng(seed)
    by = collections.defaultdict(list)
    for e in episodes:
        by[e["stratum"]].append(e)
    vals = []
    for _ in range(n):
        resampled = []
        for stratum, members in by.items():
            idx = rng.integers(len(members), size=len(members))
            resampled += [members[i] for i in idx]
        phi, _, _ = phi_stratified(resampled)
        if not math.isnan(phi):
            vals.append(phi)
    if not vals:
        return (float("nan"), float("nan"))
    return tuple(np.percentile(vals, [2.5, 97.5]))


# -------------------------------------------------------------------- loading
def load_pool_index(pool_path="results/detector_pool.jsonl",
                    final_path="results/detector_final.jsonl"):
    """row index -> record for network transcripts (verified exact join).
    detector_final.jsonl (built by build_ensemble.py) carries d3/ensemble;
    fall back to the raw pool when it has not been built yet."""
    path = final_path if os.path.exists(final_path) else pool_path
    idx = {}
    if not os.path.exists(path):
        return idx
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("src") == "network_results":
            idx[r["row"]] = r
    return idx


def build_episodes(transcript_path="network_results_transcripts.jsonl",
                   verdict=("auto_leaked",)):
    """One episode = one agent-1 broadcast (4 siblings) + the parent's own state."""
    rows = [json.loads(l) for l in open(transcript_path, encoding="utf-8")]
    pool = load_pool_index()

    def value(row_i, note):
        out = []
        for v in verdict:
            if v == "auto_leaked":
                out.append(int(note["auto_leaked"]))
            else:
                p = pool.get(row_i)
                if p is None:
                    out.append(None)
                elif v in ("d1", "d2", "d3"):
                    out.append(p.get("verdicts", {}).get(v))
                elif v == "ensemble":
                    out.append(p.get("ensemble"))
                elif v == "d1_identifier":
                    out.append(p.get("d1_identifier"))
        return out

    eps = collections.defaultdict(lambda: {"parent": None, "sib": [[]],
                                           "cell": None})
    for i, r in enumerate(rows):
        if r.get("topology") != "star6":
            continue
        key = (r["model"], r["defense"], r["pressure"], r["kind"], r["episode"])
        e = eps[key]
        e["cell"] = (r["model"], r["defense"], r["pressure"], r["kind"])
        if r["from"] == 0 and r["to"] == 1:            # parent's incoming note
            e["parent"] = value(i, r)
        elif r["from"] == 1:                            # sibling notes
            e["sib"][0].append(value(i, r))
    # keep episodes whose parent note and all 4 siblings exist and voted
    out = []
    for key, e in eps.items():
        if e["parent"] is None or len(e["sib"][0]) < 2:
            continue
        out.append((key, e))
    return out, pool


def episodes_for(verdict_name, parent_state=None):
    """-> list of {stratum, sib} for one verdict, optionally one parent state."""
    all_eps, _ = build_episodes(verdict=(verdict_name if verdict_name != "auto_leaked"
                                         else "auto_leaked",))
    vpos = 0
    res = []
    for key, e in all_eps:
        parent = e["parent"][vpos]
        if parent not in (0, 1):
            continue
        if parent_state is not None and parent != parent_state:
            continue
        sib = [s[vpos] for s in e["sib"][0]]
        if any(x not in (0, 1) for x in sib):
            continue
        res.append({"stratum": strata_key(e["cell"], parent), "sib": sib})
    return res


def analyse(verdict_name):
    report = {}
    for label, state in (("parent_infected", 1), ("parent_clean", 0), ("all", None)):
        eps = episodes_for(verdict_name, state)
        if not eps:
            report[label] = {"n_episodes": 0}
            continue
        phi, num, den = phi_stratified(eps)
        pval, null = permutation_pvalue(eps, phi) if den else (float("nan"), [])
        lo, hi = bootstrap_ci(eps) if den else (float("nan"), float("nan"))
        flat = [x for e in eps for x in e["sib"]]
        report[label] = {
            "n_episodes": len(eps), "n_notes": len(flat),
            "marginal": sum(flat) / len(flat),
            "phi": None if math.isnan(phi) else round(phi, 4),
            "ci95": [None if math.isnan(lo) else round(lo, 4),
                     None if math.isnan(hi) else round(hi, 4)],
            "perm_p_two_sided": None if isinstance(pval, float) and math.isnan(pval)
                                else round(pval, 4),
        }
    return report


def main():
    out = {"method": {"stratifier": "cell x parent_leak",
                      "permutations": PERMUTATIONS, "bootstraps": BOOTSTRAPS,
                      "seed": SEED,
                      "topology": "star6 (0 -> 1 -> {2,3,4,5}); 4 siblings from agent 1"}}
    for name in ("auto_leaked", "d1", "d2", "ensemble", "d1_identifier"):
        try:
            out[name] = analyse(name)
        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {e}"}

    hdr = f"{'verdict':16s}{'stratum':18s}{'n_eps':>6s}{'p':>7s}{'phi':>8s}" \
          f"{'95% CI':>18s}{'perm p':>9s}"
    print(hdr)
    print("-" * len(hdr))
    for name, rep in out.items():
        if name == "method":
            continue
        if "error" in rep:
            print(f"{name:16s}  {rep['error']}")
            continue
        for label in ("parent_infected", "parent_clean", "all"):
            r = rep.get(label, {})
            if not r.get("n_episodes"):
                print(f"{name:16s}{label:18s}  no data")
                continue
            ci = r["ci95"]
            ci_s = f"[{ci[0]:+.3f},{ci[1]:+.3f}]" if ci[0] is not None else "n/a"
            phi = r["phi"]
            print(f"{name:16s}{label:18s}{r['n_episodes']:6d}{r['marginal']:7.3f}"
                  f"{(f'{phi:+.3f}' if phi is not None else 'n/a'):>8s}"
                  f"{ci_s:>18s}"
                  f"{(r['perm_p_two_sided'] if r['perm_p_two_sided'] is not None else float('nan')):9.4f}")
    os.makedirs("results", exist_ok=True)
    json.dump(out, open("results/outedge.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote results/outedge.json")


if __name__ == "__main__":
    main()
