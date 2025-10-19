## MVP

##### Protocol&Question Formulation Agent
@Arthur
This agent's primary role is to define the scope and methodology of the review, creating a clear and answerable research question.
• Input: A high-level research topic from the user (e.g., "Aspirin for preventing heart attacks").
• Core Tasks:
1. PICO Framework Formulation: Interacts with the user to break down the topic into the
PICO framework:
• Population: Who are the subjects? (e.g., Adults over 50 with no history of cardiovascular disease).
• Intervention: What is the treatment? (e.g., Low-dose aspirin).
• Comparison: What is the alternative? (e.g., Placebo or no treatment).
• Outcome: What is being measured? (e.g., Incidence of myocardial infarction, stroke).
2. Protocol Generation: Based on the PICO, it drafts a formal protocol. This document pre-specifies the inclusion/exclusion criteria for studies, the primary and secondary outcomes, and the planned analytical methods (e.g., statistical model, heterogeneity measures).
• Output: A machine-readable protocol (e.g., JSON file) and a structured PICO question.
#### Search api
@Wesley
Make a workable code that inputs a query and outputs some articles from one or several sources in pdf or text format. 

Module 2: Systematic Search Agent &
This agent is responsible for conducting a comprehensive and unbiased search of the scientific literature to find all relevant studies.
• Input: The finalized PICO question and protocol from Module 1.
• Core Tasks:
1. Search Strategy Construction: Translates PICO elements into sophisticated search strings using medical subject headings (e.g., MeSH), keywords, and Boolean operators (AND, OR, NOT).
2. Database Querying: Executes the search across multiple academic databases via APls (e.g., PubMed, EMBASE, Cochrane Central Register of Controlled Trials).
3. Deduplication: Collates all results and automatically removes duplicate entries.
Outout: A library of unique citations (e.a. in a BibTeX or RIS file)

#### Screening
@Anna
Module 3: Screening & Selection Agent 2
This agent mimics the human process of screening thousands of articles to find the few that are truly eligible for the review.
• Input: The library of citations from Module 2 and the inclusion/exclusion criteria from the protocol.
• Core Tasks:
1. Title & Abstract Screening: Utilizes a Natural Language Processing (NLP) classification model to perform a rapid first-pass screening of titles and abstracts to exclude
obviously irrelevant studies.
2. Full-Text Retrieval & Analysis: For potentially relevant studies, the agent retrieves the full-text articles. It then employs more advanced NLP to analyze the full text against the detailed inclusion criteria (e.g., study design must be a randomized controlled trial, population age must be within a certain range).
• Output: A final list of included studies and a generated PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) flow diagram detailing the selection process

Does: relevance screening (title/abstract first pass), automatic classification (article type, data type, species), apply inclusion/exclusion, optional full-text eligibility decision using text provided by others.

##### Data extraction from pdf or text to useful data
@Dmitry
Module 4: Data Extraction & Risk of Bias Agent
ml
This agent meticulously extracts the necessary data points and critically appraises the quality of each included study.
• Input: The full-text articles of the included studies.
• Core Tasks:
1. Data Extraction: Scans the text, tables, and figures to locate and extract key quantitative data for both intervention and comparison groups (e.g., number of participants, means, standard deviations, number of events).
2. Risk of Bias (RoB) Assessment: Employs a trained model to evaluate each study based on the Cochrane Risk of Bias 2 (RoB 2) tool. It assesses domains such as the randomization process, deviations from the intended intervention, missing outcome data, and selective reporting.
• Output: A structured dataset (e.g., CSV file) containing the extracted study data and the RoB assessment for each study.
##### Data analysis & Report generation
Module 5: Meta-Analysis Agent
This is the core statistical agent that synthesizes the data from individual studies to calculate an overall result.
• Input: The structured dataset from Module 4.
• Core Tasks:
1. Statistical Synthesis: Selects the appropriate statistical model (fixed-effect or random-effects) based on anticipated heterogeneity. It then calculates the pooled effect size (e.g., Odds Ratio, Risk Ratio, or Mean Difference) with its 95% confidence interval.
2. Heterogeneity Assessment: Quantifies the degree of variation between studies using

statistics like 1' (the percentage of variation due to heterogeneity rather than chance).

3. Visualization: Generates a Forest Plot to visually display the results of individual

studies and the overall pooled result. It can also create a Funnel Plot to assess

##### Use Cases & Testing 
@Eli
Market research
Open Source - whe value of it?
https://silvi.ai/help

##### Code architecture. Agents framework development and data storage unification
## Next steps
##### Article screening agent


#### Notes from call with mentor
pubmed baseline+deabetis+metformin database

abstract final plot and forest plot - generation of statistics