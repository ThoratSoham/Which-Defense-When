"""Run the independent detector stack over every logged note (no LLM generation).

  python run_detectors.py                     # defaults: chain + network transcripts
  python run_detectors.py results_v2_transcripts.jsonl

Writes results/detector_pool.jsonl, one record per note:
  {pool_id, src, model, defense, pressure, kind, topology, hop, episode, secret,
   note, verdicts: {d1, d2}, d2_p}

D3 (LLM judge) is NOT run here: it costs quota, so it is run only on the notes
that matter (label sample + disagreement set) via run_d3.py.
"""
import hashlib, json, os, sys

from detector import d1_content_leak, identifier_exposure
import detectors.d2_nli as d2

DEFAULT_INPUTS = ["results_v2_transcripts.jsonl", "network_results_transcripts.jsonl"]


def load_notes(paths):
    rows = []
    for p in paths:
        if not os.path.exists(p):
            print(f"  (skipping missing {p})")
            continue
        src = os.path.basename(p).replace("_transcripts.jsonl", "")
        for i, line in enumerate(open(p, encoding="utf-8")):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            note = r.get("sent") or r.get("raw") or ""
            secret = r.get("secret", "")
            kind = r.get("kind") or ("verbatim" if str(secret).startswith("CASE-") else "semantic")
            pool_id = hashlib.sha1(
                f"{src}|{r.get('model')}|{r.get('defense')}|{r.get('pressure')}|"
                f"{r.get('topology','')}|{r.get('episode')}|{r.get('hop', r.get('to',''))}|"
                f"{note[:200]}".encode()).hexdigest()[:16]
            rows.append({
                "pool_id": pool_id, "src": src, "row": i,
                "model": r.get("model"), "defense": r.get("defense"),
                "pressure": r.get("pressure"), "kind": kind,
                "topology": r.get("topology", "chain3"), "hop": r.get("hop"),
                "episode": r.get("episode"), "secret": secret, "note": note,
                "auto_leaked_original": r.get("auto_leaked"),
            })
    return rows


def main():
    inputs = sys.argv[1:] or DEFAULT_INPUTS
    out = "results/detector_pool.jsonl"
    os.makedirs("results", exist_ok=True)
    rows = load_notes(inputs)
    print(f"pool: {len(rows)} notes from {inputs}")

    # ---- D1 (legacy keyword/ID detector, continuity only)
    for r in rows:
        r["d1"] = int(d1_content_leak(r["note"], r["secret"], r["kind"]))
        r["d1_identifier"] = int(identifier_exposure(r["note"], r["secret"]))

    # ---- D2 (NLI entailment) in batches
    print("scoring D2 (NLI) ...")
    pairs = [(r["note"], r["secret"]) for r in rows]
    B = 64
    probs = []
    for i in range(0, len(pairs), B):
        probs += d2.score_pairs(pairs[i:i + B])
        print(f"  {min(i + B, len(pairs))}/{len(pairs)}")

    with open(out, "w", encoding="utf-8") as f:
        for r, p in zip(rows, probs):
            r["d2_p"] = round(float(p), 4)
            r["d2"] = int(p >= d2.THRESHOLD)
            r["verdicts"] = {"d1": r["d1"], "d2": r["d2"]}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {out}")

    from collections import Counter
    agree = Counter((r["d1"], r["d2"]) for r in rows)
    print("D1 x D2 confusion (d1,d2)->n:", dict(agree))
    dis = sum(n for (a, b), n in agree.items() if a != b)
    print(f"D1/D2 disagreements: {dis} ({dis / max(len(rows),1):.1%})")


if __name__ == "__main__":
    main()
