import re
from typing import List

class RulePack:
    def __init__(self, positives: List[str], negatives: List[str], design: List[str]):
        self.POS = [re.compile(p, re.I) for p in positives]
        self.NEG = [re.compile(p, re.I) for p in negatives]
        self.DESIGN = [re.compile(p, re.I) for p in design]

    def fires_any(self, pats, text: str) -> bool:
        return any(p.search(text) for p in pats)

    def pos(self, text: str) -> bool: return self.fires_any(self.POS, text)
    def neg(self, text: str) -> bool: return self.fires_any(self.NEG, text)
    def design_hit(self, text: str) -> bool: return self.fires_any(self.DESIGN, text)

# Seed packs for hackathon TCs (extendable)
RESVERATROL_T2D = RulePack(
    positives=[r"resveratrol", r"trans-?resveratrol", r"SRT501",
               r"type\s?2\s?diabetes|\bT2D\b|Diabetes Mellitus, Type 2",
               r"HbA1c|glycated hemoglobin|FPG|fasting plasma glucose|HOMA-?IR"],
    negatives=[r"mouse|mice|rat|murine", r"in\s?vitro|cell\s?line",
               r"\breview\b|editorial|commentary|protocol"],
    design=[r"randomi[sz]ed", r"double-?blind", r"placebo", r"trial", r"parallel", r"crossover"]
)

METFORMIN_CANCER = RulePack(
    positives=[r"metformin|biguanide",
               r"cancer|neoplasm|incidence|risk|hazard ratio|odds ratio|rate ratio"],
    negatives=[r"mouse|mice|rat|murine", r"in\s?vitro|cell\s?line",
               r"\breview\b|editorial|protocol"],
    design=[r"cohort|case-?control|randomi[sz]ed|trial|observational|prospective|retrospective"]
)

TOPIC_PACKS = {
    "resveratrol_t2d": RESVERATROL_T2D,
    "metformin_cancer": METFORMIN_CANCER,
}
