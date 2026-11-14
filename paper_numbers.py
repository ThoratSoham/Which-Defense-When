#!/usr/bin/env python
"""Phase 7 numbers pipeline — turns scored transcripts into the paper's tables.

Sections (run one or all; every section SKIPS with instructions when its input
does not exist yet):

  ladder      H1 + H8: T per defense per detector (ensemble primary), Wilson and
              cluster-bootstrap-over-secrets 95% CIs, the 6 pairwise contrasts
              via a SECRET-LEVEL sign-flip permutation test (the cluster is the
              unit of analysis, PREREG section 4), Holm-corrected, Cohen's h,
              ladder-ordering check B0 > B2 > L1 > L1+L2 per detector, plus the
              T-per-model breakdown.
  baselines   W6: T and usefulness per baseline defense (B1/B3/B4/B5/B6/B7).
  usefulness  H6: TOST equivalence (margin +/- 0.05) of usefulness for
              gateway vs B0 — pooled, semantic-only (content gateway, no
              identifier redaction) and verbatim-only (identifier redaction in
              play) — and B4 vs B0, which the paper expects NOT to be
              equivalent.  Equivalence is decided by the paired, secret-cluster
              bootstrap 90% CI lying entirely inside the margin (the standard
              TOST <-> 90% CI correspondence).
  slip       Phase 3 slip-pool debrief: n, slips, exact Clopper-Pearson 95%
              CI, failed/empty-note flow counts, per variant and per secret,
              for every boundary pool on disk (llama + qwen replication).
  persistence  H3: (a) deterministic gateway re-pass — fraction of notes
              whose leak SURVIVED the gate (slip_survived) still leaking,
              gate-passed incl. never-leaked, and caught notes regressing,
              from results/hop2_repass*.jsonl; (b) next-agent rewrite — rho
              (persistence) and control fresh-origination with Wilson CIs,
              from results/hop2_rewrite*.jsonl.  Both reported per pool tag.
  h4         gateway-variant miss correlation: loads
              results/variant_correlation.json (miss rates per variant,
              pairwise phi / odds ratio / McNemar, rotation survival).
  icc        heterogeneity: loads results/heterogeneity.json (beta-binomial
              secret-level ICC per pool, leave-one-secret-out error,
              between-model dispersion).
  network     Phase 6 artifacts: H2/H5b calibration
              (network_calibration.json), H5a partial-protection cells
              (partial_protect.json), H2 out-edge correlation
              (outedge.json).  TEST-gated: skips until those jobs run
              after the freeze.

Scoring prerequisite: results/detector_final.jsonl must contain rows for the
section's `src` (produced by run_detectors.py -> run_d3.py -> build_ensemble.py,
ALL transcript files in ONE run_detectors invocation because it rewrites its
pool).  paper_numbers.py prints the exact command and never runs it itself.

Validation mode (old study data, no split/usefulness fields):
  python paper_numbers.py --section ladder --ladder-src results_v2 \
      --ladder-transcripts results_v2_transcripts.jsonl
  must reproduce the chain_hop1 table of results/t_by_detector.json.

Writes results/numbers.json (merges with whatever sections already ran).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from collections import defaultdict

from network_calibrate import cluster_ci, wilson

MASTER = 20261025
BOOT = 5000
FLIPS = 5000
PRIMARY = ["none", "warning", "gateway_l1", "gateway"]
DETECTORS = ["ensemble", "d1", "d2", "d3"]
MARGIN = 0.05
SCORE_CMD = ("python run_detectors.py results_v2_transcripts.jsonl "
             "network_results_transcripts.jsonl "
             "results/ladder_test_transcripts.jsonl "
             "results/api_ladder_transcripts.jsonl "
             "results/baselines_transcripts.jsonl "
             "results/baselines2_transcripts.jsonl "
             "results/network_test_transcripts.jsonl "
             "results/network_partial_transcripts.jsonl"
             "  &&  python run_d3.py --provider google"
             "  &&  python run_d3.py --provider local"
             "  &&  python build_ensemble.py")


# ---------------------------------------------------------------- loading
def load_final(path="results/detector_final.jsonl"):
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            r = json.loads(line)
            out[(r.get("src"), r.get("row"))] = r
    return out


def verdict(frow, det):
    if frow is None:
        return None
    v = frow.get("ensemble") if det == "ensemble" else \
        (frow.get("verdicts") or {}).get(det)
    return v if v in (0, 1) else None


def load_rows(transcripts, src, final):
    """Transcript rows + per-detector verdicts (_V) joined by (src, row)."""
    rows = []
    if not os.path.exists(transcripts):
        return rows, 0
    n_final = sum(1 for (s, _) in final if s == src)
    for i, line in enumerate(open(transcripts, encoding="utf-8")):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        r["row"] = i
        f = final.get((src, i))
        r["_V"] = {d: verdict(f, d) for d in DETECTORS}
        rows.append(r)
    return rows, n_final


def _secret(r):
    return r.get("secret_id") or r.get("secret") or "?"


def _task(r):
    return r.get("task") or "na"


# ---------------------------------------------------------------- stats
def cohen_h(p1, p2):
    return 2 * math.asin(math.sqrt(max(min(p1, 1), 0))) - \
           2 * math.asin(math.sqrt(max(min(p2, 1), 0)))


def sign_flip_p(diff_by_secret, iters=FLIPS, seed=MASTER):
    """Two-sided secret-level sign-flip permutation test on per-secret mean
    differences (the secret is the cluster, PREREG section 4)."""
    vals = list(diff_by_secret.values())
    n = len(vals)
    if n == 0:
        return float("nan"), 0
    obs = sum(vals) / n
    if obs == 0 or n == 0:
        return 1.0, n
    rng = random.Random(seed)
    cnt = 0
    for _ in range(iters):
        stat = sum(v if rng.random() < 0.5 else -v for v in vals) / n
        if abs(stat) >= abs(obs) - 1e-15:
            cnt += 1
    return (cnt + 1) / (iters + 1), n


def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0] * m
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj


def t_table(rows, det):
    """Per defense over hop-1 notes: n definite, k leaks, T, Wilson, cluster CI."""
    by_def = defaultdict(lambda: defaultdict(list))   # defense -> secret -> [v]
    undef = defaultdict(int)
    for r in rows:
        d = r.get("defense")
        v = r["_V"][det]
        if v is None:
            undef[d] += 1
            continue
        by_def[d][_secret(r)].append(v)
    out = {}
    for d, sec in by_def.items():
        vals = [x for lst in sec.values() for x in lst]
        k, n = sum(vals), len(vals)
        lo, hi = cluster_ci(sec, boot=BOOT, seed=MASTER)
        wlo, whi = wilson(k, n)
        out[d] = {"n": n, "k": k, "T": k / n if n else float("nan"),
                  "cluster_ci": [lo, hi], "wilson_ci": [wlo, whi],
                  "n_undetermined": undef.get(d, 0)}
    return out


def pairwise(rows, det):
    """6 pairwise contrasts on secret-level mean differences."""
    sec = defaultdict(lambda: defaultdict(list))     # defense -> secret -> [v]
    for r in rows:
        v = r["_V"][det]
        if v is None:
            continue
        sec[r.get("defense")][_secret(r)].append(v)
    present = [d for d in PRIMARY if d in sec]
    res = []
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            a, b = present[i], present[j]
            shared = set(sec[a]) & set(sec[b])
            diffs = {s: (sum(sec[a][s]) / len(sec[a][s])
                         - sum(sec[b][s]) / len(sec[b][s])) for s in shared}
            pa = [x for s in shared for x in sec[a][s]]
            pb = [x for s in shared for x in sec[b][s]]
            p, n_sec = sign_flip_p(diffs)
            res.append({"a": a, "b": b,
                        "diff": (sum(pa) / len(pa)) - (sum(pb) / len(pb)),
                        "cohen_h": cohen_h(sum(pa) / len(pa), sum(pb) / len(pb)),
                        "p": p, "n_secrets": n_sec})
    adj = holm([r["p"] for r in res]) if res else []
    for r, q in zip(res, adj):
        r["p_holm"] = q
    return res


def ordering(tables):
    """Ladder ordering check per detector (H1/H8)."""
    out = {}
    for det, tab in tables.items():
        present = [d for d in PRIMARY if d in tab]
        ts = [tab[d]["T"] for d in present]
        strict = all(a > b for a, b in zip(ts, ts[1:])) if len(ts) > 1 else None
        weak = all(a >= b for a, b in zip(ts, ts[1:])) if len(ts) > 1 else None
        out[det] = {"order": present, "T": dict(zip(present, ts)),
                    "strict": strict, "weak": weak}
    return out


# ---------------------------------------------------------------- sections
def section_ladder(args):
    final = load_final()
    rows, n_final = load_rows(args.ladder_transcripts, args.ladder_src, final)
    if not rows:
        print(f"\n[ladder] SKIP — {args.ladder_transcripts} does not exist yet")
        return None
    if n_final == 0:
        print(f"\n[ladder] SKIP — no scored rows for src={args.ladder_src!r}. "
              f"Score first:\n  {SCORE_CMD}")
        return None
    hop1 = [r for r in rows if r.get("hop") == 1]
    if any("split" in r for r in hop1):
        test = [r for r in hop1 if r.get("split") == "test"]
        if test:
            hop1 = test

    tables, ords = {}, {}
    for det in DETECTORS:
        tab = t_table(hop1, det)
        if tab:
            tables[det] = tab
    ords = ordering(tables)

    print(f"\n=== H1/H8 ladder  (src={args.ladder_src}, hop 1, n={len(hop1)} notes) ===")
    for det in DETECTORS:
        if det not in tables:
            continue
        tab = tables[det]
        print(f"\n detector={det}")
        for d in PRIMARY:
            if d not in tab:
                continue
            c = tab[d]
            print(f"   {d:12s} n={c['n']:5d}  T={c['T']:.3f}  cluster95 "
                  f"[{c['cluster_ci'][0]:.3f},{c['cluster_ci'][1]:.3f}]  "
                  f"wilson95 [{c['wilson_ci'][0]:.3f},{c['wilson_ci'][1]:.3f}]"
                  + (f"  (+{c['n_undetermined']} undetermined)" if c["n_undetermined"] else ""))
        o = ords[det]
        print(f"   ordering strict={o['strict']} weak={o['weak']}")

    contrast = None
    pw = pairwise(hop1, "ensemble")
    if pw:
        print(f"\n pairwise contrasts, ensemble (secret-level sign-flip, Holm {len(pw)}):")
        print(f"   {'contrast':24s}{'diff T':>9s}{'Cohen h':>9s}{'p':>9s}{'p Holm':>9s}{'secrets':>8s}")
        for r in pw:
            line = (f"   {r['a'] + ' vs ' + r['b']:24s}{r['diff']:9.3f}"
                    f"{r['cohen_h']:9.2f}{r['p']:9.4f}{r['p_holm']:9.4f}"
                    f"{r['n_secrets']:8d}")
            print(line)
            if {r["a"], r["b"]} == {"none", "gateway"}:
                contrast = r
        mono = ords.get("ensemble", {}).get("strict")
        print(f"   H1 monotone B0>B2>L1>L1+L2 (ensemble): {mono}; "
              f"primary B0 vs L1+L2 Holm p = "
              f"{contrast['p_holm'] if contrast else 'n/a'}")

    # descriptive T per model (H7 raw material)
    per_model = {}
    for model in sorted({r.get("model") for r in hop1}):
        line = {}
        for d in PRIMARY:
            vals = [v for r in hop1 if r.get("model") == model
                    and r.get("defense") == d and r["_V"]["ensemble"] is not None
                    for v in [r["_V"]["ensemble"]]]
            if vals:
                line[d] = round(sum(vals) / len(vals), 3)
        if line:
            per_model[str(model)] = line
    if per_model:
        print("\n T per model x defense (ensemble):")
        for m, line in per_model.items():
            print(f"   {m:16s} " + "  ".join(f"{d}={line[d]:.3f}"
                                             for d in PRIMARY if d in line))

    out = {"src": args.ladder_src, "n_hop1": len(hop1),
           "t_by_detector": tables, "ordering": ords,
           "pairwise_ensemble": pw,
           "primary_contrast": contrast, "t_per_model": per_model}
    return out


def section_baselines(args):
    final = load_final()
    rows, n_final = load_rows("results/baselines_transcripts.jsonl",
                              "baselines", final)
    if not rows:
        print("\n[baselines] SKIP — results/baselines_transcripts.jsonl does "
              "not exist yet (Phase 5)")
        return None
    if n_final == 0:
        print(f"\n[baselines] SKIP — no scored rows for src='baselines'. "
              f"Score first:\n  {SCORE_CMD}")
        return None
    hop1 = [r for r in rows if r.get("hop") == 1]
    print(f"\n=== W6 baselines (src=baselines, hop 1, n={len(hop1)}) ===")
    tab = t_table(hop1, "ensemble")
    order = sorted(tab, key=lambda d: -tab[d]["T"])
    print(f"   {'defense':18s}{'n':>6s}{'T':>8s}{'cluster 95% CI':>22s}")
    for d in order:
        c = tab[d]
        print(f"   {d:18s}{c['n']:6d}{c['T']:8.3f}   "
              f"[{c['cluster_ci'][0]:.3f},{c['cluster_ci'][1]:.3f}]")
    # usefulness per baseline (H6b + W6 usefulness claims)
    use = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get("hop") == 1 and r.get("usefulness") is not None:
            use[r.get("defense")][_secret(r)].append(float(r["usefulness"]))
    use_tab = {}
    print("\n   usefulness (mean of final-note checklist score):")
    for d in sorted(use):
        vals = [x for lst in use[d].values() for x in lst]
        if not vals:
            continue
        lo, hi = cluster_ci(use[d], boot=BOOT, seed=MASTER + 7)
        use_tab[d] = {"mean": sum(vals) / len(vals), "n": len(vals),
                      "cluster_ci": [lo, hi]}
        print(f"   {d:18s}n={len(vals):5d}  mean={sum(vals) / len(vals):.3f} "
              f"[{lo:.3f},{hi:.3f}]")
    return {"t": tab, "usefulness": use_tab}


def _paired_blocks(rows_a, rows_b):
    """Two key->{defense:(usefulness, secret)} indexes.  Blocks pair episodes
    that share secret + facts across defenses (jobs._secret_for / tasks.facts)."""
    def index(rows):
        idx = defaultdict(dict)
        for r in rows:
            if r.get("usefulness") is None:
                continue
            k = (str(r.get("model")), _task(r), str(r.get("kind")),
                 str(r.get("pressure")), r.get("episode"))
            idx[k][str(r.get("defense"))] = (float(r["usefulness"]),
                                              _secret(r))
        return idx
    return index(rows_a), index(rows_b)


def _pair_diffs(rows_a, rows_b):
    """Paired (usefulness_a - usefulness_b) lists per secret.  Each side is
    pre-filtered to ONE defense, so each block key has exactly one entry per
    side; blocks without a partner on the other side are dropped (counted)."""
    idx_a, idx_b = _paired_blocks(rows_a, rows_b)
    diffs, unmatched = defaultdict(list), 0
    for k in set(idx_a) & set(idx_b):
        if len(idx_a[k]) != 1 or len(idx_b[k]) != 1:
            continue
        v_a, s_a = next(iter(idx_a[k].values()))
        v_b, _s_b = next(iter(idx_b[k].values()))
        diffs[s_a].append(v_a - v_b)
    unmatched = len(set(idx_a) ^ set(idx_b))
    return diffs, unmatched


def tost(diff_by_secret, margin=MARGIN, seed=MASTER):
    """Paired, secret-cluster bootstrap 90% CI; equivalent iff inside +/- margin
    (TOST at alpha=0.05 <=> 90% CI within the equivalence margin)."""
    if not diff_by_secret:
        return None
    secrets = sorted(diff_by_secret)
    rng = random.Random(seed)
    means = []
    for _ in range(BOOT):
        tot, cnt = 0.0, 0
        for _ in range(len(secrets)):
            s = secrets[rng.randrange(len(secrets))]
            vals = diff_by_secret[s]
            tot += sum(vals)
            cnt += len(vals)
        means.append(tot / cnt)
    means.sort()
    lo90 = means[int(0.05 * (BOOT - 1))]
    hi90 = means[int(0.95 * (BOOT - 1))]
    n_pairs = sum(len(v) for v in diff_by_secret.values())
    grand = sum(x for v in diff_by_secret.values() for x in v)
    return {"mean_diff": grand / n_pairs,
            "ci90": [lo90, hi90], "n_pairs": n_pairs,
            "n_secrets": len(secrets),
            "equivalent": bool(lo90 > -margin and hi90 < margin),
            "margin": margin}


def section_usefulness(args):
    final = load_final()
    lad, n_lad = load_rows(args.ladder_transcripts, args.ladder_src, final)
    if not lad or n_lad == 0:
        print("\n[usefulness] SKIP — ladder not available/scored yet")
        return None
    if not any(r.get("usefulness") is not None for r in lad):
        print("\n[usefulness] SKIP — transcripts carry no usefulness field "
              "(old-study data; H6 needs the new ladder)")
        return None
    out = {"H6a": {}}
    hop1 = [r for r in lad if r.get("hop") == 1]
    none_rows = [r for r in hop1 if r.get("defense") == "none"]
    print("\n=== H6 usefulness TOST (margin +/-0.05, paired, cluster 90% CI) ===")
    for label, defn, kind in (
            ("gateway vs B0 (all kinds)", "gateway", None),
            ("gateway vs B0 (semantic only = no ident redaction)",
             "gateway", "semantic"),
            ("gateway vs B0 (verbatim only = ident redaction in play)",
             "gateway", "verbatim")):
        gw = [r for r in hop1 if r.get("defense") == defn
              and (kind is None or r.get("kind") == kind)]
        no = [r for r in none_rows
              if kind is None or r.get("kind") == kind]
        diffs, unmatched = _pair_diffs(gw, no)
        res = tost(diffs, seed=MASTER + len(label))
        out["H6a"][label] = res
        if res:
            print(f"   {label:56s} diff={res['mean_diff']:+.3f} "
                  f"90%CI [{res['ci90'][0]:+.3f},{res['ci90'][1]:+.3f}] "
                  f"n={res['n_pairs']}  equivalent={res['equivalent']}"
                  + (f"  ({unmatched} unpaired blocks)" if unmatched else ""))
        else:
            print(f"   {label:56s} no paired episodes yet")

    # H6b: B4 vs B0 across FILES (baselines cell conditions only)
    bas, n_bas = load_rows("results/baselines_transcripts.jsonl",
                           "baselines", final)
    if not bas or n_bas == 0:
        print("   B4 vs B0: SKIP — baselines not available/scored yet")
        out["H6b"] = None
    else:
        cond = {"model": "llama3.2:3b", "task": "customer_service"}
        b4 = [r for r in bas if r.get("hop") == 1
              and r.get("defense") == "b4_acl"
              and all(r.get(k2) == v for k2, v in cond.items())]
        no = [r for r in none_rows
              if all(r.get(k2) == v for k2, v in cond.items())]
        diffs, unmatched = _pair_diffs(b4, no)
        res = tost(diffs, seed=MASTER + 99)
        out["H6b"] = res
        if res:
            print(f"   {'B4 ACL vs B0 (expected NOT equivalent)':56s} "
                  f"diff={res['mean_diff']:+.3f} "
                  f"90%CI [{res['ci90'][0]:+.3f},{res['ci90'][1]:+.3f}] "
                  f"n={res['n_pairs']}  equivalent={res['equivalent']}"
                  + (f"  ({unmatched} unpaired blocks)" if unmatched else ""))
        else:
            print("   B4 ACL vs B0: no paired episodes yet")
    return out


# ------------------------------------------------------------ phase 3
POOL_FILES = ["results/slip_gen_v3_boundary_dev.jsonl",
              "results/slip_gen_v3_boundary_qwen2.5_3b_dev.jsonl"]


def _load_pool(path):
    """Dedup by (secret, variant, trial): a regenerated valid row wins over an
    older failed one; among equals the later row wins (same rule as
    slip_dedup.py, so these numbers match the pipeline's report)."""
    if not os.path.exists(path):
        return []
    best = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        k = (r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))
        valid = not r.get("err") and bool((r.get("note") or "").strip())
        if k not in best:
            best[k] = r
        else:
            prev = best[k]
            prev_valid = not prev.get("err") and bool((prev.get("note") or "").strip())
            if valid or not prev_valid:
                best[k] = r
    return list(best.values())


