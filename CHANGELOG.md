# Changelog: Manuscript Revision (v1 -> v2)

**Title Transformation:**  
*Original:* "Origination, Relay and Persistent Blind Spots in Secret Leakage Between LLM Agents" (26 pages, single-study focus).  
*Revised:* "Which Defense, When? Origination, Relay and Blind Spots in Secret Leakage Between LLM Agents" (15 pages Elsevier manuscript + 3 pages Supplementary; 14 pages TMLR submission).

**Target Formats Produced:**
1. **Copy A (Elsevier):** `main_elsevier.tex` / `main_elsevier.pdf` (15 pages, 12pt preprint, single-column elsarticle) + `supplementary_elsevier.tex` / `supplementary_elsevier.pdf` (3 pages).
2. **Copy B (TMLR):** `main_tmlr.tex` / `main_tmlr.pdf` (14 pages total: 11 pages main text strictly $\le 12$ pages, 3 pages appendix, anonymized).

---

## 1. Summary of Structural Condensation & Redundancy Removal

The original manuscript was 26 pages long due to heavy duplication across Introduction, Results, Discussion, and Conclusion, verbose protocol descriptions, sprawling narrative tables, and redundant restatements of numerical metrics. We condensed the manuscript to 15 pages while preserving **100% of the 75 knowledge items** cataloged in `knowledge_ledger.csv`.

### A. Introduction & Related Work
- **Eliminated Early Repetitions:** In the original draft, numerical findings (e.g., $T = 0.346$, $T = 0.027$, $\Delta U$, 40-fold reductions) were repeated up to 4 times across the Abstract, Section 1.1, Section 1.3, Section 5, and Section 8. The revised draft states high-level qualitative takeaways in the Introduction and reserves exact numerical values for Section 5 (Results) and Table 5.
- **Related Work Table (Table 1):** Merged multiple paragraphs of related work prose into a structured taxonomy comparing threat model, topology, defense mechanism, and leakage metrics across existing literature (Ogundoyin & Ikram 2026; Chen et al. 2024; Mozes et al. 2023; Wu et al. 2024; Debenedetti et al. 2024).

### B. Core Reframing: "Which Defense, When?"
- **New Decision Map (Table 3):** Added a 4-regime decision framework mapping operating conditions (Schema-segregated records, Entangled free text, Resource-constrained local models, Multi-hop broadcast networks) directly to recommended defenses, empirical backing, and explicit caveats.
- **Core Claims & Evidence (Table 4):** Added a rigorous claims-and-evidence matrix linking all headline assertions (B4 dominance in schema, Gateway dominance in free text, Relay barrier, Outbreak floor) to pre-registered evidence, sample sizes, and counter-evidence.

### C. Tables & Figures Streamlining
- **Merged Defense Ladder (Table 5):** Unified disparate single-secret exploratory runs ($n=360$), pre-registered multi-secret TEST split ($n=96$), and API tier (`gemini-3.5-flash-lite`, $n=80$--$85$) into a single compact table with bootstrap 95% CIs and TOST 90% equivalence intervals.
- **Consolidated Baselines & Entangled Free Text (Table 6):** Combined the 6 baselines (B1 System Prompt, B2 Few-Shot In-Context, B3 Post-Hoc Critique, B4 Static ACL, B5 Output Filter, B6 Differential Privacy) across Part A (Schema-segregated records) and Part B (Entangled free-text emails) into one unified comparative table.
- **Figure Condensation:**
  - Figure 1 (`fig1_ladder_v2.pdf`): Consolidated multi-detector ladder comparing Ensemble and $D_1$.
  - Figure 2 (`fig2_pareto_v2.pdf`): Two-panel Pareto frontier highlighting the trade-off reversal between structured fields and unstructured text.
  - Figure 3 (`fig5-validation.png`): Combined 6-agent and 12-agent network validation.
  - Figure 4 (`fig3_outbreak_v2.pdf`): 500-agent epidemic simulation curves parameterized by 2B--3B empirical rates.

### D. Relocation to Supplementary Material / Appendices
- **12-Agent Broadcast Tree Detailed Calibration:** Full topology breakdown across Barabási--Albert, Watts--Strogatz, and Random trees (Tables S1/S2 in Elsevier Supplementary, Tables 7/8 in TMLR Appendix A).
- **500-Agent Full Herd Immunity Grid:** Complete critical fraction $p_c$ table across Erdős--Rényi, Barabási--Albert, and Watts--Strogatz topologies at 100% coverage (Table S3 in Elsevier Supplementary, Table 9 in TMLR Appendix B).
- **Exploratory Probes & Threshold Sweeps:** 12-secret embedding cosine threshold calibration curves, base64/rot13 encoding robustness, and adversarial compliance checks (Section S3 in Elsevier Supplementary, Appendix C in TMLR).
- **Complete Knowledge Ledger Audit:** Explicit traceability mapping linking KL-001 through KL-075 directly to section and table locations (Table S4 in Elsevier Supplementary, Appendix D in TMLR).

---

## 2. Integrity and Scientific Corrections

1. **Static ACL (B4) Nuance Clarified:**
   - Corrected previous contradictory phrasing: B4 strictly dominates in schema-segregated tasks ($T=0.000, U=0.828$), but catastrophic failure occurs in entangled free text where stripping the field drops usefulness to $U=0.000$. The Gateway maintains $U=0.750$ and $T=0.042$ in entangled settings.
2. **Updated Outbreak Floor Projections:**
   - 500-agent epidemic simulations were updated from the obsolete exploratory parameter ($T=0.017$) to the pre-registered 2B--3B TEST measurements ($T=0.073$, $T=0.027$ via gateway, and $D_1=0.490$). Projections explicitly reflect the realistic 20%--34% outbreak floor for 2B--3B models and 6%--14% for API models.
3. **Detector Transparency:**
   - Highlighted that headline detector ensemble ($\kappa=0.51$, recall 0.63) undercounts leaks relative to $D_1$ ($\kappa=0.71$, recall 0.98). Both Ensemble and $D_1$ numbers are reported side-by-side across all tables.
   - Accurately reported single-annotator status, Gemini judge adjudication, and fallback to local rotating judges on 213/327 ties.
4. **Vocabulary & Neutrality:**
   - Strictly referred to `gemini-3.5-flash-lite` as "an API model", never "frontier".
   - Preserved all required labels: "exploratory", "post hoc, $n=24$", and "suggestive/inconclusive" (12-agent validation).

---

## 3. Knowledge Ledger Verification

Every item from `knowledge_ledger.csv` (KL-001 through KL-075) was verified automatically via `verify_ledger.py` and confirmed present in both:
- **Copy A:** `main_elsevier.tex` + `supplementary_elsevier.tex` (100% / 75 items).
- **Copy B:** `main_tmlr.tex` (100% / 75 items).

Zero result numbers are hardcoded: all metrics are systematically generated via `macros.tex` from `results/numbers_v2.json`, strictly enforced by `check_numbers.py`.

