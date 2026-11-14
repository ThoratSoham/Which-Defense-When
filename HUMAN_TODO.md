# Human Author Checklist & Remaining Action Items

This document outlines tasks that strictly require human intervention, offline resources, or personal author decisions prior to final journal submission.

---

### 1. Benchmark Annotation & Inter-Rater Reliability (High Priority)
- [ ] **Engage a Second Independent Human Annotator:**
  - The detector validation in Table 2 currently relies on a single human annotator across the 300 stratified TEST notes, with ties adjudicated.
  - *Task:* Recruit an independent second annotator to review the 300 blinded notes without access to the first annotator's labels or model markers.
  - *Calculation:* Calculate inter-annotator Cohen's $\kappa$ and Fleiss' $\kappa$ across both human raters to establish a robust, non-adjudicated human baseline.

### 2. Research Data Repository & Persistent DOI
- [ ] **Deposit Transcripts & Code to Zenodo / OSF:**
  - The manuscript currently references a placeholder DOI: `https://doi.org/10.5281/zenodo.placeholder`.
  - *Task:* Archive the git repository, frozen outputs (`results/freeze.ok`), raw conversation transcripts, and replication scripts to Zenodo.
  - *Update:* Replace the placeholder DOI in `main_elsevier.tex` and un-blinded camera-ready versions.
- [ ] **Anonymized Repository for Double-Blind Review:**
  - Verify that the anonymous GitHub repository or Anonymous GitHub link provided in `main_tmlr.tex` contains no author usernames, commit metadata, or identifiable paths.

### 3. Institutional & Funding Verification
- [ ] **Grant & Funding Contracts:**
  - Confirm whether explicit grant numbers, sponsor names, or departmental funding codes must be acknowledged in the "Funding" section of `main_elsevier.tex`.
- [ ] **Author Affiliations & ORCID IDs:**
  - Verify institutional affiliations, email addresses, and author order for all contributing authors.
  - Ensure all authors' ORCID identifiers are correctly registered in the submission portal.

### 4. Journal-Specific Submission Steps
- [ ] **Elsevier Submission:**
  - Prepare a formal Cover Letter to the Editor-in-Chief highlighting the paper's core contributions, the decision-map framework, and confirmation of originality.
  - Upload `main_elsevier.pdf`, `supplementary_elsevier.pdf`, source files (`.tex`, `.bib`, `macros.tex`, and figure PDFs/PNGs), and Highlights.
- [ ] **TMLR Submission:**
  - Upload `main_tmlr.pdf`. Verify that the generated PDF does not contain author names or affiliations (anonymity mode enabled via `\usepackage[accepted]{tmlr}` omitted during review).
  - Certify that the main manuscript body (Sections 1--9) is within the 12-page limit (currently 11 pages).

### 5. Final Sanity & Integrity Audits
- [ ] **Automated Script Verification:**
  - Confirm that `python check_numbers.py` continues to return `[SUCCESS]` (0 hardcoded numbers).
  - Confirm that `python verify_ledger.py` continues to return `[SUCCESS]` (100% / 75 knowledge items verified in both copies).
- [ ] **Repository Integrity:**
  - Ensure `main_draft.tex`, `results/freeze.ok`, and original Round 1 logs remain untampered on branch `v2-revision`.

