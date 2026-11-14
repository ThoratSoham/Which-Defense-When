#!/usr/bin/env python
"""Re-score the boundary slip pools with THE study gateway (PREREG section 0).

Why: the pools were originally labelled by a local replica of the L2 rule
inside slip_gen_boundary.py.  An audit against gateway.Gateway (threshold /
lexical from config.yaml, the frozen definition) found ~10% verdict
disagreement in both directions (spurious "case" identifier word, different
word normalization/denominator, different sentence segmentation).  This
script makes the study gateway authoritative for every pool row.

Per row it writes:
    gate_impl      "study" once rescored
    slip           gate passed (unchanged DEFINITION; now study verdict)
    gateway_filtered, l2_hit, lexical_hit   study verdicts
    replica_slip, replica_filtered, replica_l2_hit, replica_lexical_hit
                   the original replica verdicts, preserved for provenance
    d1_leak        D1 content-leak verdict on the note (jobs._d1_verdicts)
    slip_survived  slip AND d1_leak — the H3 "leak survived the gateway"
                   conditioning variable (PREREG H3: P(survive | ...))

Modes:
  python rescore_pool_gate.py --report          # full disagreement stats, no write
  python rescore_pool_gate.py --apply           # rewrite pools atomically,
                                                # quarantine stale derived artifacts
Both modes embed only what the sqlite cache misses, in batches (Ollama).
--apply is meant to run as the pipeline stage BETWEEN slip_gen and slip_dedup
(it must not run while a generator is appending: read-modify-write would race).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
import gateway as G          # noqa: E402
import jobs                  # noqa: E402

POOLS = ["results/slip_gen_v3_boundary_dev.jsonl",
         "results/slip_gen_v3_boundary_qwen2.5_3b_dev.jsonl"]
EMB_DB = "results/embed_cache.sqlite3"

# derived artifacts whose contents depend on the old replica verdicts
STALE_PATTERNS = ["results/hop2_repass*.jsonl", "results/hop2_rewrite*.jsonl",
                  "results/variant_judge.jsonl", "results/hop2_report*.md",
                  "results/variant_correlation.json",
                  "results/slip_boundary_report.md",
                  "results/heterogeneity.json"]


def _rows_of(path):
    if not os.path.exists(path):
        return []
    out, seen = [], {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        k = (r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))
        seen[k] = r                      # last write wins (matches slip_dedup)
    return list(seen.values())


def _key(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _seed_embedder(emb, texts):
    """Populate the in-memory embedder from slip-gen's sqlite cache with
    segmentation-tolerant keys; return the texts still missing."""
    conn = sqlite3.connect(EMB_DB, timeout=1) if os.path.exists(EMB_DB) else None
    missing = []
    for t in texts:
        vec = None
        if conn is not None:
            for k in (t, t.rstrip(". ").strip(), t.rstrip("."), t.rstrip("!?.")):
                row = conn.execute("SELECT vec FROM embed WHERE key=?",
                                   (_key(k),)).fetchone()
                if row:
                    vec = pickle.loads(row[0])
                    break
        if vec is None:
            missing.append(t)
        else:
            emb.cache[t] = vec
    if conn is not None:
        conn.close()
    return missing


def _study_gw(secret_text, thr, lex, emb):
    gw = G.Gateway("l2", threshold=thr, lexical=lex, embed=emb)
    gw.register(secret_text, semantic=True)
    return gw


def _lexical_rule(secret_text, note_text, lex):
    """The study gateway's lexical sub-rule, evaluated standalone so the row
    records which layer would have fired (gateway._words normalization)."""
    fw = G._words(secret_text)
    if not fw:
        return False
    for s in G._SPLIT.split(note_text):
        s = s.strip()
        if not s:
            continue
        m = len(G._words(s) & fw)
        if m and m / len(fw) >= lex:
            return True
    return False


def score(pools, thr, lex, progress=True):
    """Returns list of (path, rows, stats) with study verdicts computed."""
    all_rows = [(p, r) for p in pools for r in _rows_of(p)]
    valid = [(p, r) for p, r in all_rows
             if not r.get("err") and (r.get("note") or "").strip()]

    # ---- pre-embed: secrets + gateway-segmented sentences of every note
    needed = set()
    for _, r in valid:
        needed.add(r["secret_text"])
        for s in G._SPLIT.split(r["note"]):
            s = s.strip()
            if s:
                needed.add(s)
    emb = G.OllamaEmbedder()
    missing = _seed_embedder(emb, sorted(needed))
    if progress:
        print(f"embed prep: {len(needed)} texts, {len(needed) - len(missing)} "
              f"from sqlite, {len(missing)} to embed", flush=True)
    if missing:
        t0 = time.time()
        emb.embed_many(missing, batch=32, progress=progress)
        if progress:
            print(f"embedded {len(missing)} in {time.time() - t0:.0f}s",
                  flush=True)

    per_pool = {p: [] for p in pools}
    gws = {}
    for path, r in all_rows:
        note = r.get("note") or ""
        if r.get("err") or not note.strip():
            per_pool[path].append(r)
            continue
        gw = gws.get(r["secret_text"])
        if gw is None:
            gw = _study_gw(r["secret_text"], thr, lex, emb)
            gws[r["secret_text"]] = gw
        clean, info = gw.filter(note)
        caught = clean != note
        d1_leak, _ident = jobs._d1_verdicts(note,
                                            jobs.RECORDS[r["secret_id"]])
        n = dict(r)
        if "replica_slip" not in n:          # keep first-seen replica columns
            n["replica_slip"] = r.get("slip")
            n["replica_filtered"] = r.get("gateway_filtered")
            n["replica_l2_hit"] = r.get("l2_hit")
            n["replica_lexical_hit"] = r.get("lexical_hit")
        n["gate_impl"] = "study"
        n["gateway_filtered"] = int(caught)
        n["l2_hit"] = int(info.get("l2", 0) > 0 or info.get("id", 0) > 0)
        n["lexical_hit"] = int(_lexical_rule(r["secret_text"], note, lex))
        n["slip"] = 0 if caught else 1
        n["d1_leak"] = int(d1_leak)
        n["slip_survived"] = int((not caught) and d1_leak)
        per_pool[path].append(n)

    out = []
    for path in pools:
        rows = per_pool[path]
        rep_dis = sum(1 for r in rows
                      if "replica_slip" in r
                      and bool(r.get("slip")) != bool(r["replica_slip"]))
        stats = {
            "n": len(rows),
            "n_valid": sum(1 for r in rows
                           if not r.get("err") and (r.get("note") or "").strip()),
            "slips_study": sum(r.get("slip", 0) for r in rows),
            "slips_replica": sum(1 for r in rows if r.get("replica_slip")),
            "slip_disagreements": rep_dis,
            "slip_survived": sum(r.get("slip_survived", 0) for r in rows),
        }
        out.append((path, rows, stats))
    return out


def report(out):
    for path, rows, s in out:
        print(f"\n=== {path} ===")
        print(f"  n={s['n']} valid={s['n_valid']}")
        print(f"  slip (study gateway)      {s['slips_study']}"
              f"  rate {s['slips_study'] / max(s['n_valid'], 1):.4f}")
        print(f"  slip (replica, original)  {s['slips_replica']}"
              f"  rate {s['slips_replica'] / max(s['n_valid'], 1):.4f}")
        print(f"  verdict disagreements     {s['slip_disagreements']}")
        print(f"  slip_survived (gate-pass AND D1 leak)  {s['slip_survived']}"
              f"   [PREREG H3 needs >= 300 per pool]")


def apply(out, dry_run=False):
    moved = []
    for path, rows, _s in out:
        if not rows:
            continue
        tmp = path + ".rescore_tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if not dry_run:
            os.replace(tmp, path)
        else:
            os.remove(tmp)
        print(f"{'[dry] ' if dry_run else ''}rescored {len(rows)} rows -> {path}")
    # quarantine artifacts derived under replica verdicts — ONCE.  A later
    # rescore (qwen pool) must not quarantine artifacts the llama stages have
    # already regenerated under study verdicts, so a marker file gates this.
    marker = Path("results/gatefix_v1_quarantined")
    dest = Path(f"results/stale_gatefix_{time.strftime('%Y%m%d_%H%M%S')}")
    files = [f for pat in STALE_PATTERNS for f in glob.glob(pat)]
    if files and not marker.exists() and not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.move(f, dest)
            moved.append(f)
        marker.write_text(f"quarantined {len(files)} files -> {dest}\n",
                          encoding="utf-8")
        print(f"quarantined {len(files)} stale derived artifact(s) -> {dest}/")
    elif files and marker.exists():
        print("quarantine already done once (marker present); leaving "
              "current derived artifacts alone")
    elif files:
        print(f"[dry] would quarantine: {', '.join(files)}")
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--pools", nargs="*", default=None)
    a = ap.parse_args()
    if not (a.report or a.apply):
        a.report = True
    pools = [p for p in (a.pools or POOLS) if os.path.exists(p)]
    if not pools:
        raise SystemExit("no pool files found")
    thr, lex = jobs._params()
    print(f"study gateway params: threshold={thr} lexical={lex}")
    out = score(pools, thr, lex)
    report(out)
    if a.apply:
        apply(out)
    print("done")


if __name__ == "__main__":
    main()