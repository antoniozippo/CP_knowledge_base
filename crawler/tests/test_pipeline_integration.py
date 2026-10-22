# crawler/tests/test_pipeline_integration.py
# End-to-end: ExtractionResult -> EntityMatcher -> GraphUpdater -> saved graph.

import json
import shutil
from pathlib import Path

import pytest

from crawler.extractor import ExtractedEntity, ExtractedRelationship, ExtractionResult
from crawler.matcher import EntityMatch, EntityMatcher
from crawler.updater import GraphUpdater

REAL_GRAPH = Path("graphify-out/graph_v2.json")
PMID = "99999901"
NEW_ENTITY = "Zorblax-9"


@pytest.fixture
def graph_copy(tmp_path):
    target = tmp_path / "graph_v2.json"
    shutil.copy(REAL_GRAPH, target)
    return target


@pytest.fixture
def extraction():
    return ExtractionResult(
        pmid=PMID,
        title="Synthetic paper",
        entities=[
            ExtractedEntity(name="KCC2", entity_type="channel", compartment="dorsal_horn"),
            ExtractedEntity(name="BDNF Val66Met Polymorphism", entity_type="concept"),
            ExtractedEntity(name=NEW_ENTITY, entity_type="molecule", compartment="DRG"),
        ],
        relationships=[
            ExtractedRelationship(
                subject="BDNF Val66Met Polymorphism",
                predicate="downregulates",
                object="KCC2",
                sign=-1,
                evidence_quote="Val66Met carriers showed reduced KCC2.",
                confidence="HIGH",
            ),
        ],
    )


def _run_pipeline(graph_copy, extraction):
    matcher = EntityMatcher(graph_path=str(graph_copy))
    entity_matches, edge_matches = matcher.match_batch([extraction])
    updater = GraphUpdater(graph_path=str(graph_copy))
    report = updater.update(entity_matches, edge_matches, [extraction])
    updater.save()
    return report, entity_matches, edge_matches, json.loads(graph_copy.read_text())


def test_matcher_output_feeds_updater_without_error(graph_copy, extraction):
    report, _, _, _ = _run_pipeline(graph_copy, extraction)
    assert report.new_nodes == 1
    assert report.new_edges == 1


def test_new_entity_saved_with_provenance(graph_copy, extraction):
    _, _, _, saved = _run_pipeline(graph_copy, extraction)
    crawled = [n for n in saved["nodes"] if n.get("contributor") == "auto_crawler"]
    assert [n["label"] for n in crawled] == [NEW_ENTITY]
    assert crawled[0]["source_pmid"] == PMID
    assert crawled[0]["compartment"] == "DRG"


def test_new_edge_saved_between_matched_nodes_with_provenance(graph_copy, extraction):
    _, entity_matches, _, saved = _run_pipeline(graph_copy, extraction)
    ids = {m.extracted_name: m.matched_node_id for m in entity_matches}
    new_edges = [link for link in saved["links"] if link.get("origin") == "auto_crawled"]
    assert len(new_edges) == 1
    edge = new_edges[0]
    assert edge["source"] == ids["BDNF Val66Met Polymorphism"]
    assert edge["target"] == ids["KCC2"]
    assert edge["relation"] == "downregulates"
    assert edge["sign"] == -1
    assert edge["source_pmid"] == PMID
    assert edge["quote"] == "Val66Met carriers showed reduced KCC2."
    assert edge["validation_status"] == "UNREVIEWED"


def test_alias_status_resolves_to_existing_node_without_duplicate(graph_copy):
    updater = GraphUpdater(graph_path=str(graph_copy))
    target = next(n for n in updater.nodes if n["id"] == "BDNF_TrkB_KCC2")
    match = EntityMatch(
        extracted_name="SLC12A5",
        status="ALIAS",
        matched_node_id=target["id"],
        matched_label=target["label"],
        confidence=0.9,
    )
    before = len(updater.nodes)
    report = updater.update([match], [], [])
    assert report.new_nodes == 0
    assert len(updater.nodes) == before


def test_novel_entity_sharing_generic_token_is_not_merged(graph_copy):
    matcher = EntityMatcher(graph_path=str(graph_copy))
    result = matcher.match_entity("Zorblax-9 kinase")
    assert result.status == "NO_MATCH"
