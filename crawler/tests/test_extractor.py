# crawler/tests/test_extractor.py - reply parsing, content budget, relationship verification

import json

from crawler import extractor as ex
from crawler.extractor import ExtractedEntity, ExtractedRelationship, ExtractionResult


def rel(quote, predicate="downregulates", sign=0, subject="TNF", obj="KCC2"):
    return ExtractedRelationship(subject=subject, predicate=predicate, object=obj,
                                 sign=sign, evidence_quote=quote)


def result(*rels):
    return ExtractionResult(pmid="1", title="t", entities=[ExtractedEntity(name="TNF")],
                            relationships=list(rels))


CONTENT = "Results: TNF-alpha strongly reduced KCC2 expression in the dorsal horn (p<0.01)."


def test_parse_json_object_tolerates_think_blocks_and_fences():
    assert ex.parse_json_object('<think>reasoning {not json}</think>\n```json\n{"a": 1}\n```') == {"a": 1}
    assert ex.parse_json_object("<thought>x</thought>{\"a\": [1]}") == {"a": [1]}
    assert ex.parse_json_object("no object here") is None
    assert ex.parse_json_object("[1, 2]") is None


def test_quote_must_occur_in_content_ignoring_case_and_punctuation():
    verified, stats = ex.verify_relationships(result(
        rel("tnf alpha strongly reduced KCC2 expression in the dorsal horn"),   # kept
        rel("TNF-alpha lowers KCC2 in spinal cord neurons"),                    # paraphrase
        rel("reduced"),                                                          # too short
    ), CONTENT)
    assert [r.evidence_quote for r in verified.relationships] == [
        "tnf alpha strongly reduced KCC2 expression in the dorsal horn"]
    assert stats["dropped_unverified"] == 2


def test_fixed_direction_predicates_set_the_sign_others_keep_it():
    q = "TNF-alpha strongly reduced KCC2 expression"
    verified, stats = ex.verify_relationships(result(
        rel(q, predicate="downregulates", sign=1),
        rel(q, predicate="modulates", sign=-1),
        rel(q, predicate="binds", sign=5),
    ), CONTENT)
    assert [r.sign for r in verified.relationships] == [-1, -1, 1]
    assert stats["sign_overridden"] == 2


def test_relationship_endpoints_added_to_entities():
    verified, _ = ex.verify_relationships(result(rel("TNF-alpha strongly reduced KCC2 expression")), CONTENT)
    assert [e.name for e in verified.entities] == ["TNF", "KCC2"]
    assert verified.relationships[0].pmid == "1"


def test_single_content_budget_and_cached_results_reverified(tmp_path, monkeypatch):
    prompts = []
    reply = {"entities": [], "relationships": [
        {"subject": "TNF", "predicate": "inhibits", "object": "KCC2", "sign": 0,
         "evidence_quote": "TNF-alpha strongly reduced KCC2 expression"},
        {"subject": "TNF", "predicate": "inhibits", "object": "KCC2", "sign": 0,
         "evidence_quote": "invented sentence that is nowhere in the paper"},
    ]}
    monkeypatch.setattr(ex.LLMExtractor, "_call_llm",
                        lambda self, prompt: prompts.append(prompt) or json.loads(json.dumps(reply)))
    e = ex.LLMExtractor(cache_dir=tmp_path)
    for size in (9_000, 29_000, 31_000):
        content = CONTENT + " " + "x" * size
        e.extract(str(size), "t", content)
    sent = [p.split("Content:\n", 1)[1].split("\n\nReturn a JSON object")[0] for p in prompts]
    assert all(len(c) <= ex.MAX_CONTENT_CHARS + 60 for c in sent)
    assert "truncated" not in sent[0] and "truncated" in sent[1] and "truncated" in sent[2]

    again = e.extract("9000", "t", CONTENT + " " + "x" * 9_000, max_budget=1)  # cache hit, budget spent
    assert len(prompts) == 3
    assert [r.sign for r in again.relationships] == [-1]
    assert e.dropped_unverified == 4
