import re
from typing import Dict
from .clients import ingestion

WEIGHTS = {"design":0.4, "population":0.3, "outcomes":0.3}


def _has(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, flags=re.I))


def check_fulltext(study_id: str, protocol: Dict) -> Dict:
    ft = ingestion.get_fulltext_text(study_id)
    if ft.get("status") == "unavailable":
        return {"include": False, "reason": "fulltext_unavailable", "score": 0.0}

    meta = ingestion.get_metadata(study_id)
    sections = ft.get("sections", {})
    methods = sections.get("methods", "")
    results = sections.get("results", "") + "\n" + sections.get("abstract", "")

    # DESIGN
    designs = protocol.get("designs", [])
    design_ok = False
    if meta.get("study_design") in designs:
        design_ok = True
    else:
        for d in designs:
            if d == "RCT" and _has(methods, r"randomi[sz]ed|placebo|double-?blind"):
                design_ok = True
            if d == "Cohort" and _has(methods, r"cohort|prospective|retrospective"):
                design_ok = True
            if d == "CaseControl" and _has(methods, r"case-?control"):
                design_ok = True
    # POPULATION
    pop_ok = _has(results+methods, r"type\s?2\s?diabetes|\bT2D\b|adult") if protocol.get("pico",{}).get("population") else True

    # OUTCOMES
    outs = protocol.get("pico",{}).get("outcomes", [])
    outcome_ok = any(_has(results, re.escape(o)) for o in outs) if outs else True

    score = (WEIGHTS["design"]*(1.0 if design_ok else 0.0) +
             WEIGHTS["population"]*(1.0 if pop_ok else 0.0) +
             WEIGHTS["outcomes"]*(1.0 if outcome_ok else 0.0))

    if score >= 0.75:
        return {"include": True, "reason": "ft_score_high", "score": round(score,2)}
    if score >= 0.55:
        return {"include": False, "reason": "human_review", "score": round(score,2)}
    return {"include": False, "reason": "ft_score_low", "score": round(score,2)}