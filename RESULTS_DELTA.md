# RESULTS_DELTA.md
## Delta Tracking: Original Claims vs. Round 2 Pre-Registered Results

This document tracks every headline number, metric shift, statistical update, and claim modification between the initial manuscript and the Round 2 confirmatory suite on branch `v2-revision`.

---

### Summary Table of Headline Deltas

| Endpoint / Metric | Original / Exploratory Value | Round 2 Confirmatory Value | Delta / Shift | Reason for Shift | Impact on Paper Claims |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **B0 Hop-1 Leak Rate ($T_{\text{B0}}$)** | $0.700$ | $0.346$ | $-0.354$ | Shift from exploratory single-secret to 26 frozen TEST secrets across 10 domains | Confirms lower baseline leakage under naturalistic multi-domain secrets. |
| **Gateway Hop-1 Leak Rate ($T_{\text{gw}}$)** | $0.017$ ($1.7\%$) | $0.073$ ($7.3\%$) | $+0.056$ | Evaluated across diverse held-out TEST secrets with ensemble resolution | Replaces single-secret estimate; leakage reduction is $\sim 5\times\text{--}12\times$ rather than "40-fold". |
| **500-Agent Outbreak Floor ($p=1.0$)** | $2\%\text{--}9\%$ (mean $\approx 6.6\%$) | $25.0\%\text{--}26.2\%$ (closed-form: $26.16\%$) | $+19.5\%$ | Calculated with true TEST transmissibility $T_{\text{gw}} = 0.073$ rather than exploratory $0.017$ | Abstract and results updated to state honest $\sim 25\%$ floor under full protection; reinforces need for filter rotation. |
| **Static ACL (B4) on Free-Text Tasks** | B4 beat gateway ($U=0.828, T=0$) on separate fields | B4-schema: $T=0.958, U=0.77$<br>B4-taint: $T=0.00, U=0.00$<br>Gateway: $T=0.125, U=0.76$ | B4 fails on unstructured text | In separate fields, B4 drops columns easily. In free text, B4-schema is blind and B4-taint destroys all utility. Gateway is TOST-equivalent. | Proves the gateway's core reason to exist: protecting unstructured text where schema controls fail. |
| **Detector Stack Agreement** | "Independent 1.00 agreement" | $\kappa = 0.51$ (Ensemble), $\kappa = 0.71$ ($D_1$), $\kappa = 0.79$ (Handle refinement) | More transparent reporting | Disclosed that 1.00 agreement came from post-hoc adjudication; co-reported $D_1$ alongside Ensemble. | Honest detector hygiene; removes circularity claims. |
| **12-Agent Topology Confirmation** | "6/6 coverage confirms the simulator" | Suggestive / Inconclusive (wide CIs, tree topology constraints) | Re-framed as suggestive | 12-agent BFS trees have limited branching; predictions across topologies overlap | Weak design acknowledged as a limitation rather than claiming definitive proof. |

---

### Detailed Analysis of Substantive Changes

#### 1. Outbreak Floor Revision (Job 7)
* The formula $P_{\text{floor}} = 1 - (1 - T_{\text{gw}})^k$ demonstrates that on networks with average degree $\langle k \rangle = 4$, an initial leak rate of $T_{\text{gw}} = 0.073$ yields an outbreak probability of $1 - (1 - 0.073)^4 = 26.16\%$.
* 200 Monte Carlo runs on 500-agent Erdos-Renyi networks confirm $P(\text{outbreak}) = 0.250$ at $p=1.0$.
* **Action Taken:** The abstract floor of "2–9%" is updated to report the 25–26% floor for the headline ensemble and up to 74.9% under detector $D_1$.

#### 2. Free-Text Resolution of the B4 Contradiction (Job 1)
* Previous evaluations evaluated B4 by simply omitting the separate database column `secret_text`. Under that setup, B4 trivially preserved all other columns while removing the secret.
* Job 1 evaluated the realistic scenario where confidential disclosures are entangled inside unstructured incoming messages (customer emails and onboarding notes).
* In this setting, schema-level stripping (`B4-schema`) passes the note completely unaltered ($T=0.958$), while coarse-grained taint tracking (`B4-taint`) suppresses the entire message, resulting in zero usefulness ($U=0.00$). The semantic gateway achieves $U=0.76$ (TOST-equivalent to B0 within $\pm 0.05$) while suppressing leakage.

