# crawler/tests/test_agent_extract.py - extraction by Claude Code sessions (no LLM calls)

import json

import pytest

from crawler import agent_extract as ae
from crawler.extractor import LLMExtractor

CONTENT = "Results: TNF-alpha strongly reduced KCC2 expression in the dorsal horn."
GOOD = {"subject": "TNF-alpha", "predicate": "downregulates", "object": "KCC2", "sign": 0,
        "evidence_quote": "TNF-alpha strongly reduced KCC2 expression", "confidence": "HIGH"}
PARAPHRASE = {**GOOD, "evidence_quote": "TNF lowers KCC2 levels in spinal neurons"}


def write_extraction(directory, pmid, rels):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{pmid}.json").write_text(json.dumps({
        "pmid": pmid, "extracted_by": "claude-code-session",
        "entities": [{"name": "TNF-alpha", "entity_type": "molecule", "aliases": [],
                      "compartment": "dorsal_horn", "mentions": 1}],
        "relationships": rels, "key_findings": [], "novel_terms": [],
    }))


def test_committed_extraction_is_a_cache_hit_and_is_reverified(tmp_path):
    extractions = tmp_path / "extractions"
    write_extraction(extractions, "1", [GOOD, PARAPHRASE])
    extractor = LLMExtractor(cache_dir=tmp_path / "cache")
    extractor.extractions_dir = extractions
    extractor.cache_only = True
    extractor._call_llm = lambda prompt: pytest.fail("no LLM call expected")

    result = extractor.extract("1", "t", CONTENT)

    assert [(r.subject, r.sign) for r in result.relationships] == [("TNF-alpha", -1)]
    assert extractor.dropped_unverified == 1
    with pytest.raises(RuntimeError, match="cache-only"):
        extractor.extract("2", "t", CONTENT)  # nothing committed for PMID 2


def test_check_reports_missing_invalid_and_dropped_quotes(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "EXTRACTIONS_DIR", tmp_path)
    write_extraction(tmp_path, "1", [GOOD, PARAPHRASE])
    (tmp_path / "2.json").write_text("{not json")
    assert ae.check_extraction("3", CONTENT)["status"] == "missing"
    assert ae.check_extraction("2", CONTENT)["status"] == "invalid_json"
    report = ae.check_extraction("1", CONTENT)
    assert (report["status"], report["relationships"], report["kept"]) == ("ok", 2, 1)
    assert report["dropped_quotes"] == [PARAPHRASE["evidence_quote"]]


def test_truncation_matches_the_extractor(tmp_path):
    long = CONTENT + " x" * 20000
    assert ae._truncate(long).endswith("[... truncated for LLM context ...]")
    assert ae._truncate(CONTENT) == CONTENT


def test_instructions_carry_the_extractor_rules():
    text = ae.INSTRUCTIONS.format(system=ae._SYSTEM_PROMPT.strip())
    assert "VERBATIM" in text and "crawler/extractions/<pmid>.json" in text
