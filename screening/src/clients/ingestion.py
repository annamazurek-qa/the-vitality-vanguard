"""Contract-only client for Module 4 / ingestion.
Replace stubs with real HTTP/RPC calls provided by Dmitry's module.
"""
from typing import Dict

# Simple in-memory stubs you can swap out.
_FAKE_FULLTEXT = {}
_FAKE_META = {}

def register_fulltext(study_id: str, sections: Dict):
    _FAKE_FULLTEXT[study_id] = {"id": study_id, "sections": sections}

def register_metadata(study_id: str, meta: Dict):
    _FAKE_META[study_id] = meta

def get_fulltext_text(study_id: str) -> Dict:
    return _FAKE_FULLTEXT.get(study_id, {"status":"unavailable"})

def get_metadata(study_id: str) -> Dict:
    return _FAKE_META.get(study_id, {})
