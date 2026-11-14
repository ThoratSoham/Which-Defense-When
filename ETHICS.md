# ETHICS.md
## Ethics, Responsible Disclosure & Dual-Use Considerations

### 1. Synthetic Data & Privacy Protection
All empirical evaluations in this research use entirely synthetic data. No real-world customer tickets, employee records, patient health information (PHI), or personally identifiable information (PII) were accessed, processed, or collected. Synthetic entity names, identifiers, and factual disclosures were designed to mimic enterprise workflows while guaranteeing that zero private individual data is implicated.

### 2. Dual-Use Analysis
The methodologies evaluated in this benchmark focus on boundary security, filtering mechanisms, and leak quantification in multi-agent systems. While understanding the failure modes of lexical and semantic gateways provides insights into evasion (e.g. paraphrase or translation bypass), the explicit goal is to quantify defensive guarantees and guide secure multi-agent system design. The defense strategies studied (content-aware semantic gateways, static ACLs, and multi-tier rotation) provide defensive blueprints for practitioners to prevent accidental data dissemination.

### 3. Model Integrity & Environmental Impact
Inference was conducted primarily on energy-efficient local small models (2B–3B parameters) and rate-limited free API tiers. Checkpointing and deterministic caching protocols were enforced to avoid redundant computations, minimizing energy consumption and carbon footprint during the 72-hour evaluation window.

