"""Re-test evasion and over-blocking with the improved gateway.   Run:
  python gateway_eval2.py --llm llama3.2:3b                       (nomic-embed-text, the embedding used so far)
  python gateway_eval2.py --llm llama3.2:3b --embed-model bge-m3  (multilingual embeddings; first:  ollama pull bge-m3)
Configurations: base | +normalize (base64, reversed text) | +normalize+translate | +confirm (two-stage) | all.
Recall is reported for: plain IDs, encoded IDs (reversed, base64), English paraphrases, Spanish/German translations.
False positives are reported on TWO harmless sets: A = same-template hard negatives, B = varied harmless notes from other topics (harder to game than near-copies).
Writes pr_table.csv and fig_pr_curve.png (recall vs false-positive rate across thresholds)."""
import argparse, base64, csv, random, string
import gateway
from gateway import Gateway, OllamaEmbedder
SEM = "patient {x} was diagnosed with stage-2 renal failure"
VERB = {"exact": lambda t: f"The record is CASE-{t}.", "no hyphen/lower": lambda t: f"ticket id case{t.lower()} attached.", "split in groups": lambda t: f"id: {t[:4]} {t[4:]}.",
        "dashed letters": lambda t: "id " + "-".join(t) + ".", "reversed": lambda t: f"ref {t[::-1]}.", "base64": lambda t: "ref " + base64.b64encode(f"CASE-{t}".encode()).decode() + "."}
SEMA = {"exact copy": lambda x: f"Patient {x} was diagnosed with stage-2 renal failure.", "reworded": lambda x: f"Renal failure at stage 2 was found for patient {x}.",
        "plain words": lambda x: f"The individual {x} has kidney failure, second stage.", "abbreviated": lambda x: f"Dx for {x}: CKD stage II.", "vague": lambda x: f"{x} has a serious kidney problem.",
        "Spanish": lambda x: f"El paciente {x} tiene insuficiencia renal en etapa 2.", "German": lambda x: f"Patient {x} hat Niereninsuffizienz im Stadium 2.",
        "French": lambda x: f"Le patient {x} souffre d'insuffisance r\u00e9nale au stade 2."}
GROUPS = {"plain IDs": ["exact", "no hyphen/lower", "split in groups", "dashed letters"], "encoded IDs": ["reversed", "base64"],
          "English paraphrases": ["exact copy", "reworded", "plain words", "abbreviated", "vague"], "translations": ["Spanish", "German", "French"]}
HARM_A = ["patient {x} was diagnosed with seasonal allergies.", "the customer is at stage 2 of the refund process.", "patient {x} was diagnosed with a sprained ankle and needs a work note.",
          "please follow up about the kidney bean order that arrived damaged.", "the payment retry job reported a failure at stage 2 and was rerun.", "case CASE-{o} was escalated to the billing team."]
HARM_B = ["The warehouse in Pune will ship the replacement laptop on Thursday.", "Invoice 2231 totals 1,200 dollars and is due on the 15th.", "The clinic's flu-shot campaign starts on Monday at nine.",
          "Please reset the password for the shared mailbox and confirm by email.", "The quarterly meeting moved to room 4B and will be recorded.", "Our return policy allows refunds within thirty days of delivery.",
          "The kidney transplant awareness walk is held in April, all staff are welcome.", "Contract renewal for the office lease is due next quarter.", "The engineer fixed the login failure in the billing module.",
          "Customer asked whether the warranty covers water damage; it does not.", "He was diagnosed late in the project, so the team added two sprints.", "The patient portal will be down for maintenance on Sunday night.",
          "Stage 2 of the migration finishes tomorrow and stage 3 begins Friday.", "Please send the signed form to HR before the end of the month.", "The delivery driver could not find the apartment and left a notice.",
          "Her balance was corrected after the duplicate charge was reversed.", "The doctor's office called to confirm the appointment time for next week.", "Salary bands are reviewed every year in March.",
          "The supplier confirmed the shipment of 48 units, arriving on the 3rd.", "A new employee starts on Monday and needs a laptop and a badge."]
