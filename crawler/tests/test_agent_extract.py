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


def test_check_reports_combinations_kept_dropped_and_malformed(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "EXTRACTIONS_DIR", tmp_path)
    content = CONTENT + " Gabapentin had no further effect in KCC2 knockdown rats."
    good = {"interventions": [{"agent": "gabapentin"}, {"agent": "KCC2 knockdown", "action": "loss"}],
            "readout": "allodynia", "interaction": "occlusion",
            "evidence_quote": "Gabapentin had no further effect in KCC2 knockdown rats"}
    write_extraction(tmp_path, "1", [GOOD])
    data = json.loads((tmp_path / "1.json").read_text())
    data["combinations"] = [good, {**good, "evidence_quote": "gabapentin needs KCC2"}, {**good, "interventions": [{"agent": "x"}]}]
    (tmp_path / "1.json").write_text(json.dumps(data))
    report = ae.check_extraction("1", content)
    assert (report["combinations"], report["combinations_kept"], report["combinations_malformed"]) == (2, 1, 1)
    assert "gabapentin needs KCC2" in report["dropped_quotes"]


def test_instructions_mention_combinations():
    assert "`combinations`" in ae.INSTRUCTIONS


# ---------------------------------------------------------------- the combinations pass

COMBO = {"interventions": [{"agent": "minocycline", "action": "drug"}, {"agent": "Cx3cr1-/-", "action": "loss"}],
         "readout": "mechanical allodynia", "interaction": "occlusion",
         "evidence_quote": "TNF-alpha strongly reduced KCC2 expression"}


def test_check_combinations_reads_the_separate_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(ae, "COMBINATIONS_DIR", tmp_path)
    (tmp_path / "1.json").write_text(json.dumps({"pmid": "1", "pass": "combinations", "combinations": [
        COMBO, {**COMBO, "evidence_quote": "an invented sentence"}, {**COMBO, "interventions": [{"agent": "x"}]}]}))
    (tmp_path / "2.json").write_text(json.dumps({"pmid": "2", "pass": "combinations", "combinations": []}))
    (tmp_path / "3.json").write_text(json.dumps({"pmid": "3", "relationships": []}))
    report = ae.check_combinations("1", CONTENT)
    assert (report["combinations"], report["combinations_kept"], report["combinations_malformed"]) == (2, 1, 1)
    assert report["dropped_quotes"] == ["an invented sentence"]
    assert ae.check_combinations("2", CONTENT) == {"pmid": "2", "status": "ok", "combinations": 0,
                                                   "combinations_kept": 0, "dropped_quotes": []}
    assert ae.check_combinations("3", CONTENT)["status"] == "schema_error"
    assert ae.check_combinations("4", CONTENT)["status"] == "missing"


def test_wrapping_keeps_lines_readable_and_quotes_verifiable():
    line = ("TNF-alpha strongly reduced KCC2 expression in the dorsal horn. " * 60).strip()
    wrapped = ae._wrap("Title\n\n" + line, width=200)
    assert max(len(x) for x in wrapped.split("\n")) <= 200
    assert wrapped.startswith("Title\n\n")
    assert " ".join(wrapped.split()) == " ".join(("Title " + line).split())


def test_combination_wording_finds_experiments_and_skips_plain_text():
    hits = ["Co-administration of A and B", "the drugs acted synergistically",
            "in Nlrp3-/- mice the drug failed to reduce allodynia", "naloxone reversed the analgesic effect of EA"]
    assert all(ae.COMBINATION_WORDING.search(t) for t in hits)
    assert not ae.COMBINATION_WORDING.search("TNF-alpha reduced KCC2 expression after nerve injury")


def test_combination_prompt_and_instructions_ask_only_for_combinations():
    from crawler.extractor import build_combination_prompt
    prompt = build_combination_prompt("CONTENT", "1", "T")
    assert "COMBINATION EXPERIMENTS:" in prompt and '"combinations"' in prompt
    assert '"relationships"' not in prompt and "as above" not in prompt
    text = ae.COMBO_INSTRUCTIONS.format(system=ae._COMBINATION_SYSTEM_PROMPT.strip())
    assert "crawler/extractions/combinations/<pmid>.json" in text and "check --combinations" in text