def section_slip(args):
    try:
        from heterogeneity import clopper          # exact CP interval (scipy)
    except Exception:
        clopper = None
    pools = [(p, _load_pool(p)) for p in POOL_FILES]
    pools = [(p, rows) for p, rows in pools if rows]
    if not pools:
        print("\n[slip] SKIP — no boundary pool jsonl exists yet "
              "(Phase 3 slip generation still running)")
        return None
    out = {}
    for path, rows in pools:
        n = len(rows)
        k = sum(1 for r in rows if r.get("slip"))
        n_err = sum(1 for r in rows if r.get("err"))
        n_empty = sum(1 for r in rows
                      if not r.get("err") and not (r.get("note") or "").strip())
        if clopper is not None and n:
            lo, hi = clopper(k, n)
        else:
            wlo, whi = wilson(k, n)
            lo, hi = wlo, whi
        by_var, by_sec = {}, {}
        for r in rows:
            v = str(r.get("prompt_variant"))
            s = str(r.get("secret_id"))
            vn, vk = by_var.get(v, (0, 0))
            by_var[v] = (vn + 1, vk + int(bool(r.get("slip"))))
            sn, sk = by_sec.get(s, (0, 0))
            by_sec[s] = (sn + 1, sk + int(bool(r.get("slip"))))
        model = rows[0].get("model") or "?"
        print(f"\n=== Phase 3 slip pool  {path}  (model={model}) ===")
        print(f"   n={n}  slips={k}  rate={k / n:.4f}  "
              f"Clopper-Pearson 95% [{lo:.4f}, {hi:.4f}]" if n else
              f"   {path}: empty pool")
        print(f"   flow: {n_err} failed generations (counted non-leak), "
              f"{n_empty} empty notes, {n - n_err - n_empty} valid")
        print("   by variant: " + "  ".join(
            f"{v}={vv[1]}/{vv[0]}" for v, vv in sorted(by_var.items())))
        rates = sorted((s, c[1] / c[0]) for s, c in by_sec.items())
        print("   by secret (slips/n): " + "  ".join(
            f"{s}={by_sec[s][1]}/{by_sec[s][0]}" for s, _ in rates))
        out[path] = {"model": model, "n": n, "slips": k,
                     "rate": k / n if n else float("nan"),
                     "ci95": [lo, hi], "n_err": n_err, "n_empty": n_empty,
                     "by_variant": {v: {"n": c[0], "slips": c[1]}
                                    for v, c in by_var.items()},
                     "by_secret": {s: {"n": c[0], "slips": c[1]}
                                   for s, c in by_sec.items()}}
    return out


