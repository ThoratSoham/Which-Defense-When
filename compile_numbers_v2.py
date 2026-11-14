"""Compile all Round 2 simulation and empirical metrics into results/numbers_v2.json.
Every number is loaded from its producing job artifact with full provenance.
"""
from __future__ import annotations

import json
import os
import time
import numpy as np

MASTER_SEED = 20261113
OUT_PATH = "results/numbers_v2.json"

def compile_all():
    print("=== Compiling results/numbers_v2.json ===")
    
    out = {
        "metadata": {
            "date": "2026-11-13",
            "branch": "v2-revision",
            "git_tag": "prereg-v2",
            "git_commit": "3631432",
            "master_seed": MASTER_SEED,
            "status": "Round 2 pre-registered execution"
        }
    }
    
    # 1. Job 7 (J7): Theory Check & 500-Agent Simulations
    j7_path = "results/j7_theory_results.json"
    if os.path.exists(j7_path):
        out["job_7_theory"] = json.load(open(j7_path, encoding="utf-8"))
        print("  Loaded Job 7 theory & 500-agent results")
    else:
        print("  Warning: Job 7 results not found")
        
    # 2. Job 1 (J1): Free-Text Entangled Evaluation
    j1_path = "results/j1_freetext_summary.json"
    if os.path.exists(j1_path):
        out["job_1_freetext"] = json.load(open(j1_path, encoding="utf-8"))
        print("  Loaded Job 1 free-text summary")
    elif os.path.exists("results/j1_freetext_transcripts.jsonl"):
        # Partial/interim aggregation from transcripts
        rows = [json.loads(l) for l in open("results/j1_freetext_transcripts.jsonl", encoding="utf-8") if l.strip()]
        from collections import defaultdict
        by_def = defaultdict(list)
        for r in rows:
            by_def[r["defense"]].append(r)
        interim = {}
        for d, d_rows in by_def.items():
            interim[d] = {
                "n_interim": len(d_rows),
                "k_ens": sum(r["ensemble"] for r in d_rows),
                "T_ens": float(np.mean([r["ensemble"] for r in d_rows])),
                "k_d1": sum(r["d1"] for r in d_rows),
                "T_d1": float(np.mean([r["d1"] for r in d_rows])),
                "mean_u": float(np.mean([r["usefulness"] for r in d_rows]))
            }
        out["job_1_freetext_interim"] = interim
        print(f"  Loaded Job 1 interim transcripts ({len(rows)} rows)")
        
    # 3. Base Ladder & Baselines from frozen results/numbers.json
    if os.path.exists("results/numbers.json"):
        base_num = json.load(open("results/numbers.json", encoding="utf-8"))
        for k, v in base_num.items():
            out[k] = v
        out["ladder_test"] = base_num.get("ladder", {})
        out["baselines"] = base_num.get("baselines", {})
        out["persistence_exploratory"] = base_num.get("persistence", {})
        print("  Loaded all sections from results/numbers.json")
        
    # 4. Job 8 (J8): Profiling Benchmarks
    j8_path = "results/j8_profiling.json"
    if os.path.exists(j8_path):
        out["job_8_profiling"] = json.load(open(j8_path, encoding="utf-8"))
        print("  Loaded Job 8 profiling metrics")
        
    # 5. Job 3 (J3): Double Annotation Metrics
    j3_path = "results/j3_double_annotation.json"
    if os.path.exists(j3_path):
        out["job_3_double_annotation"] = json.load(open(j3_path, encoding="utf-8"))
        print("  Loaded Job 3 double annotation metrics")
        
    # 6. Job 2 (J2): Multi-Hop Chain
    j2_path = "results/j2_chain_summary.json"
    if os.path.exists(j2_path):
        out["job_2_chain"] = json.load(open(j2_path, encoding="utf-8"))
        print("  Loaded Job 2 chain summary")
        
    # 7. Job 5 (J5): Slip Taxonomy
    j5_path = "results/j5_slip_taxonomy.json"
    if os.path.exists(j5_path):
        out["job_5_taxonomy"] = json.load(open(j5_path, encoding="utf-8"))
        print("  Loaded Job 5 taxonomy metrics")
        
    # 8. Job 9 (J9): Rubric Usefulness
    j9_path = "results/j9_rubric_usefulness.json"
    if os.path.exists(j9_path):
        out["job_9_rubric"] = json.load(open(j9_path, encoding="utf-8"))
        print("  Loaded Job 9 rubric usefulness")
        
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Saved compiled master numbers to {OUT_PATH}")

if __name__ == "__main__":
    compile_all()

