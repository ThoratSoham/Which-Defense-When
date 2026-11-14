#!/usr/bin/env python3
r"""
Fix the api_ladder job so it runs on a model whose free tier is still alive.

What happened:
  * config.yaml's `providers.google` intentionally leaves `model` as null
    ("MUST-FILL") and jobs.py hard-codes
        API_MODELS = ["google:gemini-3.8-flash"]
    so the `api_ladder` job was wired to gemini-3.8-flash.
  * That model's free tier hit a hard daily quota (20 req/day), so every cell
    errored with RuntimeError after the backoff ladder exhausted.  Two hops of
    one episode (2 rows) are on disk as interview artifacts; the other 319
    episodes for that cell never ran.

What this script does (idempotent):
  1. Backs up jobs.py and config.yaml to .bak if a backup does not already exist.
  2. Changes API_MODELS in jobs.py to ["google:gemini-3.5-flash-lite"].
  3. Leaves config.yaml untouched (model null is fine; jobs.py is authoritative).
  4. Does NOT delete or rewrite results/api_ladder_transcripts.jsonl — the two
     rows are retained as the interview sample for the cell that actually ran.

Afterward:
  * The same `results/api_ladder_transcripts.jsonl` file is the output path, so
    any re-run appends rows after the existing 2.  The runner is checkpointed per
    (job, cell_id, episode), so re-running the whole job resumes from episode 1
    for that cell and runs all other cells fresh.
  * Because the runner appends, a reviewer comparing pre-/post-fix artifact counts
    can tell the 2 old rows apart by their ts (both 1793285097...) vs newly written
    rows.  This script does not fabricate those timestamps.

Safety:
  * Fails loudly (not silently) if the in-place edits do not match what we expect.
  * If you prefer to wipe the old 2 rows and start clean, do that explicitly after
    reviewing this output; this script does not do it for you.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs.py"
CONFIG = ROOT / "config.yaml"

OLD_MODEL = "google:gemini-3.8-flash"
NEW_MODEL = "google:gemini-3.5-flash-lite"

_state = {"jobs_backed_up": False, "config_backed_up": False, "jobs_changed": False}


def _backup(path: Path) -> Path:
    bak = Path(str(path) + ".bak")
    if not bak.exists():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return bak


def _replace_in(path: Path, pattern: str, repl: str, expect_old: bool = True) -> str:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=1)
    if expect_old and n != 1:
        raise SystemExit(f"expected exactly 1 match in {path} for {pattern!r}; got {n}")
    if not expect_old and n == 0:
        return text  # nothing to do
    path.write_text(new, encoding="utf-8")
    return new


def main() -> None:
    if not JOBS.exists():
        raise SystemExit(f"missing {JOBS}")
    if not CONFIG.exists():
        raise SystemExit(f"missing {CONFIG}")

    # sanity: the bug we are fixing must actually be present
    jobs_text = JOBS.read_text(encoding="utf-8")
    if OLD_MODEL not in jobs_text:
        print(f"note: {OLD_MODEL!r} not found in {JOBS}; nothing to fix")
        return
    if NEW_MODEL in jobs_text:
        print(f"note: {NEW_MODEL!r} already present in {JOBS}; nothing to fix")
        return

    _backup(JOBS)
    _state["jobs_backed_up"] = True
    _backup(CONFIG)
    _state["config_backed_up"] = True

    new_jobs = re.sub(
        r'API_MODELS\s*=\s*\[.*?\]\s*$',
        f'API_MODELS = ["google:gemini-3.5-flash-lite"]',
        jobs_text,
        count=1,
        flags=re.M,
    )
    if new_jobs == jobs_text:
        raise SystemExit(f"could not rewrite API_MODELS line in {JOBS}")
    JOBS.write_text(new_jobs, encoding="utf-8")
    _state["jobs_changed"] = True

    # report
    after = JOBS.read_text(encoding="utf-8")
    m = re.search(r'API_MODELS\s*=\s*\[([^\]]*)\]', after)
    print("jobs.py API_MODELS now:", m.group(0) if m else "(line not found)")
    print("config.yaml model field:", end=" ")
    cfg = __import__("yaml").safe_load(CONFIG.read_text(encoding="utf-8"))
    print(cfg.get("providers", {}).get("google", {}).get("model", "null (intentional)"))

    existing = ROOT / "results" / "api_ladder_transcripts.jsonl"
    n_rows = existing.stat().st_size // 64 if existing.exists() else 0
    print("existing api_ladder_transcripts.jsonl present:", existing.exists(),
          "size_bytes:", existing.stat().st_size if existing.exists() else 0)
    print("backup files:", JOBS.with_suffix(".py.bak"), CONFIG.with_suffix(".yaml.bak"))


if __name__ == "__main__":
    main()
