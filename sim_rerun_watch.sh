#!/usr/bin/env bash
# Waits for the Phase 3 H3(b) report, refreshes results/numbers.json, then
# re-runs the blind-spot simulations with rho_rewrite in place of the legacy
# n=20 relay estimate (the sim_* scripts read it via sim.phase3_rho()).
# Logs to results/sim_rerun.log and exits.  Detached: survives session restarts.
cd "/e/MAS Reference" || exit 1
PY="./.venv/Scripts/python"
LOG="results/sim_rerun.log"
echo "[watch] armed $(date '+%F %T')" >> "$LOG"

# Gate: hop2_report.md must exist and be newer than the rewrite jsonl it summarizes
while true; do
  if [ -f results/hop2_report.md ] && [ -f results/hop2_rewrite.jsonl ] \
     && [ results/hop2_report.md -nt results/hop2_rewrite.jsonl ]; then
    break
  fi
  # keep waiting even if the pipeline stops with a failure: the report gate stays closed
  sleep 120
done
echo "[watch] report ready $(date '+%F %T'); refreshing numbers.json" >> "$LOG"

"$PY" paper_numbers.py >> "$LOG" 2>&1

if "$PY" -c "import sys; from sim import phase3_rho; sys.exit(0 if phase3_rho() else 1)"; then
  echo "[watch] rho gate open -> sim_final --runs 200" >> "$LOG"
  "$PY" sim_final.py results_v2r.csv network_results_transcripts.jsonl --runs 200 >> "$LOG" 2>&1
  echo "[watch] sim_final rc=$? -> sim_slip" >> "$LOG"
  "$PY" sim_slip.py network_results_transcripts.jsonl >> "$LOG" 2>&1
  echo "[watch] sim_slip rc=$?  SIM_RERUN_DONE $(date '+%F %T')" >> "$LOG"
else
  echo "[watch] SKIP: rho gate still closed after report (rewrite slip arm < 100 rows?)" >> "$LOG"
fi