"""Paper figures from your existing result files.   Run: python make_figures.py
fig1_ladder.png        leak rate T per defense (95% bootstrap CI), pooled and by secret type      <- results_v2r.csv
fig2_threshold.png     gateway recall vs false positives across thresholds, 12 secrets             <- diversity_results.csv
fig3_validation.png    real vs simulated attack size on six-agent networks (one-T vs two-parameter) <- network_results_transcripts.jsonl + results_v2r.csv
Herd-immunity curves and the cost plot already exist: fig_partial_protection.png (sim_protect.py), fig_pareto.png (pareto.py)."""
import os, sys, json, collections, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
rng = np.random.default_rng(0); ORDER = ["none", "warning", "gateway_l1", "gateway"]
LAB = {"none": "no defense", "warning": "prompt warning", "gateway_l1": "L1 exact match", "gateway": "L1+L2 gateway"}
def ci(x, n=3000): b = [rng.choice(x, len(x)).mean() for _ in range(n)]; return np.percentile(b, [2.5, 97.5])
# ---- fig 1
if os.path.exists("results_v2r.csv"):
    d = pd.read_csv("results_v2r.csv", names=["model","defense","pressure","kind","hop","leaked"]); d = d[(d.hop == 1) & (d.model != "qwen2.5:7b")]
    fig, ax = plt.subplots(1, 4, figsize=(13.5, 3.6), sharey=True)
    # Panel 0: Confirmatory TEST (3-detector ensemble, n=192/def) if results/numbers.json exists
    if os.path.exists("results/numbers.json"):
        nj = json.load(open("results/numbers.json", encoding="utf-8"))
        ens = nj.get("ladder", {}).get("t_by_detector", {}).get("ensemble", {})
        for i, o in enumerate(ORDER):
            cell = ens.get(o, {})
            m = cell.get("T", 0.0)
            lo, hi = cell.get("cluster_ci", [m, m])
            ax[0].bar(i, m, yerr=[[max(0, m - lo)], [max(0, hi - m)]], capsize=3, color="#2b5c8f" if o != "gateway" else "#2ca02c")
            ax[0].text(i, hi + 0.02, f"{m:.3f}", ha="center", fontsize=8)
        ax[0].set_xticks(range(len(ORDER))); ax[0].set_xticklabels([LAB[o] for o in ORDER], rotation=25, ha="right", fontsize=8)
        ax[0].set_title("TEST ensemble (n=192/def)", fontsize=9.5, fontweight="bold")
    for a, (title, sub) in zip(ax[1:], [("Exploratory: all (n=360)", d), ("Exploratory: verbatim ID", d[d.kind == "verbatim"]), ("Exploratory: semantic", d[d.kind == "semantic"])]):
        for i, o in enumerate([x for x in ORDER if x in set(d.defense)]):
            x = sub[sub.defense == o].leaked.values; lo, hi = ci(x); a.bar(i, x.mean(), yerr=[[x.mean() - lo], [hi - x.mean()]], capsize=3, color="#4c72b0" if o != "gateway" else "#55a868")
            a.text(i, hi + 0.02, f"{x.mean():.2f}", ha="center", fontsize=8)
        a.set_xticks(range(len(ORDER))); a.set_xticklabels([LAB[o] for o in ORDER], rotation=25, ha="right", fontsize=8); a.set_title(title, fontsize=9.5)
    for a in ax: a.set_ylim(0, 0.95)          # headroom so value labels are not clipped
    ax[0].set_ylabel("per-hop leak rate T (95% CI)"); plt.tight_layout(); plt.savefig("fig1_ladder.png", dpi=220); plt.close(); print("wrote fig1_ladder.png")
# ---- fig 2
DIV = sys.argv[1] if len(sys.argv) > 1 else "diversity_results.csv"       # e.g. python make_figures.py diversity_results_min1.csv
if os.path.exists(DIV):
    r = pd.read_csv(DIV); r = r[r.threshold < 5]
    rec = r[r.kind == "paraphrase"].groupby("threshold").flagged.mean(); sp = r[r.kind == "spanish"].groupby("threshold").flagged.mean(); fp = r[r.kind == "harmless"].groupby("threshold").flagged.mean()
    plt.figure(figsize=(5.5, 3.6)); plt.plot(rec.index, rec.values, "o-", label="paraphrase recall"); plt.plot(sp.index, sp.values, "s--", label="Spanish recall"); plt.plot(fp.index, fp.values, "^-", label="false positives (hard negatives)")
    plt.axvline(0.78, color="gray", ls=":", lw=1); plt.text(0.781, 0.5, "deployed", fontsize=7, rotation=90); plt.xlabel("similarity threshold"); plt.ylabel("rate"); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig("fig2_threshold.png", dpi=220); plt.close(); print("wrote fig2_threshold.png")
