import pandas as pd
d = pd.read_csv(__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "results_T.csv", names=["model","defense","pressure","kind","hop","leaked"])
d = d[(d.hop == 1) & (d.model != "qwen2.5:7b")]
t = d.groupby(["model","pressure","kind","defense"]).leaked.mean().unstack()
t = t[[c for c in ["none","warning","gateway_l1","gateway"] if c in t.columns]]
print(t.round(2).to_string()); print("\nmean T per defense:\n", t.mean().round(3).to_string())
