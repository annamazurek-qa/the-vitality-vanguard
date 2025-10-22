import re, json
from typing import Dict, List

ARTICLE_TYPES = [
    ("Systematic review", [r"systematic review", r"meta-?analysis"]),
    ("Meta-analysis", [r"meta-?analysis"]),
    ("Protocol", [r"protocol", r"trial protocol"]),
    ("Case report", [r"case report"]),
    ("Original research", [r"randomized", r"trial", r"cohort", r"case-control", r"observational"])
]

STUDY_DESIGNS = [
    ("RCT", [r"randomi[sz]ed", r"double-?blind", r"placebo", r"parallel", r"crossover"]),
    ("Cohort", [r"cohort", r"prospective", r"retrospective"]),
    ("CaseControl", [r"case-?control"]),
    ("Observational", [r"observational"])
]

SPECIES = [
    ("Homo sapiens", [r"human|participants|patients|men|women"]),
    ("Mus musculus", [r"mouse|mice|murine"]),
    ("Rattus norvegicus", [r"rat|rats"])
]


def classify_article(title: str, abstract: str) -> Dict:
    text = f"{title}\n{abstract}".lower()
    art = "Original research"; art_conf=0.5
    for label, pats in ARTICLE_TYPES:
        if any(re.search(p, text) for p in pats):
            art = label; art_conf=0.8
            break
    design=""; dconf=0.3
    for label, pats in STUDY_DESIGNS:
        if any(re.search(p, text) for p in pats):
            design=label; dconf=0.7; break
    species=["Homo sapiens"]; sconf=0.5
    for label, pats in SPECIES:
        if any(re.search(p, text) for p in pats):
            species=[label]; sconf=0.8; break
    return {
        "article_type": art,
        "study_design": design or None,
        "species": species,
        "confidence": round((art_conf+dconf+sconf)/3,2)
    }


def classify_datatypes(protocol: Dict, title: str, abstract: str) -> List[str]:
    taxonomy = protocol.get("taxonomy", {}).get("data_types", {})
    text = f"{title}\n{abstract}".lower()
    hits = []
    for bucket, kws in taxonomy.items():
        for kw in kws:
            if kw.lower() in text:
                hits.append(bucket); break
    return sorted(set(hits))
