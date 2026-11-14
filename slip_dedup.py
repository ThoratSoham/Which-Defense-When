#!/usr/bin/env python
"""
Deduplicate results/slip_gen_v3_boundary_dev.jsonl by (secret_id, prompt_variant, trial_index),
keeping the last occurrence of each key (most recent run).  Idempotent; prints before/after counts.
"""
from __future__ import annotations
import json, pathlib
from collections import OrderedDict

SRC = pathlib.Path("results/slip_gen_v3_boundary_dev.jsonl")
if not SRC.exists():
    print("no source file")
    raise SystemExit

lines = [l for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
before = len(lines)
seen = OrderedDict()
for line in lines:
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    key = (r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))
    seen[key] = line  # keep last
kept = list(seen.values())
after = len(kept)
dropped = before - after
if dropped:
    SRC.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"deduped: before={before}, after={after}, dropped={dropped}")
else:
    print(f"no duplicates: before={before}, after={after}")

# recount
rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
from collections import Counter
by_variant = Counter(r["prompt_variant"] for r in rows)
by_secret = Counter(r["secret_id"] for r in rows)
slips = [r for r in rows if r.get("slip")]
print("rows:", len(rows), "slips:", len(slips))
print("by variant:", dict(by_variant))
print("by secret:", dict(by_secret))
print("bytes:", SRC.stat().st_size)