# ---- fig 3
F = "network_results_transcripts.jsonl"
if os.path.exists(F) and os.path.exists("results_v2r.csv"):
    from network_run import TOPO
    rows = [json.loads(l) for l in open(F, encoding="utf-8")]; eps = collections.defaultdict(list)
    for x in rows: eps[(x["model"], x["defense"], x["pressure"], x["kind"], x["topology"], x["episode"])].append(x)
    st = collections.defaultdict(lambda: {"src": [], "down": [], "size": []})
    for k, notes in eps.items():
        inc = {n["to"]: n["auto_leaked"] for n in notes}; c = k[:5]; st[c]["size"].append(sum(inc.values()))
        for n in notes:
            if n["from"] == 0: st[c]["src"].append(n["auto_leaked"])
            elif inc.get(n["from"]) == 1: st[c]["down"].append(n["auto_leaked"])
    def sim(topo, ts, td, runs=3000):
        o = []
        for _ in range(runs):
            inf = {0}
            for a in sorted(TOPO[topo]):
                for c in TOPO[topo][a]:
                    if a in inf and rng.random() < (ts if a == 0 else td): inf.add(c)
            o.append(len(inf) - 1)
        return np.mean(o)
    T1 = d.groupby(["model", "defense", "pressure", "kind"]).leaked.mean(); pts1, pts2 = [], []
    for c, v in st.items():
        m, df, p, k, t = c; real = np.mean(v["size"])
        if (m, df, p, k) in T1.index: pts1.append((real, sim(t, T1[(m, df, p, k)], T1[(m, df, p, k)])))
        if t == "star6" and (m, df, p, k, "chain6") in st and st[(m, df, p, k, "chain6")]["down"]:
            ch = st[(m, df, p, k, "chain6")]; pts2.append((real, sim("star6", np.mean(ch["src"]), np.mean(ch["down"]))))
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    ax = axes[0]
    ax.plot([0, 5], [0, 5], "k:", lw=1)
    if pts1: a = np.array(pts1); ax.scatter(a[:, 0], a[:, 1], c="#c44e52", label=f"one T per edge (MAE {np.mean(abs(a[:,0]-a[:,1])):.2f})")
    if pts2: b = np.array(pts2); ax.scatter(b[:, 0], b[:, 1], c="#4c72b0", marker="s", label=f"two-param, chain->star (MAE {np.mean(abs(b[:,0]-b[:,1])):.2f})")
    ax.set_xlabel("real mean agents infected (6-agent)"); ax.set_ylabel("simulated"); ax.set_title("6-agent chains & stars (24 cells)", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="upper left")
    ax2 = axes[1]
    ax2.plot([0, 8], [0, 8], "k:", lw=1)
    if os.path.exists("results/numbers.json"):
        nj = json.load(open("results/numbers.json", encoding="utf-8"))
        cells = nj.get("network", {}).get("calibration", {}).get("ensemble", {}).get("cells", {})
        for key, cv in cells.items():
            rm = cv["real_mean"]; lo, hi = cv["real_ci"]; pr = cv["pred_o_r"]
            col = "#c44e52" if "none" in key else "#2ca02c"
            ax2.errorbar(rm, pr, xerr=[[max(0, rm - lo)], [max(0, hi - rm)]], fmt="o", color=col, capsize=3)
            ax2.text(rm + 0.12, pr + 0.08, key, fontsize=7)
    ax2.set_xlabel("real mean infected (12-agent, 95% CI)"); ax2.set_ylabel("predicted from 3-agent chains")
    ax2.set_title("12-agent held-out (6/6 CI covered, MAE 0.48)", fontsize=9.5, fontweight="bold")
    ax2.set_xlim(0.5, 8.2); ax2.set_ylim(0.5, 6.0)
    plt.tight_layout(); plt.savefig("fig3_validation.png", dpi=220); plt.close(); print("wrote fig3_validation.png")
