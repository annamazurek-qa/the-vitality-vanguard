import json, time
from typing import Dict, Any

def _ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def append_decision(path: str, rec: Dict[str, Any]):
    rec = dict(rec)
    rec.setdefault("ts", _ts())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