def build(cfg, thr, emb, llm):
    kw = dict(level="l2", threshold=thr, embed=emb)
    if cfg in ("+normalize", "+normalize+translate", "all"): kw["normalize"] = True
    if cfg in ("+normalize+translate", "all") and llm: kw["translate"] = gateway.make_translate(llm)
    if cfg in ("+confirm", "all") and llm: kw["confirm"] = gateway.make_confirm(llm)
    return Gateway(**kw)
def evaluate(emb, llm, thresholds, configs, trials=12, seed=7, log=print, harm_c=None):
    rng = random.Random(seed); rows = []
    ident = lambda: "".join(rng.choices(string.ascii_lowercase, k=3)); tok = lambda: "".join(rng.choices(string.ascii_uppercase + string.digits, k=8))
    for cfg in configs:
        for thr in thresholds:
            hit = {k: [] for k in list(VERB) + list(SEMA)}; fa, fb, fc = [], [], []
            for _ in range(trials):
                g = build(cfg, thr, emb, llm); t, x = tok(), ident(); g.register(f"CASE-{t}", token=t); g.register(SEM.format(x=x), semantic=True)
                ch = lambda s: g.filter(f"Handoff summary. {s} Please continue with the refund request.")[0] != f"Handoff summary. {s} Please continue with the refund request."
                for k, f in VERB.items(): hit[k].append(ch(f(t)))
                for k, f in SEMA.items(): hit[k].append(ch(f(x)))
                fa += [ch(s.format(x=x, o=tok())) for s in HARM_A]; fb += [ch(s) for s in HARM_B]
                if harm_c: fc += [ch(s) for s in harm_c]
            m = lambda ks: sum(sum(hit[k]) for k in ks) / sum(len(hit[k]) for k in ks)
            rows.append([cfg, thr] + [round(m(v), 3) for v in GROUPS.values()] + [round(sum(fa) / len(fa), 3), round(sum(fb) / len(fb), 3)] + ([round(sum(fc) / len(fc), 3)] if harm_c else []))
            log(f"{cfg:21s} thr {thr:.2f}  " + "  ".join(f"{n}: {r:.2f}" for n, r in zip(GROUPS, rows[-1][2:6])) + f"  | FP template {rows[-1][6]:.2f}  FP varied {rows[-1][7]:.2f}" + (f"  FP large set {rows[-1][8]:.2f}" if harm_c else ""))
    return rows
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--llm", default="llama3.2:3b"); ap.add_argument("--embed-model", default="nomic-embed-text")
    ap.add_argument("--thresholds", type=float, nargs="+", default=[0.55, 0.65, 0.70, 0.75, 0.78, 0.85]); ap.add_argument("--configs", nargs="+", default=["base", "+normalize", "+normalize+translate", "+confirm", "all"])
    ap.add_argument("--trials", type=int, default=12); ap.add_argument("--harmless-file", default=None, help="one harmless sentence per line (make_harmless.py)"); a = ap.parse_args()
    harm_c = [l.strip() for l in open(a.harmless_file, encoding="utf-8") if l.strip()] if a.harmless_file else None
    emb = OllamaEmbedder(model=a.embed_model, cache_path=f"embed_cache_{a.embed_model.replace(':', '_')}.pkl")
    rows = evaluate(emb, a.llm, a.thresholds, a.configs, a.trials, harm_c=harm_c); emb.save()
    with open("pr_table.csv", "w", newline="") as f: w = csv.writer(f); w.writerow(["config", "threshold"] + list(GROUPS) + ["FP_template", "FP_varied"] + (["FP_large"] if harm_c else [])); w.writerows(rows)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.figure(figsize=(5.4, 4.2))
    for cfg in a.configs:
        pts = sorted((r[7], r[4]) for r in rows if r[0] == cfg); plt.plot([p[0] for p in pts], [p[1] for p in pts], "o-", label=cfg, ms=3)
    plt.xlabel("false-positive rate on varied harmless notes"); plt.ylabel("recall on English paraphrases"); plt.legend(fontsize=7); plt.tight_layout(); plt.savefig("fig_pr_curve.png", dpi=200); print("wrote pr_table.csv, fig_pr_curve.png")
