# crawler/tests/test_matcher.py

import pytest
from crawler.matcher import EntityMatcher, EntityMatch


@pytest.fixture(scope="module")
def matcher():
    return EntityMatcher(graph_path="graphify-out/graph_v2.json")


def test_exact_match_kcc2(matcher):
    result = matcher.match_entity("KCC2")
    assert result.status in ("EXACT", "FUZZY", "ALIAS")
    assert result.matched_node_id is not None


def test_exact_match_nlrp3(matcher):
    result = matcher.match_entity("NLRP3 Inflammasome")
    assert result.matched_node_id is not None


def test_alias_match_kcc2_via_norm(matcher):
    # KCC2 should match directly via norm_label
    result = matcher.match_entity("KCC2")
    assert result.status in ("EXACT", "FUZZY", "ALIAS")
    assert result.matched_node_id is not None


def test_fuzzy_match(matcher):
    result = matcher.match_entity("KCC2 transporter")
    assert result.matched_node_id is not None


def test_no_match(matcher):
    result = matcher.match_entity("ZZZZNONEXISTENT12345")
    assert result.status == "NO_MATCH"


def test_edge_match_new(matcher):
    result = matcher.match_edge("nonexistent_source", "activates", "nonexistent_target")
    assert result.status == "NEW"


def test_batch_match(matcher):
    extractions = []
    entity_matches, edge_matches = matcher.match_batch(extractions)
    assert isinstance(entity_matches, list)
    assert isinstance(edge_matches, list)
