#!/usr/bin/env bash
# Bounded wait for the H3(b) report gate.  Exit 0 = ready, 2 = stalled, 3 = heartbeat.
cd "/e/MAS Reference" || exit 1
start=$(date +%s); last=-1; stall=0
while :; do
  if [ -f results/hop2_report.md ] && [ results/hop2_report.md -nt results/hop2_rewrite.jsonl ]; then
    echo "REPORT_READY $(date '+%T')"; exit 0
  fi
  n=$(wc -l < results/hop2_rewrite.jsonl 2>/dev/null || echo 0)
  if [ "$n" = "$last" ]; then stall=$((stall+1)); else stall=0; fi
  last=$n
  now=$(date +%s)
  if [ "$stall" -ge 25 ]; then echo "STALLED rows=$n $(date '+%T')"; exit 2; fi
  if [ $((now-start)) -ge 560 ]; then
    s=$(grep -c '"condition": "slip"' results/hop2_rewrite.jsonl 2>/dev/null || echo "?")
    echo "heartbeat rows=$n slip=$s $(date '+%T')"; exit 3
  fi
  sleep 30
done
