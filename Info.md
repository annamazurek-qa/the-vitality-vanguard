# Challenge info
### How usually it's been done by human researcher

Step 1
Define question and protocol
1. Define the research question (PICO)
	Use the PICO framework (Population, Intervention, Comparison, Outcome)
2. Specify eligibility criteria
3. Develop a search strategy
4. Outline analysis and register

Step 2
Conduct search and select studies
Search multiple databases
Identify grey literature
Screen against criteria
Ensure dual review

At the end you have a set of literature that you think is highly relevant

Step 3
Statistical analysis
Extract effect size, p value, sample size, errow term for example for lifespan extension

### The challenge 
- Automate meta-analysis of (aging first) clinical trials. Make an AI agent that does that
- Prepare a nice report
- Optimize model efficiency

Your system should accept a research question as input, such as _"What is the effect of metformin on lifespan in animal models?"_, and autonomously produce a complete, publication-ready meta-analysis

The challenge will have a specific focus on biomedical interventions related to longevity and age-related diseases. This includes pharmaceuticals like **metformin and rapamycin**, as well as lifestyle interventions such as **caloric restriction or the Mediterranean diet**.

### META_ANALYSIS_PIPELINE
#### AUTOMATED WORKFLOW

##### SEARCH

- • PubMed, Embase, Cochrane
- • bioRxiv, medRxiv
- • Google Scholar

##### SELECT

- • Inclusion/exclusion criteria
- • Relevance screening
- • Quality assessment

##### EXTRACT

- • Statistical data from PDFs
- • Tables and figures
- • Effect sizes, confidence intervals

##### ANALYZE

- • Statistical synthesis
- • Heterogeneity assessment
- • Forest plots, funnel plots
### > EVALUATION_FRAMEWORK

#### Study Selection Accuracy

25%

Precision and recall against gold-standard dataset curated by expert reviewers.

#### Data Extraction Accuracy

25%

Agreement rates with manually extracted effect sizes, confidence intervals, and sample sizes.

#### Statistical Validity

25%

Reproduce published meta-analyses within acceptable margins, correct heterogeneity handling.

#### Time Efficiency

25%

Total computation time vs documented person-hours for manual meta-analysis.

#### ADVANCED CAPABILITIES (BONUS)

⚡Real-time updating as new studies are published

⚡Interactive visualization dashboards for subgroup analyses

⚡Integration with regulatory submission formats (FDA/EMA)
### TEST_CASES_&_VALIDATION 
TEST_CASE_1 
[Resveratrol supplementation and type 2 diabetes: a systematic review and meta-analysis - PubMed](https://pubmed.ncbi.nlm.nih.gov/33480264/)
TEST_CASE_2 
[Association of metformin use and cancer incidence: a systematic review and meta-analysis - PubMed](https://pubmed.ncbi.nlm.nih.gov/38291943/)
### TECHNICAL_REQUIREMENTS

#### STUDY DESIGN HANDLING

Handle multiple study designs including randomized controlled trials, cohort studies, and case-control studies, as each requires different statistical approaches and quality assessment criteria.

Randomized Controlled Trials Cohort Studies Case-Control Studies

#### AUTOMATED CLASSIFICATION

Core task: automated classification of all selected articles across multiple domains. For each article, the system should identify:

##### ARTICLE TYPE

Original research, systematic review, meta-analysis, case report, etc.

##### DATA TYPE

Blood biochemistry, RNA sequencing, DNA methylation, neurocognitive tests

##### BIOLOGICAL SPECIES

Homo sapiens, Mus musculus, etc.

#### STRUCTURED OUTPUT

##### Brief Intervention Description

3-4 sentences: active agent, molecular targets, delivery method

##### Agentic Study Selection

Automated study selection process

##### Intervention Effects

Mortality & disease risk (aggregated data using coding agents)

##### Evidence Basis

Methods used to generate data (clinical trials, animal studies)

##### Data Quality Assessment

Confidence score based on study type and journal quality

### RESOURCES_&_GUIDELINES

#### ESSENTIAL READING

- [Cochrane Handbook](https://training.cochrane.org/handbook)
    
    Systematic Reviews of Interventions
    
- [PRISMA Statement](http://www.prisma-statement.org/)
    
    Reporting standards for your system
    
- [Introduction to Meta-Analysis](https://www.meta-analysis.com/)
    
    Borenstein et al. with code examples
    

#### TECHNICAL TOOLS

- [PubMed API](https://www.ncbi.nlm.nih.gov/home/develop/api/)
    
    Literature search and access
    
- [Grobid](https://grobid.readthedocs.io/)
    
    PDF data extraction
    
- [metafor R package](https://www.metafor-project.org/)
    
    Statistical analysis implementation
    

#### ADDITIONAL RESOURCES

##### PDF PARSING

- • [LlamaParse](https://github.com/run-llama/llama_parse) (LLM-native)
- • [PyPDF2](https://pypi.org/project/PyPDF2/) (standard library)

##### VALIDATION & QUALITY

- • [Validation Dataset](https://github.com/hyesunyun/llm-meta-analysis)
- • Traffic light scoring (Green/Yellow/Red)
##### LLM TOOLS 
- [vLLM](https://docs.vllm.ai/en/latest/) & [LM Studio - Local AI on your computer](https://lmstudio.ai/) Local deployment of LLMs 
- [LiquidAI/LFM2-1.2B-Extract · Hugging Face](https://huggingface.co/LiquidAI/LFM2-1.2B-Extract) Text extraction 
- [Qwen/Qwen3-Coder-30B-A3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) Lightweight and powerful enough local coding agent