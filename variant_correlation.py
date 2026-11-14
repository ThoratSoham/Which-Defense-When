#!/usr/bin/env python
"""Phase 3 / H4 — correlation of gateway misses across variants with DIFFERENT
decision logic, plus the heterogeneous-gateway rotation estimate (PREREG §1 H4).

Variants evaluated on every note of the DEV boundary pool (same registered
secret for all of them):

  v1_frozen      L1 + L2 as frozen: lexical 0.60 OR cosine >= 0.78   (the study gateway)
  v2_lexical     lexical 0.60 only (no embedding branch)
  v3_cosine      cosine >= 0.78 only (no lexical branch)
  v4_loose       lexical 0.75 OR cosine >= 0.85   (stricter-to-pass variant)
  v5_auto_judge  secret-blind: PII regex + LLM judge (AutoGateway)     [LLM calls]
  v6_auto_regex  secret-blind: PII regex only, no judge                [free]

For every (note, variant): caught = gate redacts; miss = NOT caught AND the
note actually leaks under D1 (a pass with nothing to leak is not a miss).

Outputs pairwise phi correlation, odds ratios and McNemar tests between miss
indicators, plus the rotation estimate: persistence at hop 2 when the second
hop uses a DIFFERENT variant (P(miss_vj | miss_vi)) versus rerunning the same
gateway (P(miss_vi)), which is the quantity H4's "rotating heterogeneous
gateways reduces persistence" claim rests on.

Run:
  python variant_correlation.py --skip-judge          # deterministic variants only
  python variant_correlation.py --judge-limit 400     # + v5 on a 400-note sample
  python variant_correlation.py --report              # print from saved json

Writes results/variant_correlation.json and results/variant_judge.jsonl
(checkpointed; re-running only judges notes not yet done).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import jobs

POOL = Path("results/slip_gen_v3_boundary_dev.jsonl")
JUDGE_OUT = Path("results/variant_judge.jsonl")
REPORT_OUT = Path("results/variant_correlation.json")
MASTER = 20261025
VARIANTS = ("v1_frozen", "v2_lexical", "v3_cosine", "v4_loose",
            "v5_auto_judge", "v6_auto_regex")


def load_pool():
    rows = {}
    if not POOL.exists():
        sys.exit(f"missing {POOL}")
    for line in POOL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows[(r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))] = r
    return [rows[k] for k in sorted(rows)]


def _rec_of(row):
    return {"id": row.get("secret_id"), "text": row.get("secret_text"),
            "kind": "semantic", "ident": None}


def _sentences(text):
    import re
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _cos(a, b):
    n = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return n / (na * nb) if na and nb else 0.0


def deterministic_verdicts(row, embedder, thr_loose=0.85, lex_loose=0.75):
    """Caught-verdict per variant.
    v1/v2/v3 come from the pool's RECORDED frozen-rule flags (l2_hit,
    lexical_hit) so they are exactly the study gateway's own decisions:
        v1_frozen  = lexical OR cosine   (= not slip)
        v2_lexical = lexical only
        v3_cosine  = cosine only
    v4_loose and v6 are recomputed here."""
    rec = _rec_of(row)
    note = row.get("note") or ""
    import gateway
    from slip_gen_boundary import _lexical_hit

    lex_frozen = bool(row.get("lexical_hit"))
    cos_frozen = bool(row.get("l2_hit"))
    lex_loose_hit = _lexical_hit(rec["text"], note, lexical=lex_loose)

    secret_vec = embedder(rec["text"])
    cos_loose = any(_cos(secret_vec, embedder(s)) >= thr_loose
                    for s in _sentences(note))
    auto_regex = gateway.AutoGateway(judge=None).filter(note)[0] != note
    return {
        "v1_frozen": bool(lex_frozen or cos_frozen),
        "v2_lexical": bool(lex_frozen),
        "v3_cosine": bool(cos_frozen),
        "v4_loose": bool(lex_loose_hit or cos_loose),
        "v6_auto_regex": bool(auto_regex),
    }


def judge_verdicts(rows, limit):
    """v5 on a deterministic sample, checkpointed to JUDGE_OUT."""
    done = {}
    if JUDGE_OUT.exists():
        for line in JUDGE_OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r.get("key")] = r.get("caught")
    rng = random.Random(MASTER ^ 0xA11)
    slips = [r for r in rows if r.get("slip")]
    catches = [r for r in rows if not r.get("slip")]
    rng.shuffle(slips)
    rng.shuffle(catches)
    sample = slips[: max(limit - min(limit // 2, len(catches)), 0)]
    sample += catches[: max(limit - len(sample), 0)]
    sample = sample[:limit]

    import gateway
    judge = None
    n_new = 0
    with JUDGE_OUT.open("a", encoding="utf-8") as fh:
        for row in sample:
            key = hashlib.sha1(
                f"{row.get('secret_id')}|{row.get('prompt_variant')}|"
                f"{row.get('trial_index')}".encode()).hexdigest()[:16]
            if key in done:
                continue
            if judge is None:
                judge = gateway.make_judge(jobs._judge_for("llama3.2:3b"))
            note = row.get("note") or ""
            clean = gateway.AutoGateway(judge=judge).filter(note)[0]
            caught = int(clean != note)
            fh.write(json.dumps({"key": key, "caught": caught}) + "\n")
            fh.flush()
            done[key] = caught
            n_new += 1
    return done, n_new


# ---------------------------------------------------------------- statistics
def phi(m1, m2):
    n = len(m1)
    a = b = c = d = 0
    for x, y in zip(m1, m2):
        if x and y: a += 1
        elif x and not y: b += 1
        elif y and not x: c += 1
        else: d += 1
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (a * d - b * c) / denom if denom else float("nan"), (a, b, c, d)


def mcnemar_p(b, c):
    """Two-sided exact McNemar (binomial on discordant pairs), no scipy needed."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return min(1.0, p)


