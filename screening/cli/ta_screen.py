import argparse, json, os
from typing import Dict
from screening.src.kw_rules import TOPIC_PACKS
from screening.src.classifier import TAClassifier
from screening.src.taxonomy import classify_article, classify_datatypes
from screening.src.decisions import append_decision


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--citations", required=True)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--classifications", required=True)
    ap.add_argument("--topic", default="resveratrol_t2d", choices=list(TOPIC_PACKS.keys()))
    ap.add_argument("--threshold", type=float, default=0.70)
    args = ap.parse_args()

    with open(args.protocol, "r", encoding="utf-8") as f:
        protocol: Dict = json.load(f)

    pack = TOPIC_PACKS[args.topic]
    clf = TAClassifier(); clf.threshold = args.threshold

    # Optional: if you have seed labels, train here. For hackathon MVP, skip training.
    # (You can later add a small labeled set and call clf.train(records, labels))

    # classification output log
    cls_f = open(args.classifications, "w", encoding="utf-8")

    for rec in load_jsonl(args.citations):
        tid = rec["id"]
        text = (rec.get("title","") + "\n" + rec.get("abstract",""))
        rule_hits = []
        if pack.pos(text): rule_hits.append("kw_pos")
        if pack.design_hit(text): rule_hits.append("kw_design")
        if pack.neg(text): rule_hits.append("kw_neg")

        p = clf.score(rec)
        if ("kw_neg" in rule_hits) and p < 0.5:
            decision, reason = "exclude", "negative_rule"
        elif p >= clf.threshold:
            decision, reason = "include", "ml_high"
        elif p >= 0.5:
            decision, reason = "maybe", "ml_mid"
        else:
            decision, reason = "exclude", "ml_low"

        append_decision(args.decisions, {
            "id": tid, "stage": "ta", "decision": decision,
            "reason": reason, "score": round(float(p),4),
            "threshold": clf.threshold, "rules": rule_hits
        })

        # Automated classification (article type / design / species / data types)
        auto = classify_article(rec.get("title",""), rec.get("abstract",""))
        auto["id"] = tid
        auto["data_type"] = classify_datatypes(protocol, rec.get("title",""), rec.get("abstract",""))
        cls_f.write(json.dumps(auto, ensure_ascii=False) + "\n")

    cls_f.close()

if __name__ == "__main__":
    main()
