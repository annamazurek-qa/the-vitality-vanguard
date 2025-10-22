"""Embeddings with a graceful fallback.
Uses sentence-transformers if available; else TF-IDF.
Toggle via env USE_EMBEDDINGS=true|false
"""
import os
from typing import List

_USE_EMB = os.getenv("USE_EMBEDDINGS", "false").lower() in {"1","true","yes"}

_vec = None

def load():
    global _vec
    if _vec is not None: return _vec
    if _USE_EMB:
        try:
            from sentence_transformers import SentenceTransformer
            _vec = SentenceTransformer("all-MiniLM-L6-v2")
            return _vec
        except Exception:
            pass
    # fallback: TF-IDF
    from sklearn.feature_extraction.text import TfidfVectorizer
    _vec = TfidfVectorizer(max_features=5000, ngram_range=(1,2))
    return _vec

def fit_transform(texts: List[str]):
    v = load()
    if hasattr(v, "fit_transform"):
        return v.fit_transform(texts)
    return v.encode(texts)

def transform(texts: List[str]):
    v = load()
    if hasattr(v, "transform"):
        return v.transform(texts)
    return v.encode(texts)
