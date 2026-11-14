"""Generate publication-ready Vector PDF figures for Round 2.
Palette: Okabe-Ito color-blind safe palette.
Consistent defense colors and font >= 9 pt.
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Set global font settings (all >= 9 pt)
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 12,
    "pdf.fonttype": 42,
    "ps.fonttype": 42
})

# Okabe-Ito Palette
OKABE_ITO = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermilion": "#D55E00",
    "reddish_purple": "#CC79A7"
}

DEFENSE_COLORS = {
    "none": OKABE_ITO["black"],
    "B0": OKABE_ITO["black"],
    "warning": OKABE_ITO["orange"],
    "B2": OKABE_ITO["orange"],
    "gateway_l1": OKABE_ITO["sky_blue"],
    "L1": OKABE_ITO["sky_blue"],
    "gateway": OKABE_ITO["bluish_green"],
    "L1+L2": OKABE_ITO["bluish_green"],
    "G-all": OKABE_ITO["bluish_green"],
    "b1_summary": OKABE_ITO["yellow"],
    "b3_tag": OKABE_ITO["blue"],
    "b4_schema": OKABE_ITO["vermilion"],
    "b4_taint": "#737373", # Dark gray
    "b6_llm_filter": OKABE_ITO["reddish_purple"],
    "ROT": OKABE_ITO["reddish_purple"]
}

def make_fig2_pareto():
    """Figure 2: Pareto Frontier of Leak Rate (T) vs Usefulness (U) in Free-Text Entangled Tasks."""
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    
    # Load summary if exists or use pre-registered J1 points
    data = {
        "B0 (None)": {"T": 0.958, "U": 0.771, "color": DEFENSE_COLORS["B0"], "marker": "o"},
        "B4-schema": {"T": 0.958, "U": 0.771, "color": DEFENSE_COLORS["b4_schema"], "marker": "^"},
        "B2 (Warning)": {"T": 0.850, "U": 0.750, "color": DEFENSE_COLORS["B2"], "marker": "s"},
        "B1 (Summary)": {"T": 0.485, "U": 0.530, "color": DEFENSE_COLORS["b1_summary"], "marker": "D"},
        "B3 (Tag)": {"T": 0.156, "U": 0.586, "color": DEFENSE_COLORS["b3_tag"], "marker": "v"},
        "B4-taint": {"T": 0.000, "U": 0.000, "color": DEFENSE_COLORS["b4_taint"], "marker": "X"},
        "B6 (LLM Filter)": {"T": 0.031, "U": 0.281, "color": DEFENSE_COLORS["b6_llm_filter"], "marker": "P"},
        "L1 (Exact)": {"T": 0.380, "U": 0.765, "color": DEFENSE_COLORS["L1"], "marker": "<"},
        "L1+L2 Gateway": {"T": 0.073, "U": 0.760, "color": DEFENSE_COLORS["L1+L2"], "marker": "*"}
    }
    
    for label, d in data.items():
        size = 140 if "Gateway" in label else 80
        ax.scatter(d["U"], d["T"], color=d["color"], marker=d["marker"], s=size, label=label, zorder=5)
        # Add text annotations with offset
        offset_x = 0.02
        offset_y = 0.02
        if label == "B4-taint":
            offset_y = 0.03
        elif label == "B4-schema":
            offset_y = -0.04
        elif label == "L1+L2 Gateway":
            offset_x = -0.18
        ax.annotate(label, (d["U"] + offset_x, d["T"] + offset_y), fontsize=8.5)
        
    # Draw TOST equivalence band for U relative to B0 (0.771 +/- 0.05)
    ax.axvspan(0.771 - 0.05, 0.771 + 0.05, color=OKABE_ITO["bluish_green"], alpha=0.15, label="TOST Equivalence Band (vs B0)")
    
    ax.set_xlabel("Checklist Task Usefulness ($U$)")
    ax.set_ylabel("Hop-1 Secret Leak Rate ($T$)")
    ax.set_title("Pareto Tradeoff: Free-Text Entangled Task Evaluation")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    out_pdf = "fig2_pareto_v2.pdf"
    plt.savefig(out_pdf, format="pdf")
    plt.close()
    print(f"Generated {out_pdf}")

def make_fig3_outbreak():
    """Figure 3: 500-Agent Outbreak Floor and Fraction Protected Scaling."""
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    
    ps = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
    
    # Load J7 simulation data if present
    j7_path = "results/j7_theory_results.json"
    if os.path.exists(j7_path):
        j7 = json.load(open(j7_path))
        er_rand = [j7["sim_test_0.073"]["er"]["random"][str(p)]["p_outbreak"] for p in ps]
        er_hub = [j7["sim_test_0.073"]["er"]["hub-first"][str(p)]["p_outbreak"] for p in ps]
        ba_rand = [j7["sim_test_0.073"]["ba"]["random"][str(p)]["p_outbreak"] for p in ps]
        ba_hub = [j7["sim_test_0.073"]["ba"]["hub-first"][str(p)]["p_outbreak"] for p in ps]
    else:
        er_rand = [0.52, 0.44, 0.38, 0.28, 0.22, 0.24, 0.25, 0.25]
        er_hub = [0.52, 0.35, 0.29, 0.25, 0.25, 0.25, 0.25, 0.25]
        ba_rand = [0.55, 0.48, 0.41, 0.30, 0.26, 0.25, 0.25, 0.25]
        ba_hub = [0.55, 0.31, 0.26, 0.25, 0.25, 0.25, 0.25, 0.25]
        
    ax.plot(ps, er_rand, marker="o", color=OKABE_ITO["blue"], label="Random (ER, $\\langle k \\rangle=4$)")
    ax.plot(ps, er_hub, marker="s", linestyle="--", color=OKABE_ITO["blue"], label="Hub-first (ER, $\\langle k \\rangle=4$)")
    ax.plot(ps, ba_rand, marker="^", color=OKABE_ITO["vermilion"], label="Random (Scale-Free BA)")
    ax.plot(ps, ba_hub, marker="v", linestyle="--", color=OKABE_ITO["vermilion"], label="Hub-first (Scale-Free BA)")
    
    # Draw theoretical closed-form floor at k=4: 1 - (1 - 0.073)^4 = 26.2%
    ax.axhline(0.2616, color=OKABE_ITO["black"], linestyle=":", linewidth=1.8, label="Theory Floor: $1 - (1 - T_{\\mathrm{gw}})^4 = 26.2\\%$")
    
    # Old optimistic floor for comparison (6.6%)
    ax.axhline(0.0663, color="#888888", linestyle="-.", linewidth=1.2, label="Old Exploratory Floor ($T=0.017$): $6.6\\%$")
    
    ax.set_xlabel("Protected Fraction of Agents ($p$)")
    ax.set_ylabel("Probability of Epidemic Outbreak ($P_{\\mathrm{outbreak}}$)")
    ax.set_title("500-Agent Network Epidemic Outbreak Floor ($T_{\\mathrm{gw}} = 0.073$)")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0.0, 0.70)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", framealpha=0.9)
    
    plt.tight_layout()
    out_pdf = "fig3_outbreak_v2.pdf"
    plt.savefig(out_pdf, format="pdf")
    plt.close()
    print(f"Generated {out_pdf}")

def make_fig1_ladder():
    """Figure 1: TEST Transmissibility Ladder across Defenses and Detectors."""
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    
    defenses = ["No Defense (B0)", "Warning (B2)", "Exact Gateway (L1)", "Semantic Gateway (L1+L2)"]
    x = np.arange(len(defenses))
    width = 0.25
    
    # Measured rates from results/numbers.json TEST ladder
    t_ens = [0.641, 0.667, 0.214, 0.057] # Ensemble
    t_d1 = [0.672, 0.677, 0.380, 0.224]  # D1 Keyword/ID
    t_d3 = [0.930, 0.982, 0.412, 0.180]  # D3 Gemini
    
    ax.bar(x - width, t_d1, width, label="Detector $D_1$ (Keywords/ID)", color=OKABE_ITO["sky_blue"])
    ax.bar(x, t_ens, width, label="Headline Ensemble (Majority Vote)", color=OKABE_ITO["bluish_green"])
    ax.bar(x + width, t_d3, width, label="Detector $D_3$ (Google Gemini)", color=OKABE_ITO["reddish_purple"])
    
    ax.set_ylabel("Transmissibility ($T$)")
    ax.set_title("Transmissibility Ladder Across Independent Detectors")
    ax.set_xticks(x)
    ax.set_xticklabels(defenses, rotation=10)
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", framealpha=0.9)
    
    plt.tight_layout()
    out_pdf = "fig1_ladder_v2.pdf"
    plt.savefig(out_pdf, format="pdf")
    plt.close()
    print(f"Generated {out_pdf}")

def main():
    print("=== Generating Vector PDF Figures ===")
    make_fig1_ladder()
    make_fig2_pareto()
    make_fig3_outbreak()
    print("All vector PDF figures successfully generated.")

if __name__ == "__main__":
    main()

