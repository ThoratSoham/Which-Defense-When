#!/usr/bin/env python
"""Sensitivity check for the caught-note residue claim (draft: "616 of 1391").

The residue paragraph in sec_persist counts, among the notes the study
gateway CAUGHT, how many still carry detectable secret content after
redaction -- using D1 alone.  The draft flags that this is
"detectable by the validated detector, not ground truth" and promises a
Phase-2 ensemble sensitivity check.  This script is that check.

For every caught note (hop2_repass records with src_slip == 0, the same
records and the same post-gateway text D1 scored):

  text   = record 'sent' (post-gateway / redacted text)
  d1     = record auto_leaked          (recomputed count must equal 616)
  d2     = NLI entailment note -> secret (same model + 0.5 boundary as Phase 2)
  d3     = cross-family local LLM judge  (same rubric/judge rotation as Phase 2)
  vote   = majority >= 2 of 3           (detectors/ensemble.ensemble_vote,
           ties/absent votes -> undetermined, never silently 0)

Reports the residue rate under D1 only (validation), under each detector,
and under the ensemble, all with Wilson 95% intervals.  D3 is checkpointed
to results/residue_d3.jsonl keyed by row_key, so re-runs only judge what is
missing.

Run:  python residue_ensemble.py             # full 1391
      python residue_ensemble.py --limit 5   # smoke test
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REPASS = Path("results/hop2_repass.jsonl")
D3CK = Path("results/residue_d3.jsonl")
OUT = Path("results/residue_ensemble.json")
EXPECTED_D1 = 616          # hop2_report.md: caught notes still leaking 616/1391


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def rate(k, n):
    lo, hi = wilson(k, n)
    return {"k": int(k), "n": int(n),
            "rate": (k / n if n else float("nan")),
            "ci": [lo, hi]}


def load_c_rows():
    rows = [json.loads(l) for l in REPASS.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    return [r for r in rows if not r.get("src_slip")]


def d3_done():
    done = {}
    if D3CK.exists():
        for line in D3CK.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("leak") in (0, 1):
                done[r["key"]] = int(r["leak"])
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="judge only the first N pending D3 calls (smoke test)")
    ap.add_argument("--skip-d3", action="store_true",
                    help="only d1/d2 (ensemble then needs >=2 of the 2 voted)")
    a = ap.parse_args()

    rows = load_c_rows()
    notes = [r.get("sent") or r.get("raw") or "" for r in rows]
    secrets = [r.get("secret") for r in rows]
    print(f"caught notes (c_rows): {len(rows)}")

    d1 = [int(bool(r.get("auto_leaked"))) for r in rows]
    print(f"d1 residue (as recorded): {sum(d1)}/{len(d1)}")
    if sum(d1) != EXPECTED_D1 or len(rows) != 1391:
        print(f"WARNING: expected {EXPECTED_D1}/1391 from hop2_report.md -- "
              f"the records changed; proceeding with what is on disk")

    from detectors.d2_nli import d2_batch
    d2 = [int(x["leak"]) for x in d2_batch(notes, secrets)]
    print(f"d2 residue: {sum(d2)}/{len(d2)}")

    done = d3_done()
    if not a.skip_d3:
        todo = [r for r in rows if r["row_key"] not in done]
        if a.limit:
            todo = todo[:a.limit]
        print(f"d3: {len(todo)} to judge ({len(done)} checkpointed)")
        if todo:
            from llm_client import LLMClient, load_config
            from detectors.d3_judge import judge_batch, pick_judge
            cfg = load_config()
            client = LLMClient(config_path="config.yaml")
            # batch by judge model: Ollama keeps one model resident at a time
            todo.sort(key=lambda r: pick_judge(r.get("model"), cfg))
            with D3CK.open("a", encoding="utf-8") as fh:
                for i, r in enumerate(todo, 1):
                    model = pick_judge(r.get("model"), cfg)
                    text = r.get("sent") or r.get("raw") or ""
                    try:
                        res = judge_batch([text], [r.get("secret")], model,
                                          client, note_ids=[r["row_key"]],
                                          log=lambda *x: None)[0]
                    except Exception as e:
                        print(f"  error {r['row_key']}: {type(e).__name__}: "
                              f"{str(e)[:120]}")
                        continue
                    leak = res.get("leak")
                    if leak in (0, 1):
                        fh.write(json.dumps({"key": r["row_key"],
                                             "judge_model": model,
                                             "leak": int(leak)},
                                            ensure_ascii=False) + "\n")
                        fh.flush()
                        done[r["row_key"]] = int(leak)
                    if i % 25 == 0:
                        print(f"  {i}/{len(todo)}")

    d3 = [done.get(r["row_key"], None) for r in rows]
    voted = [v for v in d3 if v is not None]
    print(f"d3 residue (on judged rows): {sum(voted)}/{len(voted)}")

    from detectors.ensemble import ensemble_vote
    ens, undet = [], 0
    for i in range(len(rows)):
        v = ensemble_vote({"d1": d1[i], "d2": d2[i],
                           "d3": d3[i] if d3[i] is not None else None})
        if v["ensemble"] is None:
            undet += 1
            ens.append(None)
        else:
            ens.append(int(v["ensemble"]))
    ens_n = sum(1 for e in ens if e is not None)
    ens_k = sum(e for e in ens if e is not None)

    out = {
        "n_caught": len(rows),
        "d1_only": rate(sum(d1), len(rows)),
        "d2_only": rate(sum(d2), len(rows)),
        "d3_only": rate(sum(voted), len(voted)),
        "ensemble": rate(ens_k, ens_n),
        "ensemble_undetermined": undet,
        "text": "post-gateway (redacted) text of notes the study gateway "
                "caught; residue = still detectable secret content",
        "validation_d1_matches_hop2_report": (sum(d1) == EXPECTED_D1
                                              and len(rows) == 1391),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print()
    for key in ("d1_only", "d2_only", "d3_only", "ensemble"):
        r = out[key]
        print(f"  {key:10s} {r['k']:4d}/{r['n']:4d} = {r['rate']:.3f}  "
              f"CI [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}]")
    if undet:
        print(f"  ensemble undetermined on {undet} rows "
              f"(fewer than 2 votes / tie)")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
