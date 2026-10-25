"""Run D3 (LLM judge) on the notes that matter: the labelling sample plus every
D1/D2 disagreement. D3 costs quota, so it is NOT run over the whole pool.

  python run_d3.py --provider google            # API judge (free tier)
  python run_d3.py --provider local             # cross-family local judge
  python run_d3.py --provider openrouter

Judge selection: a different family than the note's author (config
models.judge_rotation) for `local`; API judges are a fixed third family.

Writes results/d3_<provider>.jsonl: {pool_id, note_id, leak, ...}. The ensemble
is then assembled by build_ensemble.py.
"""
import argparse, hashlib, json, os, sys

from llm_client import LLMClient, QuotaExhausted, load_config
from detectors.d3_judge import judge_batch, pick_judge

API_MODEL = {"google": "google:gemini-2.5-flash",
             "openrouter": "openrouter:meta-llama/llama-3.3-70b-instruct:free"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="google",
                    choices=["google", "openrouter", "local"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-disagreements", type=int, default=300,
                    help="cap on extra D1/D2-disagreement notes judged beyond the sample")
    ap.add_argument("--include-disagreements", action="store_true", default=True)
    ap.add_argument("--all", action="store_true",
                    help="judge the ENTIRE pool (full ensemble coverage for T), "
                         "not just the labelling sample and disagreements")
    a = ap.parse_args()

    pool = {r["pool_id"]: r for r in
            (json.loads(l) for l in open("results/detector_pool.jsonl", encoding="utf-8"))}
    sample_ids = set()
    if os.path.exists("results/label_sample_key.csv"):
        import csv
        sample_ids = {r["pool_id"] for r in
                      csv.DictReader(open("results/label_sample_key.csv", encoding="utf-8"))}
    targets = ([pool[i] for i in sorted(pool)] if a.all
               else [pool[i] for i in sample_ids if i in pool])
    if a.all:
        a.include_disagreements = False      # already covered by --all
    if a.include_disagreements:
        seen = {t["pool_id"] for t in targets}
        extra = [r for r in pool.values()
                 if r["pool_id"] not in seen
                 and r["verdicts"]["d1"] != r["verdicts"]["d2"]]
        extra.sort(key=lambda r: r["pool_id"])       # deterministic selection
        targets += extra[:a.max_disagreements]
    if a.limit:
        targets = targets[:a.limit]
    cfg = load_config()
    client = LLMClient(config_path="config.yaml")
    out_path = f"results/d3_{a.provider}.jsonl"
    done, failed = set(), 0
    if os.path.exists(out_path):
        # only genuinely answered rows count as done; error rows are retried
        keep = []
        for l in open(out_path, encoding="utf-8"):
            r = json.loads(l)
            if r.get("leak") in (0, 1):
                done.add(r["pool_id"]); keep.append(l)
            elif "error" in r:
                failed += 1
        if keep:
            with open(out_path, "w", encoding="utf-8") as f:
                f.writelines(keep)
    targets = [t for t in targets if t["pool_id"] not in done]
    if a.provider == "local":
        # batch by judge model: Ollama keeps one model resident at a time
        # (OLLAMA_MAX_LOADED_MODELS=1), so swapping per note would reload constantly.
        targets.sort(key=lambda t: pick_judge(t["model"], cfg))
    print(f"D3 ({a.provider}): {len(targets)} to judge "
          f"({len(done)} already done, {failed} previous errors retried)")

    with open(out_path, "a", encoding="utf-8") as f:
        for i, t in enumerate(targets, 1):
            if a.provider == "local":
                model = pick_judge(t["model"], cfg)
            else:
                model = API_MODEL[a.provider]
            try:
                res = judge_batch([t["note"]], [t["secret"]], model, client,
                                  note_ids=[t["pool_id"]], log=lambda *x: None)[0]
            except QuotaExhausted as e:
                print(f"  quota exhausted, stopping cleanly: {e}")
                break
            except Exception as e:
                print(f"  error {t['pool_id']}: {type(e).__name__}: {str(e)[:120]}")
                continue
            f.write(json.dumps({"pool_id": t["pool_id"], "provider": a.provider,
                                "judge_model": model, **res},
                               ensure_ascii=False) + "\n")
            f.flush()
            if i % 25 == 0:
                print(f"  {i}/{len(targets)}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
