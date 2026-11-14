"""Job 8 (J8): Gateway Latency, CPU, and RAM Profiling
Pre-registered in PREREG_v2.md §5.
Profiles L1, L2, and B6 across 200 notes to measure latency (ms/note),
throughput (notes/sec), and memory overhead.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import re
import sys
import time
import tracemalloc

import numpy as np

import gateway

SAMPLE_N = 200
OUT_PATH = "results/j8_profiling.json"

def load_notes_sample(n: int = SAMPLE_N) -> list[str]:
    notes = []
    # Load from available transcripts
    paths = [
        "results/j1_freetext_transcripts.jsonl",
        "results/network_test_transcripts.jsonl",
        "results/ladder_test_transcripts.jsonl"
    ]
    for p in paths:
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                line = line.strip()
                if line:
                    r = json.loads(line)
                    text = r.get("sent") or r.get("raw") or ""
                    if len(text.strip()) > 30 and text not in notes:
                        notes.append(text)
                        if len(notes) >= n:
                            break
        if len(notes) >= n:
            break
            
    # If still fewer than n, duplicate/pad deterministically
    if len(notes) < n and notes:
        while len(notes) < n:
            notes.append(notes[len(notes) % len(notes)])
    return notes[:n]

def profile_l1(notes: list[str], secret_text: str, ident: str) -> dict:
    gw = gateway.Gateway("l1")
    gw.register(secret_text, token=ident)
    
    # Warmup
    for _ in range(5):
        gw.filter(notes[0])
        
    latencies = []
    tracemalloc.start()
    t0 = time.perf_counter()
    for note in notes:
        t_start = time.perf_counter()
        clean, info = gw.filter(note)
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000.0) # in ms
    total_time = time.perf_counter() - t0
    cur_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return {
        "n_notes": len(notes),
        "mean_latency_ms": round(float(np.mean(latencies)), 3),
        "median_latency_ms": round(float(np.median(latencies)), 3),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 3),
        "p99_latency_ms": round(float(np.percentile(latencies, 99)), 3),
        "throughput_notes_per_sec": round(len(notes) / total_time, 1),
        "peak_memory_kb": round(peak_mem / 1024.0, 1)
    }

def profile_l2(notes: list[str], secret_text: str, embedder) -> dict:
    gw = gateway.Gateway("l2", threshold=0.78, lexical=0.60, embed=embedder)
    gw.register(secret_text, semantic=True)
    
    # Warmup
    for _ in range(3):
        gw.filter(notes[0])
        
    latencies = []
    tracemalloc.start()
    t0 = time.perf_counter()
    for note in notes:
        t_start = time.perf_counter()
        clean, info = gw.filter(note)
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000.0)
    total_time = time.perf_counter() - t0
    cur_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return {
        "n_notes": len(notes),
        "mean_latency_ms": round(float(np.mean(latencies)), 3),
        "median_latency_ms": round(float(np.median(latencies)), 3),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 3),
        "p99_latency_ms": round(float(np.percentile(latencies, 99)), 3),
        "throughput_notes_per_sec": round(len(notes) / total_time, 1),
        "peak_memory_kb": round(peak_mem / 1024.0, 1)
    }

def profile_b7_regex(notes: list[str]) -> dict:
    gw = gateway.AutoGateway(judge=None, regex=True)
    
    # Warmup
    for _ in range(5):
        gw.filter(notes[0])
        
    latencies = []
    tracemalloc.start()
    t0 = time.perf_counter()
    for note in notes:
        t_start = time.perf_counter()
        clean, info = gw.filter(note)
        t_end = time.perf_counter()
        latencies.append((t_end - t_start) * 1000.0)
    total_time = time.perf_counter() - t0
    cur_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return {
        "n_notes": len(notes),
        "mean_latency_ms": round(float(np.mean(latencies)), 3),
        "median_latency_ms": round(float(np.median(latencies)), 3),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 3),
        "p99_latency_ms": round(float(np.percentile(latencies, 99)), 3),
        "throughput_notes_per_sec": round(len(notes) / total_time, 1),
        "peak_memory_kb": round(peak_mem / 1024.0, 1)
    }

def main():
    print("=== Running Job 8: Gateway Latency, CPU & RAM Profiling ===")
    notes = load_notes_sample(SAMPLE_N)
    print(f"Loaded {len(notes)} benchmark notes for profiling.")
    
    secret_text = "patient eqo was diagnosed with stage-2 renal failure"
    ident = "eqo"
    
    embed_path = "results/embed_cache_ladder.pickle"
    embedder = gateway.OllamaEmbedder(cache_path=embed_path if os.path.exists(embed_path) else None)
    embedder.path = embed_path
    
    print("Profiling L1 (Exact Match Regex)...")
    res_l1 = profile_l1(notes, secret_text, ident)
    print(f"  L1: Mean = {res_l1['mean_latency_ms']} ms, Throughput = {res_l1['throughput_notes_per_sec']} notes/s")
    
    print("Profiling B7 (PII Regex Filter)...")
    res_b7 = profile_b7_regex(notes)
    print(f"  B7: Mean = {res_b7['mean_latency_ms']} ms, Throughput = {res_b7['throughput_notes_per_sec']} notes/s")
    
    print("Profiling L2 (Semantic Cosine Filter)...")
    res_l2 = profile_l2(notes, secret_text, embedder)
    print(f"  L2: Mean = {res_l2['mean_latency_ms']} ms, Throughput = {res_l2['throughput_notes_per_sec']} notes/s")
    
    out = {
        "l1_exact": res_l1,
        "b7_pii_regex": res_b7,
        "l2_semantic": res_l2,
        "hardware_context": {
            "os": sys.platform,
            "sample_size": len(notes)
        }
    }
    
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Saved profiling benchmarks to {OUT_PATH}")

if __name__ == "__main__":
    main()