def _jsonl_rows(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _tag_of(path, stem):
    """results/hop2_repass_qwen2_5_3b.jsonl -> qwen2_5_3b; plain -> llama."""
    base = os.path.basename(path)[len(stem) + 1:-6]
    return base or "llama3.2:3b"


def section_persistence(args):
    import glob as _glob
    out = {"repass": {}, "rewrite": {}}
    any_file = False

    print("\n=== H3(a) deterministic gateway re-pass (D1 on post-gateway text) ===")
    for path in sorted(_glob.glob("results/hop2_repass*.jsonl")):
        rows = _jsonl_rows(path)
        if not rows:
            continue
        any_file = True
        tag = _tag_of(path, "hop2_repass")
        has_surv = any("src_survived" in r for r in rows)
        skey = "src_survived" if has_surv else "src_slip"
        s = [r for r in rows if r.get(skey)]
        gp = [r for r in rows if r.get("src_slip")]
        c = [r for r in rows if not r.get("src_slip")]
        ks = sum(r.get("auto_leaked", 0) for r in s)
        kc = sum(r.get("auto_leaked", 0) for r in c)
        slo, shi = wilson(ks, len(s)) if s else (float("nan"),) * 2
        clo, chi = wilson(kc, len(c)) if c else (float("nan"),) * 2
        kg = sum(r.get("auto_leaked", 0) for r in gp)
        glo, ghi = wilson(kg, len(gp)) if gp else (float("nan"),) * 2
        print(f"   {tag:16s} "
              f"{'survived' if has_surv else 'slipped'} still leaking "
              f"{ks}/{len(s)} = "
              + (f"{ks / len(s):.3f} [{slo:.3f},{shi:.3f}]" if s else "n/a"))
        if has_surv and gp:
            print(f"   {tag:16s} gate-passed incl. never-leaked, leaking "
                  f"{kg}/{len(gp)} = {kg / len(gp):.3f} "
                  f"[{glo:.3f},{ghi:.3f}]")
        if c:
            print(f"   {tag:16s} caught leaking (regression) {kc}/{len(c)} "
                  f"= {kc / len(c):.3f} [{clo:.3f},{chi:.3f}]")
        out["repass"][tag] = {
            "conditioning": "slip_survived" if has_surv else "src_slip",
            "slip_leak": ks, "slip_n": len(s),
            "slip_rate": ks / len(s) if s else None,
            "slip_ci": [slo, shi] if s else None,
            "gatepass_leak": kg if has_surv else None,
            "gatepass_n": len(gp) if has_surv else None,
            "catch_leak": kc, "catch_n": len(c),
            "catch_rate": kc / len(c) if c else None,
            "catch_ci": [clo, chi] if c else None,
            "partial_file": path}

    print("\n=== H3(b) next-agent rewrite then gateway ===")
    for path in sorted(_glob.glob("results/hop2_rewrite*.jsonl")):
        rows = _jsonl_rows(path)
        if not rows:
            continue
        any_file = True
        tag = _tag_of(path, "hop2_rewrite")
        for cond, label in (("slip", "rho (persistence | survived)"),
                            ("catch", "fresh origination (control)")):
            sub = [r for r in rows if r.get("condition") == cond]
            if not sub:
                continue
            k = sum(r.get("auto_leaked", 0) for r in sub)
            lo, hi = wilson(k, len(sub))
            print(f"   {tag:16s} {label:26s} {k}/{len(sub)} = "
                  f"{k / len(sub):.3f}  95% CI [{lo:.3f},{hi:.3f}]")
            out["rewrite"].setdefault(tag, {})[cond] = {
                "leak": k, "n": len(sub), "rate": k / len(sub),
                "ci": [lo, hi]}

    if not any_file:
        print("   SKIP — no hop2_repass/hop2_rewrite jsonl yet "
              "(Phase 3 pipeline stage not reached)")
        return None
    return out


def section_h4(args):
    path = "results/variant_correlation.json"
    if not os.path.exists(path):
        print("\n[h4] SKIP — results/variant_correlation.json does not exist "
              "yet (variant-correlation stage not reached)")
        return None
    data = json.load(open(path, encoding="utf-8"))
    print(f"\n=== H4 gateway-variant miss correlation (n={data.get('n_notes')} notes) ===")
    for v, r in (data.get("rates") or {}).items():
        print(f"   {v:16s} miss {r['miss']}/{r['n']} = {r['miss_rate']:.3f} "
              f"95% CI [{r['ci'][0]:.3f},{r['ci'][1]:.3f}]")
    pairs = data.get("pairs") or {}
    if pairs:
        phis = [p["phi"] for p in pairs.values() if p.get("phi") is not None]
        ors = [p["or"] for p in pairs.values()
               if p.get("or") is not None and math.isfinite(p["or"])]
        ps = [p["mcnemar_p"] for p in pairs.values()
              if p.get("mcnemar_p") is not None]
        if phis:
            print(f"   pairwise phi: n={len(phis)}  "
                  f"mean={sum(phis) / len(phis):.3f}  "
                  f"min={min(phis):.3f}  max={max(phis):.3f}")
        if ors:
            print(f"   odds ratio: min={min(ors):.3f}  max={max(ors):.3f}")
        if ps:
            print(f"   McNemar p: min={min(ps):.4f}  max={max(ps):.4f}")
        print(f"   pairs ({len(pairs)}): " + ", ".join(
            f"{k} phi={v.get('phi', float('nan')):.3f}"
            for k, v in list(pairs.items())[:8]))
    rot = data.get("rotation") or {}
    for a, r in rot.items():
        same = r.get("same_gateway_rho")
        rots = {k[7:]: v for k, v in r.items() if k.startswith("rot_to_")}
        if same is not None:
            print(f"   rotation from {a:16s} same-gw rho={same:.3f}  "
                  + "  ".join(f"rot->{b}={v:.3f}" for b, v in rots.items()
                             if v == v))
    return data


def section_icc(args):
    path = "results/heterogeneity.json"
    if not os.path.exists(path):
        print("\n[icc] SKIP — results/heterogeneity.json does not exist yet "
              "(heterogeneity stage not reached)")
        return None
    data = json.load(open(path, encoding="utf-8"))
    age_h = (os.path.getmtime(path) - os.path.getmtime(__file__)) / 3600
    print(f"\n=== H3 heterogeneity / ICC ({path}) ===")
    print(f"   {'model':16s} {'n':>5s} {'slips':>6s} {'rate':>6s} "
          f"{'95% CI':>16s} {'ICC(secret)':>12s} {'LOO err':>8s}")
    for r in data.get("pools") or []:
        ci = r.get("ci") or [float("nan")] * 2
        looe = r.get("loo_mean_abs_error")
        print(f"   {str(r.get('model'))[:16]:16s} {r.get('n_notes', 0):5d} "
              f"{r.get('n_slips', 0):6d} {r.get('rate', float('nan')):6.3f} "
              f"[{ci[0]:.3f},{ci[1]:.3f}] {r.get('icc_secret', float('nan')):12.3f} "
              + ("  n/a" if looe is None else f"{looe:8.3f}"))
        sv = r.get("survived")
        if sv:
            svloo = sv.get("loo_mean_abs_error")
            print(f"   {'':16s}   survived: {sv.get('n_notes', 0):5d} "
                  f"{sv.get('n_slips', 0):6d} "
                  f"{sv.get('rate', float('nan')):6.3f} "
                  f"[{sv['ci'][0]:.3f},{sv['ci'][1]:.3f}] "
                  f"{sv.get('icc_secret', float('nan')):12.3f} "
                  + ("  n/a" if svloo is None else f"{svloo:8.3f}"))
        elif sv is None and any("survived" in p
                                for p in (data.get("pools") or [])):
            pass  # pool predates slip_rescore; gate-pass line only
    ml = data.get("model_level") or {}
    print(f"   model-level: n_models={ml.get('n_models')}  "
          f"between-model var(logit)={ml.get('between_model_var_logit')}  "
          f"{ml.get('note', '')}")
    if age_h < 0:
        print("   NOTE: file written before paper_numbers.py — regenerate "
              "after the pipeline finishes for final numbers")
    return data


def section_network(args):
    """Phase 6: H2/H5b calibration, H5a partial protection, H2 out-edge."""
    out = {}
    any_file = False

    cal = "results/network_calibration.json"
    if os.path.exists(cal):
        any_file = True
        data = json.load(open(cal, encoding="utf-8"))
        out["calibration"] = data
        print("\n=== H2/H5b simulator calibration (network_calibration.json) ===")
        for det, r in data.items():
            if not isinstance(r, dict):
                continue
            bits = []
            for key in ("mae_one", "mae_two", "mae", "coverage",
                        "covered", "n_cells", "coverage_frac"):
                if key in r:
                    v = r[key]
                    bits.append(f"{key}={v:.3f}" if isinstance(v, float)
                                else f"{key}={v}")
            fit = r.get("fit")
            if isinstance(fit, dict) and fit:
                bits.append("fit " + " ".join(
                    f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                    for k, v in list(fit.items())[:6]))
            print(f"   {det:10s} " + ("  ".join(bits) if bits else
                                      "(keys: " + ", ".join(list(r)[:8])
                                      + ")"))
    else:
        print("\n[network] SKIP calibration — "
              "results/network_calibration.json missing (TEST-gated: run "
              "runner --job network_test / network_partial, then "
              "network_calibrate.py after the freeze)")

    pp = "results/partial_protect.json"
    if os.path.exists(pp):
        any_file = True
        data = json.load(open(pp, encoding="utf-8"))
        out["partial_protect"] = data
        print(f"\n=== H5a partial protection "
              f"(outbreak >= {data.get('outbreak_min')}) ===")
        cells = data.get("cells") or {}
        print(f"   {'cell':16s}{'mean inf':>9s}{'95% CI':>15s}"
              f"{'P(outbreak)':>13s}{'n':>6s}{'pred':>8s}")
        for k in sorted(cells,
                        key=lambda x: (float(x.split("/")[0]), x)):
            c = cells[k]
            ci = c.get("real_ci") or [float("nan")] * 2
            pred = c.get("pred_mean")
            print(f"   {k:16s}{c.get('mean_infected', float('nan')):9.2f}"
                  f"  [{ci[0]:.2f},{ci[1]:.2f}]"
                  f"{c.get('p_outbreak', float('nan')):13.3f}"
                  f"{c.get('n', 0):6d}"
                  + (f"{pred:8.2f}" if pred is not None else "        -"))
        for fr in sorted({k.split("/")[0] for k in cells},
                         key=float):
            h = cells.get(f"{fr}/hub-first")
            r_ = cells.get(f"{fr}/random")
            if h and r_:
                d = h["mean_infected"] - r_["mean_infected"]
                print(f"   frac {fr:>5s}: hub minus random, mean infected "
                      f"{d:+.2f}")
    else:
        print("[network] SKIP partial protection — "
              "results/partial_protect.json missing (TEST-gated Phase 6.4)")

    oe = "results/outedge.json"
    if os.path.exists(oe):
        any_file = True
        data = json.load(open(oe, encoding="utf-8"))
        out["outedge"] = data
        print("\n=== H2 secondary: out-edge correlation ===")
        for label, r in data.items():
            if not isinstance(r, dict) or "phi" not in r:
                continue
            ci = r.get("ci95") or [None, None]
            print(f"   {label:16s} phi={r.get('phi')}  "
                  f"CI [{ci[0]},{ci[1]}]  "
                  f"perm p={r.get('perm_p_two_sided')}  "
                  f"n_episodes={r.get('n_episodes')}  "
                  f"marginal={r.get('marginal')}")
    else:
        print("[network] SKIP out-edge — results/outedge.json missing "
              "(outedge_correlation.py after network transcripts are scored)")

    return out if any_file else None


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", action="append",
                    choices=["ladder", "baselines", "usefulness",
                             "slip", "persistence", "h4", "icc",
                             "network"],
                    help="default: all (missing inputs are skipped)")
    ap.add_argument("--ladder-src", default="ladder_test")
    ap.add_argument("--ladder-transcripts",
                    default="results/ladder_test_transcripts.jsonl")
    ap.add_argument("--out", default="results/numbers.json")
    a = ap.parse_args()
    sections = a.section or ["ladder", "baselines", "usefulness",
                             "slip", "persistence", "h4", "icc",
                             "network"]

    results = {}
    if os.path.exists(a.out):
        try:
            results = json.load(open(a.out, encoding="utf-8"))
        except json.JSONDecodeError:
            results = {}
    fn = {"ladder": section_ladder, "baselines": section_baselines,
          "usefulness": section_usefulness, "slip": section_slip,
          "persistence": section_persistence, "h4": section_h4,
          "icc": section_icc, "network": section_network}
    for s in sections:
        res = fn[s](a)
        if res is not None:
            results[s] = res
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(results, open(a.out, "w", encoding="utf-8"), indent=2,
              default=str)
    print(f"\nwrote {a.out} ({', '.join(sorted(results)) or 'nothing new'})")


if __name__ == "__main__":
    main()
