import json
from collections import Counter, defaultdict
from typing import Dict

"""Reads TA and FT decision logs and emits PRISMA-style counters as JSON."""

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def make_prisma(ta_path: str, ft_path: str = None) -> Dict:
    prisma = {
        "identified": defaultdict(int),  # optional by source
        "deduplicated": 0,               # should be provided by Module 2, keep 0 here
        "screened": 0,
        "ta_excluded": 0,
        "fulltext_assessed": 0,
        "fulltext_excluded": 0,
        "included": 0,
        "reasons": Counter()
    }

    ids_ta = set()
    for r in load_jsonl(ta_path):
        if r.get("stage") != "ta":
            continue
        ids_ta.add(r["id"])
        prisma["screened"] += 1
        if r.get("decision") == "exclude":
            prisma["ta_excluded"] += 1
            prisma["reasons"][r.get("reason","unknown")] += 1

    if ft_path:
        seen = set()
        for r in load_jsonl(ft_path):
            if r.get("stage") != "fulltext":
                continue
            if r["id"] in seen: continue
            seen.add(r["id"])
            prisma["fulltext_assessed"] += 1
            if r.get("decision") == "include":
                prisma["included"] += 1
            else:
                prisma["fulltext_excluded"] += 1
                prisma["reasons"][r.get("reason","unknown")] += 1

    prisma["reasons"] = dict(prisma["reasons"])  # to JSON
    return prisma
