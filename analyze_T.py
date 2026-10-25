"""Turn results_T.csv into T estimates with bootstrap 95% CIs."""
import pandas as pd, numpy as np
d = pd.read_csv(__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "results_T.csv", names=["model","defense","pressure","kind","hop","leaked"])
rng = np.random.default_rng(0)
def ci(x): b=[rng.choice(x,len(x)).mean() for _ in range(2000)]; return np.percentile(b,[2.5,97.5])
rows=[]
for k,g in d[d.hop==1].groupby(["model","defense","pressure","kind"]):
    x=g.leaked.values; lo,hi=ci(x); rows.append((*k, len(x), x.mean(), lo, hi))
print(pd.DataFrame(rows, columns=["model","defense","pressure","kind","n","T","lo","hi"]).to_string(index=False))
