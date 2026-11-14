#!/usr/bin/env python
"""Diagnostic: sim_slip p=1.0 floors at rho=0.873 vs old rho=0.95, 1000 runs/cell,
to size the Monte Carlo noise behind the published 200-run figures.
Writes results/diag_rho.txt.  No manuscript artifact depends on this file."""
import contextlib
import io
import sys

import sim

OUT = open("results/diag_rho.txt", "w", encoding="utf-8")


def run(rho, n, tag):
    buf = io.StringIO()
    sim.phase3_rho = lambda: (rho, 158 if rho == 0.873 else 20,
                              (0.813, 0.917) if rho == 0.873 else (0.768, 0.992))
    sys.argv = ["sim_slip.py", "network_results_transcripts.jsonl"]
    src = open("sim_slip.py", encoding="utf-8").read().replace(
        "N, RUNS, rng = 500, 200,", "N, RUNS, rng = 500, %d," % n)
    with contextlib.redirect_stdout(buf):
        exec(src, {"__name__": "__main__"})
    print("=== rho=%s, %d runs ===" % (tag, n), file=OUT, flush=True)
    for line in buf.getvalue().splitlines():
        if "/" in line and any(m in line for m in ("gemma", "llama", "qwen")):
            print(line, file=OUT, flush=True)


try:
    run(0.873, 1000, "0.873 (measured)")
    run(0.95, 1000, "0.95 (legacy n=20)")
finally:
    OUT.close()
    print("DIAG_DONE", flush=True)
