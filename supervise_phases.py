#!/usr/bin/env python
"""Round-robin supervisor for the remaining collection jobs (COMPUTE_PLAN §4).

Order (tier A, then tier B):
    A5  api_ladder       free-API frontier ladder        960 API calls
    A6  baselines        Phase 5 baselines, 1 model     2160 local calls
    A7  network_test     Phase 6.3 real networks        1980 local calls
    A8  ladder_test      Phase 4 scale grid, TEST       8640 local calls
    B1  network_partial  Phase 6.4 partial protection   2640 local calls
    B3  baselines2       Phase 5 baselines, 2 models    4320 local calls

Design rules:
  * every slice is `runner.py --job J --max-minutes N` (N <= 330, under the
    6 h approval rule), so nothing is one uninterrupted >6 h job
  * a healthy job is sliced repeatedly until it is DONE, then the next job
    starts — tier order is preserved and one heavy local job runs at a time
  * a job that makes no progress in a slice (free-tier 429s, Ollama down) is
    parked with exponential backoff (120 s -> 1800 s) and the round continues
    with the next job; parked jobs are revisited every round
  * all state lives in results/checkpoints.sqlite3, so killing this process
    (or a Freebuff restart) loses at most the in-flight episode; relaunching
    this file is always safe and never duplicates finished episodes
  * exits only when every job reports 0 pending, or after 96 consecutive
    zero-progress rounds (~8 h of pure backoff) — the log says which job is
    stuck.  Log: results/supervisor.log
"""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
import time

PY = sys.executable
ORDER = ["api_ladder", "baselines", "network_test", "ladder_test",
         "network_partial", "baselines2"]
SLICE_MIN = {"api_ladder": "120"}     # API job: revisit often, quotas reset daily
DEFAULT_SLICE_MIN = "330"             # local jobs: ~5.5 h per slice
PARK_MAX = 1800
PARK_FAIL_ROUNDS_EXIT = 96            # ~8 h of pure backoff with no progress
LOG = "results/supervisor.log"


def log(msg: str) -> None:
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def pending(job: str) -> int | None:
    try:
        r = subprocess.run([PY, "runner.py", "--job", job, "--list"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except Exception as e:                                   # pragma: no cover
        log(f"  pending({job}) raised {e!r}")
        return None
    txt = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"(\d+) pending", txt)
    if not m:
        tail = txt.strip().splitlines()[-1:]
        log(f"  pending({job}) unparseable: {tail}")
        return None
    return int(m.group(1))


def run_slice(job: str) -> tuple[int, int, object]:
    """Run one slice; return (pending_before, pending_after, returncode)."""
    p0 = pending(job)
    if not p0:
        return p0 or 0, p0 or 0, "already done"
    budget = SLICE_MIN.get(job, DEFAULT_SLICE_MIN)
    log(f"slice start {job}: {p0} pending, budget {budget} min")
    t0 = time.time()
    try:
        r = subprocess.run([PY, "runner.py", "--job", job,
                            "--max-minutes", budget])
        rc = r.returncode
    except KeyboardInterrupt:
        raise
    except Exception as e:                                   # pragma: no cover
        rc = f"exc {e!r}"
    p1 = pending(job)
    log(f"slice end   {job}: {p0} -> {p1} pending (rc={rc}, "
        f"{time.time()-t0:.0f}s)")
    return p0, p1, rc


def main() -> int:
    park: dict[str, float] = {}          # job -> earliest resume time
    park_backoff: dict[str, int] = {}
    dead_rounds = 0
    rounds = 0
    while True:
        rounds += 1
        state = {j: pending(j) for j in ORDER}
        log(f"round {rounds}: " + ", ".join(f"{j}={v}" for j, v in state.items()))
        if all(v == 0 for v in state.values()):
            log("ALL JOBS COMPLETE — supervisor exiting")
            return 0

        now = time.time()
        progress = False
        for job in ORDER:
            if state.get(job, 0) in (0, None):
                continue
            if park.get(job, 0) > now:
                continue
            # keep slicing this job until it stops progressing
            while True:
                p0, p1, rc = run_slice(job)
                if p0 == 0:
                    break                                   # finished meanwhile
                if p1 is not None and p1 < p0:
                    progress = True
                    park.pop(job, None)
                    park_backoff.pop(job, None)
                    if p1 > 0:
                        continue                            # healthy: next slice
                    break                                   # done
                # no progress: park with backoff, move to the next job
                b = min(max(park_backoff.get(job, 0) * 2, 120), PARK_MAX)
                park_backoff[job] = b
                park[job] = time.time() + b
                log(f"parked {job} for {b}s (no progress; rc={rc})")
                break

        if progress:
            dead_rounds = 0
        else:
            dead_rounds += 1
            if dead_rounds >= PARK_FAIL_ROUNDS_EXIT:
                stuck = [j for j in ORDER if state.get(j, 0)]
                log(f"GIVING UP after {dead_rounds} zero-progress rounds; "
                    f"still pending: {stuck} — investigate (rate limits? "
                    f"Ollama down?) and relaunch")
                return 2
            sleep_s = min(max(min(park.values(), default=120) - time.time(), 60),
                          PARK_MAX)
            log(f"no job progressed this round; sleeping {sleep_s:.0f}s")
            time.sleep(max(sleep_s, 1))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("interrupted — checkpoints intact; relaunch supervise_phases.py")
        sys.exit(130)
