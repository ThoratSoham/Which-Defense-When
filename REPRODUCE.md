# REPRODUCE.md
## Exact Commands to Reproduce Analyses, Figures, Tables, and PDFs

Execute all commands from the repository root on branch `v2-revision` inside `.venv` (or `.venv-1`).

```powershell
# Activate virtual environment (Windows PowerShell)
.venv\Scripts\activate
```

---

### 1. Freeze & Split Integrity Checks

* **Pre-registration & frozen parameters:** documented in `PREREG.md` (§5–§6) and locked in `results/freeze.ok`.
* **Verify split integrity and freeze marker:**
  ```powershell
  python -c "import os, json; assert os.path.exists('results/freeze.ok'); s=json.load(open('corpus/splits.json')); print('DEV semantic/id:', len(s['semantic']['dev']), len(s['identifier']['dev']), 'TEST semantic/id:', len(s['semantic']['test']), len(s['identifier']['test']))"
  ```

---

### 2. Primary Confirmatory Pipeline & Round 2 Theory Simulations

| Artifact / Stage | Command | Key Outputs |
| :--- | :--- | :--- |
| Primary & detector pipeline (Phases 1–6) | `python pipeline.py` | `results/detector_final.jsonl`, `results/agreement.json`, `results/t_by_detector.json` |
| 12-agent broadcast-tree & partial protection | `python network_experiment.py` & `python network_calibrate.py` | `results/network_calibration.json`, `results/partial_protect.json` |
| Primary compiled statistics | `python paper_numbers.py` | `results/numbers.json` |
| **J7** Closed-form outbreak floor & 500-agent TEST sims | `python run_j7_theory.py` | `results/j7_theory_results.json` |
| Master Round 2 JSON compilation | `python compile_numbers_v2.py` | `results/numbers_v2.json` |
| LaTeX macro & number audit generation | `python make_macros.py` | `macros.tex` |

> **Status of queued `PREREG_v2.md` extensions (see `INCOMPLETE.md`):** Only **J7** (`run_j7_theory.py`) is completed and incorporated into the manuscript tables/figures; **J1** (`run_j1_freetext.py`) has an unintegrated interim transcript (`results/j1_freetext_transcripts.jsonl`, 490 rows), and **J2** (`run_j2_chain.py`), **J3** (`run_j3_annotation.py`), **J5** (`run_j5_taxonomy.py`), **J8** (`run_j8_profiling.py`), and **J9** (`run_j9_rubric_usefulness.py`) have not yet been executed.

---

### 3. Figures

| Figure | Command | Output Files |
| :--- | :--- | :--- |
| Hop-1 ladder, Pareto `(a)/(b)`, validation, threshold sweep | `python make_paper_figures.py` | `fig1-ladder.png`, `fig2-pareto.png`, `fig5-validation.png`, `fig6-other-secrets.png` |
| 500-agent TEST outbreak floor (`Fig. 3 / 4`) | `python make_paper_figures_v2.py` | `fig3_outbreak_v2.pdf` (also `fig1_ladder_v2.pdf`, `fig2_pareto_v2.pdf`) |

---

### 4. Manuscript Verification & LaTeX Compilation

```powershell
# Verify all numeric results come from macros and all 75 ledger items appear in both copies
python check_numbers.py
python verify_ledger.py

# Compile TMLR manuscript (double-blind)
pdflatex -interaction=nonstopmode main_tmlr.tex
bibtex main_tmlr
pdflatex -interaction=nonstopmode main_tmlr.tex
pdflatex -interaction=nonstopmode main_tmlr.tex

# Compile Elsevier manuscript and supplement
pdflatex -interaction=nonstopmode main_elsevier.tex
pdflatex -interaction=nonstopmode main_elsevier.tex
pdflatex -interaction=nonstopmode supplementary_elsevier.tex
pdflatex -interaction=nonstopmode supplementary_elsevier.tex
```
