import os
import pandas as pd

print("looking in:", os.getcwd())
print("csv exists:", os.path.exists("results_T.csv"))

d = pd.read_csv("results_T.csv", names=["model","defense","pressure","kind","hop","leaked"])
c = d.groupby(["model","defense","pressure","kind"]).size().reset_index(name="rows")
c["episodes"] = c.rows // 2
c["complete"] = c.episodes >= 30
print(c.to_string(index=False))
print("\ncells complete:", c.complete.sum(), "of", 4 * d.model.nunique())