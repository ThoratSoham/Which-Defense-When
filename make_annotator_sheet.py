"""Make a blank sheet for a SECOND annotator from the sheet you already labelled.
Run:  python make_annotator_sheet.py label_sheet_22.csv        (your labelled sheet; it is shuffled, so the first 50 rows are a random subset)
Writes annotator2_sheet.csv with your labels removed. Do NOT send them label_sheet_22.csv itself."""
import sys, pandas as pd
src = sys.argv[1] if len(sys.argv) > 1 else "label_sheet_22.csv"; n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
d = pd.read_csv(src).head(n); d["human_leaked"] = ""
d.to_csv("annotator2_sheet.csv", index=False)
print(f"wrote annotator2_sheet.csv ({len(d)} notes, no labels). Send it with the written definition, not your labels.")
