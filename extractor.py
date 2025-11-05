import os, re, json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import tempfile

#import fitz  # 
from PyPDF2 import PdfReader
#from docling.document_converter import DocumentConverter
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

        "outcomes": [
            {
                "name": "HOMA_IR|FPG|HbA1c",
                "timepoint_weeks": "float|null",
                "arm_name": "intervention|control|exposed|unexposed|other",
                "n": "int|null",
                "baseline_mean": "float|null",
                "baseline_sd": "float|null",
                "followup_mean": "float|null",
                "followup_sd": "float|null",
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
        output_dir: Optional[str] = "extractor_output",
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.pdf_name = None
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self.full_text_dir = (self.output_dir / "full_text_extraction") if self.output_dir else None
        if self.full_text_dir:
            self.full_text_dir.mkdir(parents=True, exist_ok=True)

        self.client = OpenAI(
            base_url=base_url,
            api_key=os.getenv("NEBIUS_API_KEY")
        )

    # ========= Utility: debug printing/saving =========
    def _d(self, *args):
        print("[DEBUG]", *args)
    
    def _sanitize_basename(self, name: str) -> str:
        # keep readable names; strip illegal fs chars and trim
        name = re.sub(r"[\\/:\*\?\"<>\|\s]+", "_", name).strip("_")
        return name or "file"

    def save_any(
        self,
        dest_dir: Union[str, Path],
        content: Union[str, bytes, dict, list],
        *,
        pdf_path: Optional[str] = None,
        base_name: Optional[str] = None,
        ext: Optional[str] = None,
        add_timestamp: bool = False,
    ) -> Optional[Path]:
        """
        Universal save (cross-platform, atomic-ish):
        - creates dest_dir if missing
        - infers extension when not given
        - writes to a temp file in the same folder, then os.replace(...) → target
        Returns Path or None on failure.
        """
        try:
            d = Path(dest_dir)
            d.mkdir(parents=True, exist_ok=True)
            if d.exists() and d.is_file():
                raise IOError(f"Destination path is a file, not a directory: {d}")

            # filename stem
            if base_name:
                stem = Path(base_name).stem
            elif pdf_path:
                stem = Path(pdf_path).stem
            else:
                stem = "output"
            stem = self._sanitize_basename(stem)

            # extension
            if ext:
                suffix = ext if ext.startswith(".") else f".{ext}"
            else:
                if isinstance(content, (dict, list)):
                    suffix = ".json"
                elif isinstance(content, bytes):
                    suffix = ".bin"
                else:
                    suffix = ".txt"

            if add_timestamp:
                from datetime import datetime
                stem = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            target = d / f"{stem}{suffix}"

            # prepare bytes
            if isinstance(content, (dict, list)):
                blob = json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
            elif isinstance(content, str):
                blob = content.encode("utf-8")
            else:
                blob = content

            # write temp then replace (works on Windows & POSIX)
            fd, tmp_path = tempfile.mkstemp(dir=str(d))
            try:
                with os.fdopen(fd, "wb") as tmp:
                    tmp.write(blob)
                os.replace(tmp_path, str(target))
            except Exception:
                # ensure temp file is removed if replace failed
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                finally:
                    raise

            self._d(f"Saved: {target}")
            return target
        except Exception as e:
            self._d(f"save_any error: {type(e).__name__}: {e}")
            return None

    def _save_output(self, pdf_path: str, payload: Dict[str, Any]) -> Optional[Path]:
        """Persist extraction results to `extractor_output/<pdfname>.json`."""
        if not self.output_dir:
            return None

        target = self.output_dir / f"{self.pdf_name}.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self._d(f"Saved extraction output -> {target}")
        return target

    def extract_text_pypdf2(self, pdf_path: str, normalize: bool = True) -> str:
        """Current backend: PyPDF2. Returns one unified text string.
        Set normalize=False to avoid whitespace/line cleanup (more 'raw')."""
        buf = []
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    try:
                        t = page.extract_text() or ""
                    except Exception:
                        t = ""
                    buf.append(t)
        except Exception as e:
            self._d(f"PyPDF2 read error: {type(e).__name__}: {e}")
            return ""
        text = "\n".join(buf)  # keep native line breaks; no extra blanks injected
        if normalize:
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def extract_text_docling(self, pdf_path: str) -> str:
        """Alternative backend: Docling. Returns one unified text string."""
        try:
            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            # markdown export tends to keep structure; normalize a bit
            text = (result.document.export_to_markdown() or "").strip()
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            return text
        except Exception as e:
            self._d(f"Docling error: {type(e).__name__}: {e}")
            return ""

    def load_saved_text(self, pdf_path: str) -> str:
        """Loads extractor_output/full_text_extraction/<pdfname>.txt if present."""
        if not self.output_dir:
            return ""
        stem = Path(pdf_path).stem
        f = (self.output_dir / "full_text_extraction" / f"{stem}.txt")
        try:
            return f.read_text(encoding="utf-8")
        except Exception as e:
            self._d(f"load_saved_text error: {type(e).__name__}: {e}")
            return ""

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

Question: {question}

TEXT:
{text}
"""
        self._d("User message length:", len(msg))
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

            text, where = self._extract_any_content(resp)
            if text:
                self._d(f"{label} -> content via {where}, length={len(text)}")
                self._d("Raw head:", repr(text[:200]))
                self._d("Raw tail:", repr(text[-200:]))
                return text
            else:
                self._d(f"{label} -> empty content. Details: {where}")

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
        self._d("JSON parsing steps:")
        for s in steps:
            self._d(" -", s)

    # ========= Public: run end-to-end on a PDF =========
    def extract(self, pdf_path: str, question: str) -> Dict[str, Any]:
        self.pdf_name = Path(pdf_path).stem
        
        # --- Single unified Docling extraction ---
        full_text = self.extract_text_pypdf2(pdf_path)

        self.save_any(
            dest_dir=(self.output_dir / "full_text_extraction"),
            content=full_text or "",
            pdf_path=pdf_path,   # will use original PDF name
            ext=".txt",
        )
        
        #full_text = self.load_saved_text(pdf_path)

        
        # User message
        user_payload = self.make_user_message(question, full_text)

        # LLM
        try:
            raw = self.llm_raw_output_all(self.SYSTEM_PROMPT, user_payload)
        except Exception as e:
            result = self._empty_payload(
                f"LLM call failed: {e}",
                evidence=[{"section": "full_tail", "page": None, "snippet": "LLM returned empty/failed; inspect full_response_*.txt"}],
            )
            self._save_output(pdf_path, result)
            return

        # Parse
        try:
            parsed = self.parse_json_safely(raw)
        except Exception as e:
            result = self._empty_payload(
                f"JSON parse failed: {e}",
                evidence=[{"section": "full_text", "page": None, "snippet": "See raw response file"}],
            )
            self._save_output(pdf_path, result)
            return

        self._save_output(pdf_path, parsed)

    def extract_folder(self, folder_path: str, question: str) -> None:
        """Run extraction for every PDF in a folder (non-recursive)."""
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder_path}")
        # Windows globbing is case-insensitive; using both patterns doubles the list.
        files = sorted({str(p.resolve()) for p in folder.glob("*.pdf")})
        for fp in files:
            self.extract(fp, question)

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
        model="openai/gpt-oss-20b"
    )
    
    # result = extractor.extract(pdf_path, question)

    # process all PDFs in a folder
    extractor.extract_folder(pdf_folder_path, question)
