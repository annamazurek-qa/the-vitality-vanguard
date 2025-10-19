import json, re
from typing import List, Tuple
from . import embedder

class TAClassifier:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.threshold = 0.70

    def train(self, records: List[dict], labels: List[int]):
        # records must contain title+abstract
        texts = [f"{r.get('title','')} [SEP] {r.get('abstract','')}" for r in records]
        X = embedder.fit_transform(texts)
        # choose model
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.calibration import CalibratedClassifierCV
            base = LogisticRegression(max_iter=500)
            self.model = CalibratedClassifierCV(base)
            self.model.fit(X, labels)
        except Exception:
            # super-lightweight fallback: keyword prior only
            self.model = None
            self.vectorizer = None
        self.vectorizer = embedder.load()

    def score(self, rec: dict) -> float:
        text = f"{rec.get('title','')} [SEP] {rec.get('abstract','')}"
        if self.model is not None:
            if hasattr(self.vectorizer, "transform"):
                X = self.vectorizer.transform([text])
            else:
                X = self.vectorizer.encode([text])
            p = float(self.model.predict_proba(X)[0,1])
            return p
        # no model: simple heuristic
        s = text.lower()
        p = 0.5
        p += 0.2 if re.search(r"randomi[sz]ed|trial|placebo", s) else 0
        p += 0.2 if len(s) > 200 else 0
        return max(0.0, min(1.0, p))
