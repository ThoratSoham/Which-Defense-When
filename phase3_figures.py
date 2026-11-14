#!/usr/bin/env python
"""Phase 3 figures for the manuscript (DEV boundary pool + persistence + H4).

Outputs (each written only when its input is COMPLETE, so a partial run can
never masquerade as a result):

  fig_phase3_slips.png       slip rate by variant and by secret, exact
                             two-sided 95% Clopper-Pearson intervals,
                             study-gateway verdicts (gate_impl == "study")
                             <- results/slip_gen_v3_boundary_dev.jsonl (+qwen)
  fig_phase3_persistence.png H3 panels: (a) deterministic re-pass survival,
                             (b) rewrite rho vs fresh-origination control,
                             Wilson 95% CIs, per model tag
                             <- results/hop2_repass*.jsonl / hop2_rewrite*.jsonl
                             complete iff rows >= pool keys (same rule the
                             pipeline uses) and rewrite arms >= min(target, n)
  fig_phase3_h4.png          pairwise miss-correlation phi across gateway
                             variants with McNemar p labels
                             <- results/variant_correlation.json

Run:  python phase3_figures.py            # write what is ready, skip the rest
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

POOL_LLAMA = "results/slip_gen_v3_boundary_dev.jsonl"
POOL_QWEN = "results/slip_gen_v3_boundary_qwen2.5_3b_dev.jsonl"


def _jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _pool_keys(path):
    return {(r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))
            for r in _jsonl(path)}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def clopper(k, n, alpha=0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def dedup_pool(path):
    out = {}
    for r in _jsonl(path):
        out[(r.get("secret_id"), r.get("prompt_variant"),
             r.get("trial_index"))] = r
    return list(out.values())


# ---------------------------------------------------------------- fig: slips
def fig_slips():
    # primary (llama) pool only: the slip-rate paragraph and the figure
    # caption both quote this pool; the qwen pool is the replication arm
    # reported through the ICC (heterogeneity.json), not this figure.
    pools = [p for p in (POOL_LLAMA,) if os.path.exists(p)]
    if not pools:
        print("[fig slips] SKIP - no pool jsonl yet")
        return None
    rows = [r for p in pools for r in dedup_pool(p)]
    study = [r for r in rows if r.get("gate_impl") == "study"]
    if not study:
        print("[fig slips] SKIP - pool not rescored with the study gateway "
              "(slip_rescore stage has not run)")
        return None

    by_var, by_sec = {}, {}
    for r in study:
        v = str(r.get("prompt_variant"))
        s = str(r.get("secret_id"))
        by_var.setdefault(v, [0, 0])
        by_sec.setdefault(s, [0, 0])
        by_var[v][0] += 1
        by_sec[s][0] += 1
        if r.get("slip"):
            by_var[v][1] += 1
            by_sec[s][1] += 1

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    vs = sorted(by_var)
    ax = axes[0]
    for i, v in enumerate(vs):
        n, k = by_var[v]
        lo, hi = clopper(k, n)
        rate = k / n
        ax.bar(i, rate, color="#4c72b0", capsize=3)
        ax.errorbar(i, rate, yerr=[[rate - lo], [hi - rate]], fmt="none",
                    ecolor="black", capsize=3)
        ax.text(i, hi + 0.01, f"{rate:.3f}", ha="center", fontsize=8)
    n_all = sum(n for n, _ in by_var.values())
    k_all = sum(k for _, k in by_var.values())
    ax.axhline(k_all / n_all, color="gray", ls="--", lw=1,
               label=f"pooled {k_all / n_all:.3f}")
    ax.set_xticks(range(len(vs)))
    ax.set_xticklabels(vs, rotation=20, ha="right")
    ax.set_ylabel("slip rate (gate pass)  95% CP CI")
    ax.set_title(f"by prompt variant (study gateway, n={n_all})")
    ax.legend(fontsize=8)
    ax.set_ylim(0, max(clopper(k, n)[1] for n, k in by_var.values()) + 0.08)

    ss = sorted(by_sec, key=lambda s: -by_sec[s][1] / by_sec[s][0])
    ax = axes[1]
    for i, s in enumerate(ss):
        n, k = by_sec[s]
        lo, hi = clopper(k, n)
        rate = k / n
        ax.barh(i, rate, color="#55a868")
        ax.plot([lo, hi], [i, i], color="black", lw=1)
        ax.text(hi + 0.01, i, f"{k}/{n}", va="center", fontsize=7)
    ax.set_yticks(range(len(ss)))
    ax.set_yticklabels(ss, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("slip rate  95% CP CI")
    ax.set_title("by secret (worst first)")
    ax.set_xlim(0, max(clopper(k, n)[1] for n, k in by_sec.values()) + 0.12)

    plt.tight_layout()
    plt.savefig("fig_phase3_slips.png", dpi=220)
    plt.close()
    print(f"[fig slips] wrote fig_phase3_slips.png "
          f"({len(study)} study-scored notes, {k_all} slips)")
    return "fig_phase3_slips.png"


# ---------------------------------------------------------- fig: persistence
def fig_persistence():
    repass_targets = {}
    rewrite_arms = {}
    for pool in (POOL_LLAMA, POOL_QWEN):
        keys = _pool_keys(pool)
        if keys:
            repass_targets[pool] = len(keys)
        slips = catches = 0
        for r in dedup_pool(pool):
            if r.get("slip_survived", r.get("slip")):
                slips += 1
            if not r.get("slip"):
                catches += 1
        if keys:
            # control-arm size must match what the pipeline actually ran:
            # llama 300/300, qwen 300/150 (pipeline.run_rewrite_qwen).
            ctrl = 150 if pool == POOL_QWEN else 300
            rewrite_arms[pool] = (min(300, slips), min(ctrl, catches))

    panels = []
    # (a) re-pass: complete iff every pool key has a row
    for path in sorted(glob.glob("results/hop2_repass*.jsonl")):
        rows = _jsonl(path)
        tag = os.path.basename(path)[len("hop2_repass"):-6]
        pool = POOL_QWEN if tag else POOL_LLAMA
        want = repass_targets.get(pool, -1)
        if want < 0 or len(rows) < want:
            print(f"[fig persistence] re-pass {path}: PARTIAL "
                  f"({len(rows)}/{want if want >= 0 else '?'}), skipping")
            continue
        surv = [r for r in rows if r.get("src_survived")]
        gp = [r for r in rows if r.get("src_slip")]
        cat = [r for r in rows if not r.get("src_slip")]
        mtag = "qwen" if tag else "llama"
        panels.append((f"a re-pass ({mtag}): survived", len(surv),
                       sum(r["auto_leaked"] for r in surv)))
        panels.append((f"a re-pass ({mtag}): gate-passed", len(gp),
                       sum(r["auto_leaked"] for r in gp)))
        panels.append((f"a re-pass ({mtag}): caught", len(cat),
                       sum(r["auto_leaked"] for r in cat)))
    # (b) rewrite: complete iff both arms reach their targets
    for path in sorted(glob.glob("results/hop2_rewrite*.jsonl")):
        rows = _jsonl(path)
        tag = os.path.basename(path)[len("hop2_rewrite"):-6]
        pool = POOL_QWEN if tag else POOL_LLAMA
        mtag = "qwen" if tag else "llama"
        tgt = rewrite_arms.get(pool)
        got_s = sum(1 for r in rows if r.get("condition") == "slip")
        got_c = sum(1 for r in rows if r.get("condition") == "catch")
        if tgt is None or got_s < tgt[0] or got_c < tgt[1]:
            print(f"[fig persistence] rewrite {path}: PARTIAL "
                  f"(slip {got_s}, catch {got_c}), skipping")
            continue
        for cond, label in (("slip", f"b rewrite ({mtag}): rho"),
                            ("catch", f"b rewrite ({mtag}): control")):
            sub = [r for r in rows if r.get("condition") == cond]
            panels.append((label, len(sub),
                           sum(r["auto_leaked"] for r in sub)))

    if not any(p[0].startswith("a") for p in panels) and \
            not any(p[0].startswith("b") for p in panels):
        print("[fig persistence] SKIP - no complete persistence artifact yet")
        return None

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for i, (label, n, k) in enumerate(panels):
        rate = k / n if n else float("nan")
        lo, hi = wilson(k, n)
        col = ("#4c72b0" if label.startswith("a") and "caught" not in label
               else "#c44e52" if "caught" in label or "control" in label
               else "#55a868")
        ax.bar(i, rate, color=col)
        if n:
            # clamp: for k == n the Wilson upper bound can round just below
            # 1.0 (e.g. 158/158 -> 0.999994), giving a negative yerr
            ax.errorbar(i, rate,
                        yerr=[[max(0.0, rate - lo)],
                              [max(0.0, hi - rate)]],
                        fmt="none", ecolor="black", capsize=3)
        ax.text(i, (hi if n else 0) + 0.02, f"{k}/{n}", ha="center",
                fontsize=7, rotation=90)
    ax.set_xticks(range(len(panels)))
    ax.set_xticklabels([p[0] for p in panels], rotation=25, ha="right",
                       fontsize=8)
    ax.set_ylabel("P(leak after gateway)  95% Wilson CI")
    ax.set_title("H3 persistence: deterministic re-pass and next-agent "
                 "rewrite (DEV)")
    ax.set_ylim(0, 1.12)
    plt.tight_layout()
    plt.savefig("fig_phase3_persistence.png", dpi=220)
    plt.close()
    print(f"[fig persistence] wrote fig_phase3_persistence.png "
          f"({len(panels)} bars)")
    return "fig_phase3_persistence.png"


# ------------------------------------------------------------------ fig: H4
def fig_h4():
    path = "results/variant_correlation.json"
    if not os.path.exists(path):
        print("[fig h4] SKIP - variant_correlation.json not written yet")
        return None
    data = json.load(open(path, encoding="utf-8"))
    pairs = data.get("pairs") or {}
    if not pairs:
        print("[fig h4] SKIP - no pairs in report")
        return None
    names = [k.replace("|", " vs\n") for k in pairs]
    phis = [pairs[k].get("phi") or 0.0 for k in pairs]
    ps = [pairs[k].get("mcnemar_p") for k in pairs]

    fig, ax = plt.subplots(figsize=(max(6.0, 1.4 * len(names)), 4.2))
    bars = ax.bar(range(len(names)), phis,
                  color=["#4c72b0" if (p is not None and p < 0.05)
                         else "#cccccc" for p in ps])
    for i, (b, p) in enumerate(zip(bars, ps)):
        if p is not None:
            ax.text(i, b.get_height(), f"p={p:.3f}", ha="center",
                    va="bottom", fontsize=7, rotation=90)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=7)
    ax.set_ylabel("phi (pairwise miss correlation)")
    ax.set_title(f"H4: correlation of misses across gateway variants "
                 f"(n={data.get('n_notes', '?')} notes; blue = McNemar "
                 f"p<0.05)")
    plt.tight_layout()
    plt.savefig("fig_phase3_h4.png", dpi=220)
    plt.close()
    print(f"[fig h4] wrote fig_phase3_h4.png ({len(names)} pairs)")
    return "fig_phase3_h4.png"


def main():
    written = [f for f in (fig_slips(), fig_persistence(), fig_h4()) if f]
    if not written:
        print("no phase-3 figure ready yet")
        return 1
    print(f"wrote {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())