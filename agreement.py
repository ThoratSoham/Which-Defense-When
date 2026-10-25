"""Compare YOUR labels with the automatic leak detector.  Run after labelling: python agreement.py"""
import pandas as pd
s, k = pd.read_csv("label_sheet.csv"), pd.read_csv("label_key.csv")
d = s.merge(k, on="id").dropna(subset=["human_leaked"]); d["human_leaked"] = d.human_leaked.astype(int)
def rep(x, name):
    tp = ((x.human_leaked == 1) & (x.auto_leaked == 1)).sum(); tn = ((x.human_leaked == 0) & (x.auto_leaked == 0)).sum()
    fp = ((x.human_leaked == 0) & (x.auto_leaked == 1)).sum(); fn = ((x.human_leaked == 1) & (x.auto_leaked == 0)).sum(); n = len(x)
    po = (tp + tn) / n; pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / n**2
    print(f"{name:22s} n={n:3d} agreement={po:.2f} kappa={(po - pe) / (1 - pe + 1e-9):.2f} precision={tp / max(tp + fp, 1):.2f} recall={tp / max(tp + fn, 1):.2f}  (FP={fp}, FN={fn})")
rep(d, "ALL")
for kind in ("verbatim", "semantic"): rep(d[d.kind == kind], kind)
for df in ("none", "gateway"): rep(d[d.defense == df], "defense=" + df)
