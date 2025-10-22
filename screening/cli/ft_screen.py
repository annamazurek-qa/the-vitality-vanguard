import argparse, json
from typing import Dict
from screening.src.ft_eligibility import check_fulltext
from screening.src.decisions import append_decision


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ta", required=True, help="TA decisions jsonl")
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--decisions", required=True, help="append here fulltext decisions")
    args = ap.parse_args()

    with open(args.protocol, "r", encoding="utf-8") as f:
        protocol: Dict = json.load(f)

    # Only process items marked include/maybe from TA
    for r in load_jsonl(args.ta):
        if r.get("stage") != "ta":
            continue
        if r.get("decision") not in {"include","maybe"}:
            continue
        sid = r["id"]
        res = check_fulltext(sid, protocol)
        append_decision(args.decisions, {
            "id": sid,
            "stage": "fulltext",
            "decision": "include" if res["include"] else "exclude",
            "reason": res.get("reason","unknown"),
            "score": res.get("score",0.0)
        })

if __name__ == "__main__":
    main()
