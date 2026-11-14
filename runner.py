"""Resumable, checkpointed job runner.

A job = list of cells (dicts) x episodes. For every (cell, episode) the runner
calls `episode_fn(cell, episode)`, writes the returned record(s) to a JSONL
transcript file, then marks the pair done in a SQLite checkpoint table.

Guarantees
  * transcripts are written BEFORE the checkpoint commit, so a crash can lose at
    most one episode's checkpoint marker (re-running it is a cache hit, not a
    duplicate experiment) — and analysis treats the JSONL as the source of truth.
  * re-running the same command skips finished cells (resume).
  * `max_minutes` slices a job cleanly so no single run needs to exceed the
    ~6 h approval threshold.

CLI:
  python runner.py --job <name> --list            # show pending cells
  python runner.py --job <name> [--dry-run] [--max-minutes 300]
"""
import argparse, json, os, sqlite3, sys, time

CKPT = os.path.join("results", "checkpoints.sqlite3")
SCHEMA = """CREATE TABLE IF NOT EXISTS done (
    job TEXT NOT NULL, cell_id TEXT NOT NULL, episode INTEGER NOT NULL,
    finished_at REAL, PRIMARY KEY (job, cell_id, episode));"""


def cell_id(cell: dict) -> str:
    return "|".join(f"{k}={cell[k]}" for k in sorted(cell))


def _ckpt_con(path=CKPT):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.commit()
    return con


def load_done(con, job):
    return {r[0] for r in con.execute("SELECT cell_id || '|' || episode FROM done WHERE job=?",
                                      (job,))}


def run_grid(job_name, cells, episode_fn, out_path, *, dry_run=False,
             max_minutes=None, progress_every=5, log=print):
    """Run all (cell, episode) pairs not yet done. Returns a summary dict."""
    con = _ckpt_con()
    done = load_done(con, job_name)
    pending = [(c, e) for c in cells for e in range(int(c.get("episodes", 1)))
               if f"{cell_id(c)}|{e}" not in done]
    total_pairs = len(cells) and sum(int(c.get("episodes", 1)) for c in cells)

    if dry_run:
        log(f"[dry-run] {job_name}: {total_pairs} (cell, episode) pairs, "
            f"{len(done)} done, {len(pending)} pending")
        for c in cells[:10]:
            log(f"   cell: {cell_id(c)}")
        return {"job": job_name, "pending": len(pending), "done": len(done), "dry_run": True}

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    t0, written, failed = time.time(), 0, 0
    with open(out_path, "a", encoding="utf-8") as fh:
        for i, (cell, ep) in enumerate(pending, 1):
            if max_minutes and (time.time() - t0) / 60 >= max_minutes:
                log(f"[slice] {job_name}: {max_minutes} min budget reached after "
                    f"{written} episodes; checkpointed — rerun to continue")
                break
            try:
                rec = episode_fn(cell, ep)
            except KeyboardInterrupt:
                log("[interrupt] checkpointed; rerun to resume"); raise
            except Exception as e:                    # keep a bad cell from killing a batch
                failed += 1
                log(f"  ERROR cell={cell_id(cell)} ep={ep}: {type(e).__name__}: {str(e)[:160]}")
                if failed >= 10:
                    log("[abort] 10 consecutive-capacity failures; stopping with checkpoint")
                    break
                continue
            recs = rec if isinstance(rec, list) else [rec]
            for r in recs:
                fh.write(json.dumps({"job": job_name, "cell": cell, "episode": ep,
                                     "ts": time.time(), **r}, ensure_ascii=False) + "\n")
            fh.flush()
            con.execute("INSERT OR REPLACE INTO done VALUES (?,?,?,?)",
                        (job_name, cell_id(cell), ep, time.time()))
            con.commit()
            written += 1
            if progress_every and written % progress_every == 0:
                rate = written / max(time.time() - t0, 1e-9)
                eta_min = (len(pending) - i) / max(rate, 1e-9) / 60
                log(f"  {job_name}: {written}/{len(pending)} episodes "
                    f"({rate:.2f}/s, ETA {eta_min:.0f} min, {failed} errors)")
    summary = {"job": job_name, "written": written, "failed": failed,
               "pending_after": len(pending) - written, "elapsed_s": time.time() - t0}
    log(f"[done] {job_name}: {summary}")
    return summary


def clear_job(job_name, out_path=None, confirm=True):
    """Test/utility: remove checkpoint rows (and optionally the transcript file)."""
    con = _ckpt_con()
    con.execute("DELETE FROM done WHERE job=?", (job_name,))
    con.commit()
    if out_path and os.path.exists(out_path) and confirm:
        os.remove(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-minutes", type=float, default=None)
    ap.add_argument("--only", action="append", default=None,
                    help="substring of the cell_id to run (repeatable; all must match). "
                         "Example: --only defense=none --only pressure=high")
    a = ap.parse_args()
    import jobs                                   # registry module defining JOBS
    spec = jobs.JOBS[a.job]
    cells = spec["cells"]()
    if a.only:
        cells = [c for c in cells
                 if all(s in cell_id(c) for s in a.only)]
        if not cells:
            sys.exit(f"no cells match --only {a.only}")
    run_grid(a.job, cells, spec["episode_fn"], spec["out"],
             dry_run=a.list or a.dry_run, max_minutes=a.max_minutes)


if __name__ == "__main__":
    main()
