Excellent — now that you have the official specification, we can tighten and upgrade your plan so it perfectly aligns with what judges expect and covers all evaluation dimensions.

Below is a refined roadmap, showing what to add, adjust, or simplify from your current version.

⸻

🚀 Refined Strategy for “Automated Meta-Analysis & Systematic Review”

⸻

1️⃣ Overall System Vision

Keep the same modular agentic architecture — but now explicitly align each agent to the official pipeline terms:

Official Stage	Your Module	Key Changes / Additions
SEARCH	SearchAgent	Must handle at least 3 sources: PubMed (via E-utilities), bioRxiv/medRxiv (via API or SerpAPI), and Google Scholar fallback. Log full query string + timestamp (for reproducibility).
SELECT	ScreeningAgent	Implement inclusion/exclusion criteria parsing + relevance scoring (e.g., 0–1 relevance). Add quality scoring (Cochrane “risk of bias” or PRISMA traffic-light rating).
EXTRACT	ExtractionAgent	Must extract numeric data (n, mean, SD, effect size, CI). Add classification of: study type (RCT/cohort/case-control), species, and data type (biochemistry, RNAseq, etc.).
ANALYZE	StatsAgent	Implement random/fixed effects meta-analysis (e.g. metafor, statsmodels, or rpy2). Include heterogeneity (I², τ²) and funnel plot generation.
REPORT (implicit)	ReportAgent	Generate PRISMA-style flow diagram + structured summary (intervention, sample, methods, effect, quality).


⸻

2️⃣ Additions to Meet “TECHNICAL_REQUIREMENTS”

✅ Automated Classification

For every included study, classify:
	•	Article Type: original / review / meta-analysis / case report (LLM or text-classifier)
	•	Study Design: RCT / cohort / case-control
	•	Species: Homo sapiens / Mus musculus
	•	Data Type: molecular / behavioral / imaging / etc.

Use a lightweight ClassificationAgent or extend ExtractionAgent with a taxonomy JSON schema.

✅ Study Design Handling
	•	Differentiate statistical models per design:
	•	RCT → standardized mean difference (SMD)
	•	Cohort → relative risk (RR) or hazard ratio (HR)
	•	Case-control → odds ratio (OR)

This can be a function switch in the StatsAgent.

✅ Quality Assessment

Implement a Confidence Score:

{
  "bias_risk": "low",
  "journal_rank": "Q1",
  "confidence_score": 0.85
}

Use journal metadata (e.g. via CrossRef API) to enrich.

⸻

3️⃣ Evaluation Framework Alignment

You must design your pipeline so each 25% category can be quantitatively measured.

Evaluation Criterion	How to Measure in Prototype
Study Selection Accuracy	Compare your selected DOIs vs. provided gold-standard list → precision/recall.
Data Extraction Accuracy	Compare your extracted values vs. provided dataset (RMSE, mean diff).
Statistical Validity	Compare meta-analysis result (effect size, CI) vs. published one.
Time Efficiency	Log timestamps → compute runtime vs. estimated human effort (from Cochrane average).

Include a small “evaluation notebook” to compute these metrics.

⸻

4️⃣ Advanced Capabilities (for bonus points)

Bonus Feature	Easy Implementation Hint
⚡ Real-time updating	Re-run PubMed query weekly; highlight new articles vs last version (hash comparison).
⚡ Interactive dashboard	Use Streamlit or Gradio to visualize forest/funnel plots and subgroup filters.
⚡ Regulatory-ready output	Export report in structured XML (PRISMA-compliant schema).


⸻

5️⃣ Adapted Project Folder Structure

meta-ai/
├── agents/
│   ├── search_agent.py
│   ├── screening_agent.py
│   ├── extraction_agent.py
│   ├── classification_agent.py
│   ├── stats_agent.py
│   └── report_agent.py
├── data/
│   ├── test_case_1_metformin/
│   ├── test_case_2_behavioral/
│   └── test_case_3_diagnostic/
├── notebooks/
│   ├── evaluation_metrics.ipynb
│   ├── forest_plot.ipynb
│   └── heterogeneity_analysis.ipynb
├── docs/
│   ├── ONE-PAGER.md
│   ├── ARCHITECTURE.md
│   ├── PRISMA_FLOW.png
│   └── QUESTIONS.md
├── meta_pipeline.py          # orchestrator
├── requirements.txt
└── README.md


⸻

6️⃣ Refined Step Flow
	1.	User Input: "What is the effect of metformin on lifespan in animal models?"
	2.	SearchAgent → fetch top 100 results (PubMed + bioRxiv)
	3.	ScreeningAgent → apply PRISMA inclusion/exclusion → produce shortlist
	4.	ExtractionAgent → parse tables + extract effect sizes (mean, SD, n)
	5.	ClassificationAgent → annotate article type, species, study design
	6.	StatsAgent → compute effect size, heterogeneity, funnel + forest plots
	7.	ReportAgent → generate structured report (PRISMA flow, summary table)
	8.	Evaluation Notebook → compare with ground truth for scoring

⸻

7️⃣ Team Adjustments

Role	New Focus
PM / Domain Lead	Define inclusion/exclusion & quality rules (PRISMA-based)
ML Engineer	Implement classification and LLM-based extraction
Data Scientist	Focus on heterogeneity stats and validation
DevOps	Create reproducible pipeline + logging
Communicator	Prepare demo, README, and visualization dashboard


⸻

8️⃣ Key Improvements from Your Original Plan

Old Plan	Adjustment
4 main agents	Expand to 5–6 (add Classification & Quality)
MVP = forest plot	MVP = PRISMA-style structured report
Manual question choice	Must include 3 provided test cases
Simple evaluation	Add quantitative metrics per official framework
General pipeline	Add study design-specific handling
Unstructured output	Produce JSON + PDF + Dashboard output


⸻


# Requirements

SEARCH	SearchAgent	Must handle at least 3 sources: PubMed (via E-utilities), bioRxiv/medRxiv (via API or SerpAPI), and Google Scholar fallback. Log full query string + timestamp (for reproducibility).

1. User Input: "What is the effect of metformin on lifespan in animal models?" 
- assuming we have a valid inquiery
2. SearchAgent → fetch top 100 results (PubMed + bioRxiv)
- api requests to 3 sources: PubMed (via E-utilities), bioRxiv/medRxiv (via API or SerpAPI), and Google Scholar fallback. Log full query string + timestamp (for reproducibility).









AI inquiery formatter. 
- a user send research inquiry per prompt
- if the inquiery is not clear - AI (e.g. Chat GPT) offers formatting