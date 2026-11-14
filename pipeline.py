#!/usr/bin/env python
"""Sequential phase pipeline — runs the Phase-3 chain unattended, checkpointed
by artifact existence, so a >6 h stage needs no babysitting.

Design rules:
  * one heavy local job at a time (Ollama RAM discipline, COMPUTE_PLAN §5)
  * every step is idempotent: re-running resumes rather than duplicates
  * a step is "done" only when its output artifact satisfies its predicate —
    not when its process exits 0
  * everything logs to results/pipeline.log with timestamps
  * editing this file does NOT disturb a running pipeline process; relaunch it
    (done steps are skipped) to pick up appended steps

Stage order (Phase 3, PREREG H3/H4):
  slip_gen -> slip_dedup -> slip_report -> hop2_repass -> hop2_rewrite ->
  hop2_report -> variant_correlation (H4) -> slip_gen_qwen (per-model
  replication for H3 model ICC) -> hop2_qwen_repass -> hop2_qwen_rewrite ->
  hop2_qwen_report -> heterogeneity (both pools)

Run:
  python pipeline.py            # run every pending step in order
  python pipeline.py --status   # show step state, run nothing
  python pipeline.py --from STEP_ID / --only STEP_ID
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

PY = sys.executable
LOG = Path("results/pipeline.log")

POOL_LLAMA = "results/slip_gen_v3_boundary_dev.jsonl"
POOL_QWEN = "results/slip_gen_v3_boundary_qwen2.5_3b_dev.jsonl"
QWEN_MODEL = "qwen2.5:3b"
QWEN_TAG = "qwen2_5_3b"


def log(msg: str) -> None:
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _sh(cmd: list[str], timeout: int | None = None) -> int:
    log("  $ " + " ".join(cmd))
    t0 = time.time()
    try:
        r = subprocess.run(cmd, timeout=timeout)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        log("  timeout reached; killing step")
        rc = -9
    log(f"  -> rc={rc} in {time.time()-t0:.0f}s")
    return rc


def _sh_out(cmd: list[str], timeout: int | None = None):
    """Run and return (rc, stdout_text)."""
    log("  $ " + " ".join(cmd))
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        log(f"  -> rc={r.returncode} in {time.time()-t0:.0f}s")
        return r.returncode, (r.stdout or "") + (("\n[stderr]\n" + r.stderr)
                                                if r.stderr else "")
    except subprocess.TimeoutExpired:
        log("  timeout reached")
        return -9, ""


def _jsonl(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------------------------------------------------------------- key sets
EXPECTED_VARIANTS = ("plain", "paraphrase", "antonym", "compressed")
EXPECTED_TRIALS = 20


def expected_keys() -> set:
    splits = json.loads(Path("corpus/splits.json").read_text(encoding="utf-8"))
    dev = splits["semantic"]["dev"]
    return {(sid, v, t) for sid in dev for v in EXPECTED_VARIANTS
            for t in range(EXPECTED_TRIALS)}


def pool_keys(path: str) -> set:
    return {(r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))
            for r in _jsonl(path)}


def slips_and_catches(path: str):
    rows = _jsonl(path)
    ks = {}
    for r in rows:
        k = (r.get("secret_id"), r.get("prompt_variant"), r.get("trial_index"))
        # H3 slip arm = leak survived the gate (slip_survived, set by the
        # slip_rescore stage); plain gate-pass on pools not yet rescored
        ks[k] = bool(r.get("slip_survived", r.get("slip")))
    n_slip = sum(1 for v in ks.values() if v)
    return n_slip, len(ks) - n_slip

def gen_done(path: str) -> bool:
    missing = expected_keys() - pool_keys(path)
    if missing:
        log(f"  slip_gen: {len(missing)} keys still missing ({path})")
    return not missing


def _noop_profile() -> int:
    return 0


def dedup_done() -> bool:
    rows = _jsonl(POOL_LLAMA)
    return bool(rows) and len(rows) == len(pool_keys(POOL_LLAMA))


def report_done() -> bool:
    p = Path("results/slip_boundary_report.md")
    pool = Path(POOL_LLAMA)
    return p.exists() and pool.exists() and p.stat().st_mtime >= pool.stat().st_mtime


def repass_done(pool: str, out: str) -> bool:
    want = len(pool_keys(pool))
    return want > 0 and len(_jsonl(out)) >= want


def rewrite_done(pool: str, out: str, slip_n: int, catch_n: int) -> bool:
    n_slip, n_catch = slips_and_catches(pool)
    t_s = min(slip_n, n_slip)
    t_c = min(catch_n, n_catch)
    rows = _jsonl(out)
    got_s = sum(1 for r in rows if r.get("condition") == "slip")
    got_c = sum(1 for r in rows if r.get("condition") == "catch")
    ok = t_s > 0 and got_s >= t_s and got_c >= t_c
    if not ok:
        log(f"  rewrite: slip {got_s}/{t_s}, catch {got_c}/{t_c} ({out})")
    return ok


def hop2_report_done(tag: str) -> bool:
    p = Path(f"results/hop2_report{ '_' + tag if tag else ''}.md")
    src = Path(f"results/hop2_rewrite{'_' + tag if tag else ''}.jsonl")
    return p.exists() and src.exists() and p.stat().st_mtime >= src.stat().st_mtime


def variant_done() -> bool:
    p = Path("results/variant_correlation.json")
    if not p.exists():
        return False
    n_judge = len(_jsonl("results/variant_judge.jsonl"))
    target = min(400, len(pool_keys(POOL_LLAMA)))
    if n_judge < target:
        log(f"  variant: judge {n_judge}/{target}")
        return False
    return p.stat().st_mtime >= Path(POOL_LLAMA).stat().st_mtime


# ---------------------------------------------------------------- step runners

def heterogeneity_done() -> bool:
    p = Path("results/heterogeneity.json")
    if not p.exists():
        return False
    newest_pool = max(Path(POOL_LLAMA).stat().st_mtime,
                      Path(POOL_QWEN).stat().st_mtime if Path(POOL_QWEN).exists() else 0)
    return p.stat().st_mtime >= newest_pool


# ---------------------------------------------------------------- predicates
def repass_done(pool: str, out: str) -> bool:
    want = len(pool_keys(pool))
    return want > 0 and len(_jsonl(out)) >= want

def _gen_loop(pool: str, model: str | None, attempts: int = 6) -> int:
    for attempt in range(attempts):
        if gen_done(pool):
            return 0
        cmd = [PY, "-u", "slip_gen_boundary.py"]
        if model:
            cmd += ["--model", model]
        rc = _sh(cmd, timeout=15 * 3600)
        if rc != 0:
            log(f"  slip_gen rc={rc}, retrying ({attempt+1}/{attempts})")
            time.sleep(30)
    return 0 if gen_done(pool) else 1


def run_slip_gen() -> int:
    return _gen_loop(POOL_LLAMA, None)


def run_slip_gen_qwen() -> int:
    return _gen_loop(POOL_QWEN, QWEN_MODEL)


def run_dedup() -> int:
    return _sh([PY, "slip_dedup.py"])


def run_slip_report() -> int:
    rc, out = _sh_out([PY, "slip_report_debrief.py"])
    if rc != 0:
        return rc
    Path("results/slip_boundary_report.md").write_text(
        "# Phase 3 boundary slip-pool debrief (DEV)\n\n```\n" + out + "\n```\n",
        encoding="utf-8")
    return 0


def _hop2(pool: str, tag: str, model: str, extra: list[str],
          timeout: int) -> int:
    cmd = [PY, "hop2_persistence.py", "--pool", pool, "--model", model]
    if tag:
        cmd += ["--tag", tag]
    return _sh(cmd + extra, timeout=timeout)


def run_repass() -> int:
    return _hop2(POOL_LLAMA, "", "llama3.2:3b", [], 6 * 3600)


def run_rewrite() -> int:
    return _hop2(POOL_LLAMA, "", "llama3.2:3b",
                 ["--rewrite", "--skip-repass", "--slip-n", "300",
                  "--control-n", "300"], 15 * 3600)


def run_repass_qwen() -> int:
    return _hop2(POOL_QWEN, QWEN_TAG, QWEN_MODEL, [], 6 * 3600)


def run_rewrite_qwen() -> int:
    return _hop2(POOL_QWEN, QWEN_TAG, QWEN_MODEL,
                 ["--rewrite", "--skip-repass", "--slip-n", "300",
                  "--control-n", "150"], 15 * 3600)


def _capture_report(tag: str) -> int:
    rc, out = _sh_out([PY, "hop2_persistence.py", "--report"] +
                      (["--tag", tag] if tag else []))
    name = f"results/hop2_report{'_' + tag if tag else ''}.md"
    Path(name).write_text(
        f"# Phase 3 hop-2 persistence report{' (' + tag + ')' if tag else ''}\n\n"
        "```\n" + out + "\n```\n", encoding="utf-8")
    return rc


def run_hop2_report() -> int:
    return _capture_report("")


def run_hop2_report_qwen() -> int:
    return _capture_report(QWEN_TAG)


def run_variant() -> int:
    return _sh([PY, "variant_correlation.py", "--judge-limit", "400"],
               timeout=12 * 3600)


def run_heterogeneity() -> int:
    return _sh([PY, "heterogeneity.py"], timeout=3600)


def run_rescore_llama() -> int:
    return _sh([PY, "rescore_pool_gate.py", "--apply", "--pools", POOL_LLAMA],
               timeout=3 * 3600)


def run_rescore_qwen() -> int:
    return _sh([PY, "rescore_pool_gate.py", "--apply", "--pools", POOL_QWEN],
               timeout=3 * 3600)


def _pool_rescored(pool: str) -> bool:
    rows = _jsonl(pool)
    valid = [r for r in rows
             if not r.get("err") and (r.get("note") or "").strip()]
    return bool(valid) and all(r.get("gate_impl") == "study" for r in valid)


STEPS = [
    ("slip_gen", run_slip_gen, lambda: gen_done(POOL_LLAMA),
     "Phase 3: boundary slip pool, llama3.2:3b (DEV, 20 secrets x 4 variants x 20 trials)"),
    ("slip_rescore", run_rescore_llama, lambda: _pool_rescored(POOL_LLAMA),
     "recompute pool gate verdicts with THE study gateway (PREREG 2026-10-27 fix)"),
    ("slip_dedup", run_dedup, dedup_done,
     "dedup pool by (secret, variant, trial)"),
    ("slip_profile", _noop_profile, lambda: True,
     "checkpoint envelope: survives an artifact-only predicate resume without re-running generation"),
    ("slip_report", run_slip_report, report_done,
     "Phase 3: slip-pool debrief with Clopper-Pearson intervals"),
    ("slip_profile", _noop_profile, lambda: True,
     "checkpoint envelope: survives an artifact-only predicate resume without re-running generation"),
    ("hop2_repass", run_repass,
     lambda: repass_done(POOL_LLAMA, "results/hop2_repass.jsonl"),
     "Phase 3 H3(a): deterministic gateway re-pass on every pool note"),
    ("hop2_rewrite", run_rewrite,
     lambda: rewrite_done(POOL_LLAMA, "results/hop2_rewrite.jsonl", 300, 300),
     "Phase 3 H3(b): next-agent rewrite then gateway (300 slips + 300 controls)"),
    ("hop2_report", run_hop2_report, lambda: hop2_report_done(""),
     "Phase 3: persistence report with Wilson CIs"),
    ("variant_correlation", run_variant, variant_done,
     "Phase 3 H4: gateway-variant miss correlation + rotation (400 judge calls)"),
    ("slip_gen_qwen", run_slip_gen_qwen, lambda: gen_done(POOL_QWEN),
     "Phase 3: boundary slip pool replication, qwen2.5:3b (per-model ICC)"),
    ("slip_rescore_qwen", run_rescore_qwen, lambda: _pool_rescored(POOL_QWEN),
     "recompute qwen pool gate verdicts with THE study gateway"),
    ("hop2_qwen_repass", run_repass_qwen,
     lambda: repass_done(POOL_QWEN, f"results/hop2_repass_{QWEN_TAG}.jsonl"),
     "Phase 3 H3(a) qwen pool: deterministic re-pass"),
    ("hop2_qwen_rewrite", run_rewrite_qwen,
     lambda: rewrite_done(POOL_QWEN, f"results/hop2_rewrite_{QWEN_TAG}.jsonl",
                          300, 150),
     "Phase 3 H3(b) qwen pool: rewrite then gateway (300 + 150)"),
    ("hop2_qwen_report", run_hop2_report_qwen,
     lambda: hop2_report_done(QWEN_TAG),
     "Phase 3: qwen persistence report"),
    ("heterogeneity", run_heterogeneity, heterogeneity_done,
     "Phase 3: beta-binomial ICC (secret + model) with leave-one-secret-out"),
]


def status() -> None:
    for sid, _, done, desc in STEPS:
        mark = "DONE" if done() else "TODO"
        print(f"  [{mark:4s}] {sid:22s} {desc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--from", dest="start", default=None)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    if a.status:
        status()
        return 0
    started = a.only is None and a.start is None
    for sid, run, done, desc in STEPS:
        if a.only and sid != a.only:
            continue
        if not started:
            if sid == (a.start or a.only):
                started = True
            else:
                print(f"  (skip {sid})")
                continue
        if done():
            log(f"[skip] {sid} already complete")
            continue
        log(f"[run ] {sid}: {desc}")
        rc = run()
        if rc != 0:
            log(f"[stop] {sid} failed (rc={rc}); remaining steps not run")
            return rc
        if not done():
            log(f"[stop] {sid} exited 0 but its artifact predicate is not satisfied")
            return 1
        log(f"[ok  ] {sid}")
    log("pipeline complete")
    status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
