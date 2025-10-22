Workflow Stages  SEARCH → SELECT → EXTRACT → ANALYZE → REPORT
```
├─ Planner/Controller
├─ Search Agent
├─ Screening Agent
├─ Extraction Agent
├─ Stats Agent
├─ Report Agent
```
## Extraction Agent
Not an agent really
### Input
**pdf file**

**question**
```
What is the effect of metformin on lifespan in animal models?

Testcase A — Resveratrol & T2D (RCTs, continuous outcomes)
Question: In adults with type 2 diabetes (or high metabolic risk), does oral resveratrol supplementation, compared with placebo or no resveratrol, improve glycemic control—specifically HOMA-IR, fasting plasma glucose (FPG), and HbA1c—over 4–24 weeks?

What is the effect of oral resveratrol on glycemic control in randomized human trials?

Testcase B — Metformin & Cancer Incidence (observational, relative risks)
Question: In adults, is metformin use (ever/current vs non-use) associated with a lower risk of incident cancer, compared with no metformin, across cohort, case-control, or randomized designs?
Rationale: The review pools cancer incidence across RCT/cohort/case-control, extracts adjusted effect estimates when available, and standardizes comparator to non-use.

```

**SYSTEM_PROMPT (predefined)**

**json EXTRACTION_SCHEMA (predefined now, should not be)**

**Rules for llm to answer (predefined)**

### Flow
pages = self.extract_pages(pdf_path)

(Skipped)
~~Building context from predefined keywords and found tables.
context = self.build_context(pages)
	slice_sections(full_text)
	find_table_like_blocks(p["text"])~~
	
User message is a combination of question, json EXTRACTION_SCHEMA, Rules for llm to answer and context
user_payload = self.make_user_message(question, pages)

raw = self.llm_raw_output_all(self.SYSTEM_PROMPT, user_payload)

parsed = self.parse_json_safely(raw)
### Output
parsed json

### Improvement plan and ideas
Context building is not working now. It is skipped. Sections are predefined, and I believe, the text from them is bound by the page ending. 

I need to think of how to narrow the search context. Maybe use a more advanced extractor that can see sections and make an small llm call to filter out irrelevant ones

json EXTRACTION_SCHEMA is predefined. I think it should vary with the research question 

I still have no idea of what to extract specifically

Don't know how to handle different outcome types in multiple researches 