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
```

**Sections to search (predefined now, should not be)**
```
SECTION_HEADS = [

        ("abstract",   re.compile(r"(?is)\babstract\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),

        ("methods",    re.compile(r"(?is)\bmaterials?\s+and\s+methods?\b|\bmethods?\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),

        ("results",    re.compile(r"(?is)\bresults(?:\s+and\s+discussion)?\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),

        ("discussion", re.compile(r"(?is)\bdiscussion\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),

        ("conclusion", re.compile(r"(?is)\bconclusion[s]?\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),

    ]
```

**SYSTEM_PROMPT (predefined)**
```
"You are a precise information extraction engine. "

"Return ONLY a valid, minified JSON object that matches the requested schema. "

"Use null when a field is unknown. Do not include any extra keys or commentary."
```

**json EXTRACTION_SCHEMA (predefined now, should not be)**
```
EXTRACTION_SCHEMA = {

  "study_metadata": {

	"design": "RCT|cohort|case-control|cross-sectional|other|null",

	"species": "Homo sapiens|Mus musculus|other|null",

	"n_total": "int|null",

	"primary_outcome": "string|null"

  },

  "effect": {

	"type": "SMD|OR|RR|HR|mean_diff|null",

	"estimate": "float|null",

	"ci_low": "float|null",

	"ci_high": "float|null",

	"p_value": "float|null"

  },

  "where_found": [{"section":"abstract|methods|results|tables_texty|full_tail","page":"int|null"}],

  "evidence": [{"section":"string","page":"int|null","snippet":"string (≤200 chars)"}],

  "missing_fields": ["string"],

  "confidence": "float in [0,1]",

  "comment": "string (≤20 words)",

  "comment_detailed": "string (≤150 words)"

}
```

**Rules for llm to answer (predefined)**
```
Rules:

- Output MUST be a SINGLE VALID JSON object (no comments, no extra keys).

- Be conservative: if uncertain, set null.

- Populate 'missing_fields' with any keys you could not fill (use dotted paths like "study_metadata.n_total").

- Include 1–3 'evidence' snippets (≤200 chars) that justify values or explain missingness.

- 'comment' ≤20 words summarizing status.

- 'comment_detailed' ≤150 words explaining: (a) what you looked for (sections/phrases),

  (b) why fields are null or uncertain, (c) what would likely help (e.g., tables, full PDF, Methods).

- Set 'confidence' in [0,1].

- If CI present, ensure estimate ∈ [ci_low, ci_high].
```

### Flow
pages = self.extract_pages(pdf_path)

(Skipped)
# Building context from predefined keywords and found tables.
# context = self.build_context(pages)
# 	slice_sections(full_text)
# 	find_table_like_blocks(p["text"])
	
User message is a combination of question, json EXTRACTION_SCHEMA, Rules for llm to answer and context
user_payload = self.make_user_message(question, pages)

raw = self.llm_raw_output_all(self.SYSTEM_PROMPT, user_payload)

parsed = self.parse_json_safely(raw)
### Output
parsed

### Improvement plan and ideas
Context building is not working now. It is skipped. Sections are predefined, and I believe, the text from them is bound by the page ending. 

I need to think of how to narrow the search context. Maybe use a more advanced extractor that can see sections and make an small llm call to filter out irrelevant ones

json EXTRACTION_SCHEMA is predefined. I think it should vary with the research question 

I still have no idea of what to extract specifically

Don't know how to handle different outcome types in multiple researches 