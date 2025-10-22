import os, re, json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

#import fitz  # 
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()


class PDFLLMExtractor:
    """
    Minimal MVP extractor for PDFs using Nebius (OpenAI-compatible) LLMs.
    - Parses pages (text-only)
    - Heuristically slices sections
    - Builds a compact context
    - Calls LLM and parses strict JSON
    - Optional debug mode prints/records essential intermediate outputs
    """

    # ---------- Regex config ----------
    TABLE_HINT = re.compile(r"(?:\bTable\s*\d+\b)|(?:\|)|(?:\t)|(?:\s{2,}\S+\s{2,})")
    SECTION_HEADS = [
        ("abstract",   re.compile(r"(?is)\babstract\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),
        ("methods",    re.compile(r"(?is)\bmaterials?\s+and\s+methods?\b|\bmethods?\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),
        ("results",    re.compile(r"(?is)\bresults(?:\s+and\s+discussion)?\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),
        ("discussion", re.compile(r"(?is)\bdiscussion\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),
        ("conclusion", re.compile(r"(?is)\bconclusion[s]?\b(.*?)(?:\n[A-Z][^\n]{0,60}\n|\Z)")),
    ]
    KW = re.compile(r"(?i)\b(lifespan|survival|longevity|metformin|%|mM)\b")

    # ---------- Default extraction schema ----------
    EXTRACTION_SCHEMA = {
        "study_metadata": {
            "study_id": "string|null",
            "design": "RCT|cohort|case-control|trial|other|null"
        },

        "exposure": {
            "label": "string|null",         # intervention or exposure (e.g., resveratrol, metformin)
            "comparator": "string|null"     # placebo|non_use|standard_care|other
        },

        "effects_by_outcome": [
            {
                "name": "HOMA_IR|FPG|HbA1c|overall_cancer|site_specific|other",
                "type": "MD|SMD|RR|OR|HR|LOGRR|LOGOR|LOGHR|null",
                "timepoint_weeks": "float|null",
                "estimate": "float|null",     # on the scale implied by 'type' (e.g., MD or RR or LOGRR)
                "ci_low": "float|null",
                "ci_high": "float|null",
                "adjusted": "true|false|null",
                "unit": "HOMA_units|mmol_L|mg_dL|%|ratio|other|null",
                "subgroup": "string|null",    # optional: pooled separately if present
                "notes": "string|null"
            }
        ],

        "outcomes_raw": [
            {
                "name": "string",
                "timepoint_weeks": "float|null",
                "arm_name": "intervention|control|exposed|unexposed|other",
                "n": "int|null",
                "baseline_mean": "float|null",
                "baseline_sd": "float|null",
                "followup_mean": "float|null",
                "followup_sd": "float|null",
                "change_mean": "float|null",
                "change_sd": "float|null",
                "units": "string|null"
            }
        ],

        "comment_detailed": "string"      # free-form debugging/explanation text (no length limit)
    }

    SYSTEM_PROMPT = (
      "You are a precise information extraction engine. "
      "Return ONLY a valid, minified JSON object that matches the requested schema. "
      "Use null when a field is unknown. Do not include any extra keys or commentary."
    )

    def __init__(
        self,
        base_url: str = "https://api.studio.nebius.com/v1/",
        model: str = "openai/gpt-oss-20b",
        temperature: float = 0.0,
        max_tokens: int = 5000,
        debug: bool = False,
        save_debug: bool = False,
        debug_dir: str = "debug_logs",
        output_dir: Optional[str] = "extractor_output",
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.debug = debug
        self.save_debug = save_debug
        self.pdf_name = None
        self.debug_dir = Path(debug_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        if self.save_debug:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        self.client = OpenAI(
            base_url=base_url,
            api_key=os.getenv("NEBIUS_API_KEY")
        )

    # ========= Utility: debug printing/saving =========
    def _d(self, *args):
        if self.debug:
            print("[DEBUG]", *args)

    def _save_text(self, name: str, data: Any) -> Path:
        """Save debug data to a UTF-8 .txt file.

        Accepts strings and other Python types (e.g., dict, list). Dicts are
        rendered with one top-level key per block for readability.
        """
        if not self.save_debug:
            return Path()

        def _indent(text: str, n: int = 2) -> str:
            pad = " " * n
            return "\n".join(pad + line if line else pad for line in text.splitlines())

        def _format_value(val: Any) -> str:
            # Strings: pretty-print if they contain valid JSON
            if isinstance(val, str):
                s = val.strip()
                if s.startswith("{") or s.startswith("["):
                    try:
                        parsed = json.loads(s)
                        return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
                    except Exception:
                        pass
                return val
            # Mapping: pretty JSON for nested dicts when not top-level
            if isinstance(val, dict):
                try:
                    return json.dumps(val, ensure_ascii=False, indent=2, sort_keys=True)
                except Exception:
                    from pprint import pformat
                    return pformat(val, width=100, compact=False)
            # Sequences/Sets: one item per line
            if isinstance(val, (list, tuple, set)):
                lines = []
                for item in val:
                    try:
                        as_json = json.dumps(item, ensure_ascii=False)
                    except Exception:
                        from pprint import pformat
                        as_json = pformat(item, width=100, compact=False)
                    lines.append(f"- {as_json}")
                return "\n".join(lines)
            # Fallback: JSON if possible, else repr
            try:
                return json.dumps(val, ensure_ascii=False, indent=2)
            except Exception:
                from pprint import pformat
                return pformat(val, width=100, compact=False)

        def _format_for_save(obj: Any) -> str:
            # Top-level dict: one block per key with clear separation
            if isinstance(obj, dict):
                parts = []
                for k in sorted(obj.keys(), key=lambda x: str(x)):
                    v = obj[k]
                    v_text = _format_value(v)
                    parts.append(f"{k}:\n{_indent(v_text, 2)}")
                return "\n\n".join(parts)
            # Other types
            return _format_value(obj)

        text = _format_for_save(data) if data is not None else ""

        fname = self.debug_dir / f"{self.pdf_name}_{name}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)
        self._d(f"Saved {name} -> {fname}")
        return fname

    def _save_output(self, pdf_path: str, payload: Dict[str, Any]) -> Optional[Path]:
        """Persist extraction results to `extractor_output/<pdfname>.json`."""
        if not self.output_dir:
            return None

        target = self.output_dir / f"{self.pdf_name}.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self._d(f"Saved extraction output -> {target}")
        return target

    # ========= PDF → pages =========
    def extract_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        pages: List[Dict[str, Any]] = []
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for i, page in enumerate(reader.pages):
                    # PyPDF2 may return None if the page has no extractable text
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        text = ""
                    text = re.sub(r"[ \t]+", " ", text)
                    text = re.sub(r"\n{3,}", "\n\n", text).strip()
                    pages.append({"page": i + 1, "text": text})
        except Exception as e:
            self._d(f"PDF read error: {type(e).__name__}: {e}")

        self._d(f"Pages extracted: {len(pages)}")
        if pages:
            self._d("Page[1] head:", repr(pages[0]["text"][:200]))
            if self.save_debug:
                self._save_text('pages', pages)
        return pages

    # ========= Table-ish finder (text only) =========
    def find_table_like_blocks(self, text: str, window: int = 6) -> List[str]:
        lines = text.splitlines()
        hits = []
        for i, l in enumerate(lines):
            if self.TABLE_HINT.search(l):
                start = max(0, i - window)
                end = min(len(lines), i + window)
                hits.append("\n".join(lines[start:end]))
        uniq = []
        for h in hits:
            if not any(fuzz.token_set_ratio(h, u) > 90 for u in uniq):
                uniq.append(h)
        return uniq

    # ========= Section slicing =========
    def slice_sections(self, full_text: str) -> Dict[str, str]:
        out = {}
        for name, rx in self.SECTION_HEADS:
            m = rx.search(full_text)
            if m:
                out[name] = m.group(1).strip()[:8000]
        for k, v in out.items():
            self._d(f"Section '{k}' length: {len(v)}")
        return out

    # ========= Context builder =========
    def build_context(self, pages: List[Dict[str, Any]], include_tables: bool = True) -> Dict[str, str]:
        full = "\n\n---PAGE BREAK---\n\n".join(p["text"] for p in pages)
        secs = self.slice_sections(full)

        table_blocks = []
        if include_tables:
            for p in pages:
                table_blocks += self.find_table_like_blocks(p["text"])

        context = {
            "abstract": secs.get("abstract", "")[:4000],
            "methods": secs.get("methods", "")[:6000],
            "results": secs.get("results", "")[:8000],
            "discussion": secs.get("discussion", "")[:6000],
            "conclusion": secs.get("conclusion", "")[:2000],
            "tables_texty": ("\n\n".join(table_blocks)[:6000]) if include_tables else "",
            "full_tail": full[:8000],
        }

        # Debug summary
        self._d("Context lengths:",
                {k: len(v) for k, v in context.items()})
        if self.debug:
            for key in ("results"):
                if context.get(key):
                    self._d(f"{key.upper()} head:", repr(context[key][:200]))

        if self.save_debug:
            self._save_text('context', context)

        return context

    # ========= Prompt builder =========
    def make_user_message(self, question: str, content) -> str:
        schema_json = json.dumps(self.EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)

        # Handle list of pages or dict of sections
        if isinstance(content, list):
            # Assume list of pages, each a dict with "text"
            text = "\n\n---PAGE BREAK---\n\n".join(p.get("text", "") for p in content)
        elif isinstance(content, dict):
            # Build section blocks from keys
            blocks = []
            for k, v in content.items():
                if not v:
                    continue
                title = k.replace("_", " ").upper()
                blocks.append(f"== {title} ==\n{v}")
            text = "\n\n".join(blocks)
        else:
            # Fallback: treat it as raw text
            text = str(content)

        text = text[:14000]  # Safety truncate

        msg = f"""Task: Extract fields in this schema from the article text. If unknown, use null.
Schema (types/examples, not values):
{schema_json}

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

Question: {question}

TEXT:
{text}
"""
        self._d("User message length:", len(msg))
        if self.debug:
            self._d("User message head:", repr(msg[:300]))
        return msg

    # ========= LLM call variants & extraction =========
    def _make_kwargs(self, system_prompt: str, user_payload: str, try_json_mode: bool, as_parts: bool) -> Dict[str, Any]:
        messages = (
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ] if not as_parts else
            [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": user_payload}]},
            ]
        )
        kwargs = dict(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            seed=7,
            messages=messages
        )
        if try_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    def _extract_any_content(self, resp) -> Tuple[str, str]:
        info = []
        try:
            choice0 = resp.choices[0]
        except Exception:
            return "", "No choices[0] on response."

        # 1) Standard chat content
        try:
            text = choice0.message.content
            if text:
                info.append("message.content")
                return text, " | ".join(info)
        except Exception:
            pass

        # 2) function_call.arguments
        try:
            fc = getattr(choice0.message, "function_call", None)
            if fc and getattr(fc, "arguments", None):
                info.append("function_call.arguments")
                return fc.arguments, " | ".join(info)
        except Exception:
            pass

        # 3) tool_calls[*].function.arguments
        try:
            tc = getattr(choice0.message, "tool_calls", None)
            if tc and len(tc) > 0:
                for t in tc:
                    func = getattr(t, "function", None)
                    if func and getattr(func, "arguments", None):
                        info.append("tool_calls[0].function.arguments")
                        return func.arguments, " | ".join(info)
        except Exception:
            pass

        # 4) Legacy choice.text
        try:
            text = getattr(choice0, "text", None)
            if text:
                info.append("choice.text")
                return text, " | ".join(info)
        except Exception:
            pass

        return "", "No content found in known fields."

    def llm_raw_output_all(self, system_prompt: str, user_payload: str) -> str:
        attempts = [
            ("jsonmode_on_string",  True,  False),
            ("jsonmode_off_string", False, False),
            ("jsonmode_on_parts",   True,  True),
            ("jsonmode_off_parts",  False, True),
        ]

        for label, json_mode, as_parts in attempts:
            self._d(f"Attempt: {label}")
            kwargs = self._make_kwargs(system_prompt, user_payload, json_mode, as_parts)
            try:
                resp = self.client.chat.completions.create(model=self.model, **kwargs)
            except Exception as e:
                self._d(f"{label} -> API error: {type(e).__name__}: {e}")
                continue

            # Save full response JSON (optional)
            full = ""
            try:
                full = resp.to_json()
            except Exception:
                try:
                    full = json.dumps(resp, ensure_ascii=False, default=str)
                except Exception:
                    full = "<unserializable response>"
            self._save_text(f"full_response_{label}", full)

            text, where = self._extract_any_content(resp)
            if text:
                self._d(f"{label} -> content via {where}, length={len(text)}")
                self._save_text(f"llm_raw_{label}", text)
                if self.debug:
                    self._d("Raw head:", repr(text[:200]))
                    self._d("Raw tail:", repr(text[-200:]))
                return text
            else:
                self._d(f"{label} -> empty content. Details: {where}")

        self._save_text("llm_raw_all_attempts_empty", "")
        raise RuntimeError("All attempts returned empty content. Inspect the saved full_response_*.txt files.")

    # ========= JSON parsing (transparent) =========
    def parse_json_safely(self, text: str) -> Dict[str, Any]:
        steps = []
        try:
            obj = json.loads(text); steps.append("A: direct json.loads OK"); self._log_steps(steps); return obj
        except Exception as e: steps.append(f"A: direct failed: {type(e).__name__}: {e}")

        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            candidate = text[s:e+1]
            try: obj = json.loads(candidate); steps.append("B: brace-crop OK"); self._log_steps(steps); return obj
            except Exception as e2: steps.append(f"B: brace-crop failed: {type(e2).__name__}: {e2}")
        else:
            steps.append("B: brace-crop not possible")

        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
        try: obj = json.loads(cleaned); steps.append("C: strip-fences OK"); self._log_steps(steps); return obj
        except Exception as e3: steps.append(f"C: strip-fences failed: {type(e3).__name__}: {e3}")

        cleaned2 = re.sub(r",\s*([}\]])", r"\1", cleaned)
        try: obj = json.loads(cleaned2); steps.append("D: remove-trailing-commas OK"); self._log_steps(steps); return obj
        except Exception as e4: steps.append(f"D: remove-trailing-commas failed: {type(e4).__name__}: {e4}")

        self._log_steps(steps)
        snippet = text[:400].replace("\n", "\\n")
        raise ValueError(f"Could not parse model output as JSON. First 400 chars: {snippet}")

    def _log_steps(self, steps: List[str]):
        if self.debug:
            self._d("JSON parsing steps:")
            for s in steps:
                self._d(" -", s)

    # ========= Public: run end-to-end on a PDF =========
    def extract(self, pdf_path: str, question: str) -> Dict[str, Any]:
        self.pdf_name = Path(pdf_path).stem
        # 1) Pages
        pages = self.extract_pages(pdf_path)
        if not pages:
            result = self._empty_payload("No text pages extracted (scanned PDF?)")
            self._save_output(pdf_path, result)
            return result

        # 2) Context
        # context = self.build_context(pages)
        user_payload = self.make_user_message(question, pages)

        # 3) LLM
        try:
            raw = self.llm_raw_output_all(self.SYSTEM_PROMPT, user_payload)
        except Exception as e:
            result = self._empty_payload(
                f"LLM call failed: {e}",
                evidence=[{"section": "full_tail", "page": None, "snippet": "LLM returned empty/failed; inspect full_response_*.txt"}],
            )
            self._save_output(pdf_path, result)
            return result

        # 4) Parse
        try:
            parsed = self.parse_json_safely(raw)
        except Exception as e:
            result = self._empty_payload(
                f"JSON parse failed: {e}",
                evidence=[{"section": "full_tail", "page": None, "snippet": "See llm_raw_*.txt for the raw content"}],
            )
            self._save_output(pdf_path, result)
            return result

        self._save_output(pdf_path, parsed)
        return parsed

    def extract_folder(self, folder_path: str, question: str) -> None:
        """Run extraction for every PDF in a folder (non-recursive)."""
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder_path}")
        for fp in sorted(list(folder.glob("*.pdf")) + list(folder.glob("*.PDF"))):
            self.extract(str(fp), question)

    # ========= Helper: null payload with explanation =========
    def _empty_payload(self, comment: str, evidence: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if evidence is None:
            evidence = []
        return {
            "study_metadata": {"design": None, "species": None, "n_total": None, "primary_outcome": None},
            "effect": {"type": None, "estimate": None, "ci_low": None, "ci_high": None, "p_value": None},
            "where_found": [],
            "evidence": evidence[:3],
            "missing_fields": [
                "study_metadata.design", "study_metadata.species", "study_metadata.n_total",
                "study_metadata.primary_outcome", "effect.type", "effect.estimate",
                "effect.ci_low", "effect.ci_high", "effect.p_value"
            ],
            "confidence": 0.1,
            "comment": "Extraction failed",
            "comment_detailed": comment[:600].replace("See llm_raw_*.txt for the raw content", "See terminal logs (llm_raw_* dump) for the raw content")
        }


# -------------- Example usage --------------
if __name__ == "__main__":
    pdf_path = "pdfs/testcase_1/101.pdf"
    pdf_folder_path = "pdfs/test_case_1_example"
    question = "What is the effect of oral resveratrol on glycemic control in randomized human trials?"

    extractor = PDFLLMExtractor(
        model="openai/gpt-oss-20b",
        debug=True,          # print essential debug
        save_debug=True      # also dump raw/full responses to debug_logs/
    )
    
    # result = extractor.extract(pdf_path, question)

    # process all PDFs in a folder
    extractor.extract_folder(pdf_folder_path, question)
