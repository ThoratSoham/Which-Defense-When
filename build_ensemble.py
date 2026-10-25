"""Join D1/D2/D3 verdicts into the majority-vote ensemble.

  python build_ensemble.py

Reads results/detector_pool.jsonl + results/d3_<provider>.jsonl (any providers
present), writes results/detector_final.jsonl with verdicts = {d1, d2, d3} and
`ensemble` (>=2 of 3; None when fewer than 2 detectors voted).
"""
import glob, json, os
from detectors.ensemble import ensemble_vote


def main():
    pool = [json.loads(l) for l in open("results/detector_pool.jsonl", encoding="utf-8")]
    d3 = {}
    for path in sorted(glob.glob("results/d3_*.jsonl")):
        provider = os.path.basename(path)[4:-6]
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            # prefer an API judge over a local one if both exist for the note
            if r["pool_id"] not in d3 or provider.startswith(("google", "openrouter")):
                d3[r["pool_id"]] = {"leak": r.get("leak"), "provider": provider,
                                    "model": r.get("judge_model")}
    out = "results/detector_final.jsonl"
    n_d3 = n_ens = 0
    with open(out, "w", encoding="utf-8") as f:
        for r in pool:
            j = d3.get(r["pool_id"])
            verdicts = {"d1": r["verdicts"]["d1"], "d2": r["verdicts"]["d2"],
                        "d3": (j or {}).get("leak")}
            ens = ensemble_vote(verdicts)
            r["verdicts"] = verdicts
            r["d3"] = j
            r["ensemble"] = ens["ensemble"]
            r["ensemble_n_voted"] = ens["n_voted"]
            n_d3 += verdicts["d3"] is not None
            n_ens += ens["ensemble"] is not None
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {out}: {len(pool)} notes, {n_d3} with a D3 verdict, "
          f"{n_ens} with an ensemble verdict")


if __name__ == "__main__":
    main()