def odds_ratio(a, b, c, d):
    if min(b, c) == 0:
        return float("inf") if max(a, d) > 0 else float("nan")
    return (a * d) / (b * c)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    ctr = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((ctr - half) / den, (ctr + half) / den)


def analyze(rows, judge_map):
    emb = jobs._embedder()
    recs = []
    for row in rows:
        rec = _rec_of(row)
        leak, _ = jobs._d1_verdicts(row.get("note") or "", rec)
        caught = deterministic_verdicts(row, emb)
        key = hashlib.sha1(
            f"{row.get('secret_id')}|{row.get('prompt_variant')}|"
            f"{row.get('trial_index')}".encode()).hexdigest()[:16]
        if key in judge_map:
            caught["v5_auto_judge"] = bool(judge_map[key])
        recs.append({"leak": leak, "caught": caught,
                     "slip": int(bool(row.get("slip"))),
                     "secret_id": row.get("secret_id")})

    # A variant need only cover its own subset to be scored (v5 is a
    # stratified 400-note sample: 200 slips + 200 catches, per PREREG).
    # Pairwise statistics use the common-coverage subset of both variants.
    present = [v for v in VARIANTS
               if any(v in r["caught"] for r in recs)]
    covered = {v: [r for r in recs if v in r["caught"]] for v in present}
    # miss = gate passes AND the note really leaks
    miss = {v: [(not r["caught"][v]) and r["leak"] for r in covered[v]]
            for v in present}
    out = {"n_notes": len(recs), "variants": present,
           "coverage": {v: len(covered[v]) for v in present},
           "rates": {}, "pairs": {}, "rotation": {}}
    print(f"notes: {len(recs)}; variants scored: "
          + ", ".join(f"{v} (n={len(covered[v])})" for v in present))
    for v in present:
        n = len(covered[v])
        k = sum(miss[v])
        lo, hi = wilson(k, n)
        caught_n = sum(r["caught"][v] for r in covered[v])
        out["rates"][v] = {"miss": k, "n": n, "miss_rate": k / n,
                           "ci": [lo, hi], "caught": caught_n}
        if n < len(recs):
            out["rates"][v]["stratified_sample"] = (
                "sampled 200 slips + 200 catches; miss_rate is sample-"
                "conditional, not a population estimate")
        print(f"  {v:16s} caught {caught_n:5d}/{n}  "
              f"miss(leak survives) {k:4d}  rate {k/n:.3f}  CI [{lo:.3f},{hi:.3f}]"
              + (f"   [sample n={n}, rate biased vs population]"
                 if n < len(recs) else ""))

    print("\npairwise miss correlation (notes covered by BOTH variants):")
    for i, a in enumerate(present):
        for b in present[i + 1:]:
            common = [r for r in recs
                      if a in r["caught"] and b in r["caught"]]
            ma = [(not r["caught"][a]) and r["leak"] for r in common]
            mb = [(not r["caught"][b]) and r["leak"] for r in common]
            r, (p_, q, rr, s) = phi(ma, mb)
            orr = odds_ratio(p_, q, rr, s)
            pval = mcnemar_p(q, rr)
            out["pairs"][f"{a}|{b}"] = {"phi": r, "table": [p_, q, rr, s],
                                        "or": orr, "mcnemar_p": pval,
                                        "n": len(common)}
            print(f"  {a:16s} vs {b:16s} phi={r:6.3f}  OR={orr:8.3f}  "
                  f"McNemar p={pval:.4f}  (a,b,c,d)={p_,q,rr,s}  n={len(common)}")

    # rotation: hop-2 survival when hop-2 uses a different variant
    print("\nrotation (persistence at hop 2 given hop-1 miss):")
    for a in present:
        base = out["rates"][a]["miss_rate"]
        out["rotation"][a] = {"same_gateway_rho": base,
                              "n": out["rates"][a]["n"]}
        for b in present:
            if a == b:
                continue
            common = [r for r in recs
                      if a in r["caught"] and b in r["caught"]]
            ma = [(not r["caught"][a]) and r["leak"] for r in common]
            mb = [(not r["caught"][b]) and r["leak"] for r in common]
            na = sum(ma)
            both = sum(1 for x, y in zip(ma, mb) if x and y)
            cond = both / na if na else float("nan")
            out["rotation"][a][f"rot_to_{b}"] = cond
        print(f"  {a:16s} same-gateway rho={base:.3f}  "
              + "  ".join(f"rot->{b}={out['rotation'][a][f'rot_to_{b}']:.3f}"
                          for b in present if b != a))

    REPORT_OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {REPORT_OUT}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-judge", action="store_true")
    ap.add_argument("--judge-limit", type=int, default=400)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        print(REPORT_OUT.read_text(encoding="utf-8") if REPORT_OUT.exists()
              else "no report yet")
        return
    rows = load_pool()
    print(f"pool: {len(rows)} notes, {sum(1 for r in rows if r.get('slip'))} slips")
    judge_map = {}
    if not a.skip_judge:
        judge_map, n = judge_verdicts(rows, a.judge_limit)
        print(f"v5 judge: {n} new verdicts cached ({len(judge_map)} total)")
    analyze(rows, judge_map)
    try:
        jobs._embedder().save()
    except Exception:
        pass


if __name__ == "__main__":
    main()
