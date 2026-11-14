"""One-off bookkeeping (2026-10-31): quarantine stale api_ladder rows, append the
PREREG §6 amendment for the frontier-model slug, append the --help clobber
incident to errors_found.md. Idempotent: re-running skips anything already done.
"""
import json
import pathlib

# 1. quarantine the 2 gemini-3.8-flash rows (superseded slug, 429-only history)
src = pathlib.Path("results/api_ladder_transcripts.jsonl")
rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
keep = [r for r in rows if r.get("model") != "google:gemini-3.8-flash"]
stale = [r for r in rows if r.get("model") == "google:gemini-3.8-flash"]
print(f"api_ladder rows: total={len(rows)} keep={len(keep)} stale={len(stale)}")
if stale:
    q = pathlib.Path("results/api_ladder_transcripts.stale-38flash.jsonl")
    with q.open("a", encoding="utf-8") as fh:
        for r in stale:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    src.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep),
        encoding="utf-8",
    )
    print(f"quarantined {len(stale)} rows -> {q}")

# 2. PREREG section 6 amendment: api ladder frontier model slug
p = pathlib.Path("PREREG.md")
txt = p.read_text(encoding="utf-8")
row = (
    "| 2026-10-31 | **Free-API ladder frontier model = `google:gemini-3.5-flash-lite`** "
    "(`jobs.api_ladder_cells`). The 2026-10-29 launch targeted `google:gemini-3.8-flash`, "
    "which returned HTTP 429 on every attempt (10 backoff tries per call, then "
    "\"unresponsive after 10 tries\") and completed no episode; its two transcript rows "
    "(both cell `defense=none|kind=semantic|pressure=low`, ep 0) are quarantined in "
    "`results/api_ladder_transcripts.stale-38flash.jsonl` and excluded from every "
    "analysis. The replacement slug was live-tested with one call before relaunch "
    "(0.9 s, 2026-10-31). Nothing in the ladder grid changed — cells, n=20 per cell, "
    "4 defenses x 2 kinds x 2 pressures, split=TEST — only the provider model id. |\n"
)
if "Free-API ladder frontier model" not in txt:
    p.write_text(txt.rstrip("\n") + "\n" + row, encoding="utf-8")
    print("PREREG §6 amendment appended")
else:
    print("PREREG §6 amendment already present")

# 3. errors_found.md incident note
p = pathlib.Path("errors_found.md")
txt = p.read_text(encoding="utf-8")
entry = """
## 2026-10-31 — `--help` truncated two detector result files (recovered)

`run_detectors.py` and `build_ensemble.py` do **not** use argparse: `sys.argv` is
read positionally, where the arguments are source-file paths. Probing them with
`--help` therefore made `run_detectors` treat "--help" as its only source (0 notes
found) and rewrite `results/detector_pool.jsonl` to 0 bytes; `build_ensemble` then
rewrote `results/detector_final.jsonl` to 0 bytes off the emptied pool.

Both files are tracked, and `git checkout --` restored them **byte-identical** to
their pre-incident content: 5,468,029 B / 5,795,304 B in the working tree (CRLF),
the same sizes they had before the incident (git stores LF at 5,463,349 B /
5,790,624 B; the 4,680-byte delta is exactly the 4,680 line endings). No analysis ran
against the emptied files — `results/numbers.json` was last written 2026-10-30 from
intact inputs and was not regenerated in between.

Lesson: never pass `--help` to scripts in this repo that read `sys.argv` positionally
(`run_detectors.py`, `build_ensemble.py`, and any other module without argparse);
read the module docstring for usage instead.
"""
if "2026-10-31 — `--help` truncated" not in txt:
    p.write_text(txt.rstrip("\n") + "\n" + entry, encoding="utf-8")
    print("errors_found.md incident appended")
else:
    print("errors_found.md incident already present")

print("done")
