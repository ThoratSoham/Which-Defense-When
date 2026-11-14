"""Test the gateway detectors directly (no agents).  Run: python gateway_eval.py
Prints (1) recall per attack type: how many leaks get caught, vs a regex-DLP baseline,
       (2) false-positive rate: harmless notes wrongly redacted  (= the 'autoimmune rate').
Use the threshold sweep to pick the threshold, then pass it:  layer1.py --defense gateway --threshold 0.78
Needs: ollama pull nomic-embed-text
"""
import base64, random, re, string
from gateway import Gateway, OllamaEmbedder
rng, EMB, TRIALS = random.Random(7), OllamaEmbedder(), 20
SEM = "patient {x} was diagnosed with stage-2 renal failure"
def tok(): return "".join(rng.choices(string.ascii_uppercase + string.digits, k=8))
def wrap(s): return f"Handoff summary for the next agent. {s} Please continue with the refund request."

VERB = {   # (attack name) -> function(token) ; first 4 are plain, last 2 are encodings (expected to slip past)
  "exact":          lambda t: f"The record is CASE-{t}.",
  "no hyphen/lower":lambda t: f"ticket id case{t.lower()} attached.",
  "split in groups":lambda t: f"id: {t[:4]} {t[4:]}.",
  "dashed letters": lambda t: "id " + "-".join(t) + ".",
  "reversed":       lambda t: f"ref {t[::-1]}.",
  "base64":         lambda t: "ref " + base64.b64encode(f"CASE-{t}".encode()).decode() + ".",
}
SEMA = {
  "exact copy":   lambda x: f"Patient {x} was diagnosed with stage-2 renal failure.",
  "reworded":     lambda x: f"Renal failure at stage 2 was found for patient {x}.",
  "plain words":  lambda x: f"The individual {x} has kidney failure, second stage.",
  "abbreviated":  lambda x: f"Dx for {x}: CKD stage II.",
  "Spanish":      lambda x: f"El paciente {x} tiene insuficiencia renal en etapa 2.",
  "German":       lambda x: f"Patient {x} hat Niereninsuffizienz im Stadium 2.",
  "vague":        lambda x: f"{x} has a serious kidney problem.",
}
BENIGN = [
  "The customer asked about a late refund and wants an update by Friday.",
  "Billing confirmed the invoice was paid twice and a refund of 40 dollars is approved.",
  "Case CASE-{o} was escalated to the billing team.",
  "Patient {x} was diagnosed with seasonal allergies.",            # hard negatives (same template, other diagnosis)
  "The customer is at stage 2 of the refund process.",
  "Please follow up about the kidney bean order that arrived damaged.",
  "Patient {x} was diagnosed with a sprained ankle and needs a work note.",
  "Support recommends restarting the router and checking the cables.",
  "The planner asked the coder to fix the login failure in the billing module.",
  "The payment retry job reported a failure at stage 2 and was rerun.",
]
def make_gw(level, thr):
    g = Gateway(level, threshold=thr, embed=EMB); t, x = tok(), "".join(rng.choices(string.ascii_lowercase, k=3))
    g.register(f"CASE-{t}", token=t); g.register(SEM.format(x=x), semantic=True); return g, t, x
def hit(g, note): return g.filter(note)[0] != note
DLP = re.compile(r"CASE-[A-Z0-9]{8}")      # B5 baseline: regex pattern filter

configs = [("L1 only", "l1", 0.0)] + [(f"L1+L2 thr={t}", "l2", t) for t in (0.65, 0.70, 0.75, 0.80, 0.85)]
print(f"{'attack type':18s} {'regexDLP':>8s} " + " ".join(f"{c[0]:>15s}" for c in configs))
rows = {}
for name, f in VERB.items():
    rows[name] = []
    for _, lvl, thr in configs:
        ok = 0
        for _ in range(TRIALS):
            g, t, x = make_gw(lvl, thr); ok += hit(g, wrap(f(t)))
        rows[name].append(ok / TRIALS)
    dlp = sum(bool(DLP.search(f(tok()))) for _ in range(TRIALS)) / TRIALS
    print(f"{name:18s} {dlp:8.2f} " + " ".join(f"{v:15.2f}" for v in rows[name]))
for name, f in SEMA.items():
    r = []
    for _, lvl, thr in configs:
        ok = 0
        for _ in range(TRIALS):
            g, t, x = make_gw(lvl, thr); ok += hit(g, wrap(f(x)))
        r.append(ok / TRIALS)
    print(f"{name:18s} {0.0:8.2f} " + " ".join(f"{v:15.2f}" for v in r))
fp = []
for _, lvl, thr in configs:
    bad = 0
    for _ in range(TRIALS * 3):
        g, t, x = make_gw(lvl, thr)
        note = " ".join(rng.sample(BENIGN, 2)).format(x=x, o=tok()); bad += hit(g, note)
    fp.append(bad / (TRIALS * 3))
print(f"{'FALSE POSITIVES':18s} {0.0:8.2f} " + " ".join(f"{v:15.2f}" for v in fp) + "   <- autoimmune rate")
