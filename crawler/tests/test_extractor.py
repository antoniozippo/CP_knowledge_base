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


def test_direction_verbs_supply_a_missing_sign_others_keep_it():
    q = "TNF-alpha strongly reduced KCC2 expression"
    verified, stats = ex.verify_relationships(result(
        rel(q, predicate="downregulates", sign=0),
        rel(q, predicate="modulates", sign=-1),
        rel(q, predicate="binds", sign=5),
    ), CONTENT)
    assert [(r.predicate, r.sign) for r in verified.relationships] == [("downregulates", -1), ("modulates", -1), ("binds", 1)]
    assert stats["sign_overridden"] == 2 and stats["verb_replaced"] == 0


def test_a_sign_that_contradicts_its_verb_wins_and_the_verb_becomes_modulates():
    # "Loss-of-function mutations in Nav1.7 cause CIP" is extracted as causes, -1; "RTX depleted
    # CGRP" as releases, -1. The sign is the net effect the prompt asks for, so it is kept.
    q = "TNF-alpha strongly reduced KCC2 expression"
    verified, stats = ex.verify_relationships(result(
        rel(q, predicate="causes", sign=-1),
        rel(q, predicate="prevents", sign=1),
        rel(q, predicate="inhibits", sign=-1),          # agrees: unchanged
    ), CONTENT)
    assert [(r.predicate, r.sign) for r in verified.relationships] == [("modulates", -1), ("modulates", 1), ("inhibits", -1)]
    assert stats["verb_replaced"] == 2 and stats["sign_overridden"] == 0


def test_normalize_sign_clamps_and_keeps_free_predicates():
    assert ex.normalize_sign("binds", 3) == ("binds", 1)
    assert ex.normalize_sign("Activates", 0) == ("Activates", 1)
    assert ex.normalize_sign("activates", -1) == ("modulates", -1)


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


def test_quotes_match_across_inline_markup_in_the_source():
    content = "Infiltrating CD8<sup>+</sup> T cells rose (<i>P</i> < 0.05) after SNI."
    verified, stats = ex.verify_relationships(result(
        rel("Infiltrating CD8+ T cells rose (P < 0.05) after SNI"),
        rel("Infiltrating CD8<sup>+</sup> T cells rose"),
    ), content)
    assert len(verified.relationships) == 2 and stats["dropped_unverified"] == 0


# ---------------------------------------------------------------- combination experiments

COMBO_CONTENT = ("Results: MCC950 reduced mechanical allodynia in wild-type mice after CCI, but MCC950 had no "
                 "effect on allodynia in Nlrp3-/- mice. Co-administration of gabapentin and morphine produced "
                 "a synergistic reduction of allodynia.")


def combo(**kw):
    base = {"interventions": [{"agent": "MCC950", "target": "NLRP3", "action": "loss"},
                              {"agent": "Nlrp3-/- mice", "target": "NLRP3", "action": "loss"}],
            "readout": "mechanical allodynia", "readout_direction": -1, "singles": [-1, -1],
            "interaction": "occlusion", "interaction_basis": "stated", "model": "CCI", "species": "mouse",
            "evidence_quote": "MCC950 had no effect on allodynia in Nlrp3-/- mice"}
    base.update(kw)
    return base


def test_a_combination_record_is_coerced_to_the_schema():
    c = ex.parse_combination(combo(interaction="Sub-additive", readout_direction=5, singles=[-1],
                                   interventions=[{"agent": "A", "action": "Inhibitor"}, {"agent": "B", "action": "gain"}]))
    assert c.interaction == "sub_additive" and c.readout_direction == 1
    assert c.singles == [-1, 0]                                  # padded to one per intervention
    assert [i.action for i in c.interventions] == ["unspecified", "gain"]
    assert ex.parse_combination(combo(interaction="strongly synergistic")).interaction == "unclear"


def test_a_combination_needs_two_interventions_a_readout_and_a_quote():
    assert ex.parse_combination(combo(interventions=[{"agent": "MCC950"}])) is None
    assert ex.parse_combination(combo(readout="")) is None
    assert ex.parse_combination(combo(evidence_quote="")) is None
    assert ex.parse_combination("not a record") is None


def test_combination_quotes_are_verified_like_relationships():
    raw = {"pmid": "7", "title": "t", "entities": [], "relationships": [], "combinations": [
        combo(), combo(interaction="synergy", evidence_quote="Co-administration of gabapentin and morphine produced a synergistic reduction of allodynia"),
        combo(evidence_quote="MCC950 needs NLRP3 to relieve pain in knockout mice")]}       # paraphrase
    result = ex.LLMExtractor()._validate_result(raw)
    verified, stats = ex.verify_relationships(result, COMBO_CONTENT)
    assert [c.interaction for c in verified.combinations] == ["occlusion", "synergy"]
    assert stats["combinations_dropped_unverified"] == 1
    assert all(c.pmid == "7" for c in verified.combinations)


def test_old_extractions_without_combinations_still_load():
    result = ex.LLMExtractor()._validate_result({"pmid": "1", "entities": [], "relationships": []})
    assert result.combinations == []


def test_the_prompt_asks_for_combinations_and_defines_the_classes():
    for word in ("COMBINATION EXPERIMENTS", "occlusion", "synergy", "sub_additive", "no_added_effect", "antagonism"):
        assert word in ex._SYSTEM_PROMPT
    assert '"combinations"' in ex._USER_PROMPT_TEMPLATE
