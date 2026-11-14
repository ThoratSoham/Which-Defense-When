#!/usr/bin/env python
"""Regenerate the six PNG files main.tex requires, next to the .tex file.

main.tex includes (missing files render as labelled placeholder boxes):

    fig1-ladder.png          T per defense, 95% CI, pooled + by secret type
                             <- make_figures.py fig1        [results_v2r.csv]
    fig2-pareto.png          leak rate vs task success      <- pareto.py
                             [results_v2.csv + results_v2_task.csv]
    fig3-outbreak.png        P(outbreak) by defense/topology (measured T)
                             <- sim_measured.py             [results_T.csv]
    fig4-protection.png      P(outbreak) vs fraction protected (initial study)
                             <- sim_protect.py              [results_v2.csv]
    fig5-validation.png      real vs simulated attack size <- make_figures.py fig3
                             [network_results_transcripts.jsonl + results_v2r.csv]
    fig6-other-secrets.png   recall / FP across thresholds, 12 secrets
                             <- make_figures.py fig2        [diversity_results.csv]

The generator scripts write their historical file names (fig1_ladder.png, ...);
this wrapper runs them and copies each output to the canonical hyphenated name,
so neither the generators nor main.tex change.

Run:
  python make_paper_figures.py            # regenerate everything
  python make_paper_figures.py --check    # only report which files exist/are stale
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

PY = sys.executable
HERE = Path(__file__).resolve().parent

# canonical name -> (script, argv, intermediate name the script writes)
FIGS = {
    "fig1-ladder.png": ("make_figures.py", [], "fig1_ladder.png"),
    "fig2-pareto.png": ("pareto.py", ["results_v2r.csv"], "fig_pareto.png"),
    "fig3-outbreak.png": ("sim_measured.py", ["results_v2r.csv"], "fig_outbreak_by_defense.png"),
    "fig4-protection.png": ("sim_protect.py", ["results_v2r.csv"], "fig_partial_protection.png"),
    "fig5-validation.png": ("make_figures.py", [], "fig3_validation.png"),
    "fig6-other-secrets.png": ("make_figures.py", ["diversity_results.csv"], "fig2_threshold.png"),
}

# make_figures.py emits fig1/fig5/fig6 in a single process, so run it once.
GEN_SCRIPTS = [
    ("make_figures.py", []),
    ("pareto.py", ["results_v2r.csv"]),
    ("sim_measured.py", ["results_v2r.csv"]),
    ("sim_protect.py", ["results_v2r.csv"]),
]


def check() -> dict:
    state = {}
    for canonical, (script, _, inter) in FIGS.items():
        c, i = HERE / canonical, HERE / inter
        state[canonical] = {
            "script": script,
            "exists": c.exists(),
            "age_s": time.time() - c.stat().st_mtime if c.exists() else None,
            "inter": inter,
            "inter_exists": i.exists(),
        }
    return state


def run_generators() -> list[tuple[str, int, float]]:
    results = []
    for script, argv in GEN_SCRIPTS:
        if not (HERE / script).exists():
            results.append((script, -1, 0.0))
            print(f"[skip] {script} not found")
            continue
        t0 = time.time()
        print(f"[run ] {script} {' '.join(argv)}".rstrip())
        p = subprocess.run([PY, "-u", script, *argv], cwd=HERE,
                           capture_output=True, text=True, errors="replace")
        dt = time.time() - t0
        results.append((script, p.returncode, dt))
        # keep the generator's own output visible but bounded
        tail = (p.stdout or "").strip().splitlines()[-4:]
        for line in tail:
            print(f"       {line}")
        if p.returncode != 0:
            err = (p.stderr or "").strip().splitlines()[-6:]
            print(f"       !! rc={p.returncode} ({dt:.0f}s)")
            for line in err:
                print(f"       {line}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report state only, regenerate nothing")
    args = ap.parse_args()

    if not args.check:
        run_generators()
        # copy intermediates to canonical names (skip if script produced nothing)
        print("\n[copy] intermediate -> canonical:")
        for canonical, (_, _, inter) in FIGS.items():
            src, dst = HERE / inter, HERE / canonical
            if src.exists():
                shutil.copyfile(src, dst)
                print(f"       {inter} -> {canonical}")
            else:
                print(f"       !! {inter} missing; {canonical} NOT updated "
                      f"(LaTeX will show a placeholder)")

    state = check()
    missing = [c for c, s in state.items() if not s["exists"]]
    print("\n[check] main.tex figures:")
    for canonical, s in state.items():
        if s["exists"]:
            mins = s["age_s"] / 60
            print(f"       OK   {canonical:24s} ({mins:.0f} min old, from {s['script']})")
        else:
            print(f"       MISS {canonical:24s} <- {s['script']}")
    if missing:
        print(f"\n{len(missing)} figure(s) missing; main.tex renders placeholders for them.")
        return 1
    print("\nall six figure files present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())