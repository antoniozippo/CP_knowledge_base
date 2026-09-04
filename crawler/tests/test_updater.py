# crawler/tests/test_updater.py

import pytest
import json
from pathlib import Path
from crawler.updater import GraphUpdater, UpdateReport


@pytest.fixture(scope="module")
def updater():
    return GraphUpdater(graph_path="graphify-out/graph_v2.json")


def test_updater_loads_graph(updater):
    assert len(updater.nodes) > 500
    assert len(updater.links) > 900


def test_classify_entity_type(updater):
    assert updater._classify_entity_type("TNF-alpha", "molecule") == "molecule"
    assert updater._classify_entity_type("Nav1.7", "channel") == "channel"
    assert updater._classify_entity_type("Microglia", "cell_type") == "cell_type"
    assert updater._classify_entity_type("Fasudil", "drug") == "drug"


def test_add_node(updater):
    node = updater.add_node(
        name="TestCrawlerNode",
        entity_type="molecule",
        compartment="dorsal_horn",
        source_pmid="99999999",
    )
    assert node["id"].startswith("CRAWLED_") or node["id"].startswith("testcrawler")
    assert node["entity_type"] == "molecule"
    assert node["compartment"] == "dorsal_horn"


def test_add_edge(updater):
    edge = updater.add_edge(
        subject_id="nonexistent1",
        predicate="activates",
        object_id="nonexistent2",
        sign=1,
        evidence_quote="Test evidence",
        source_pmid="99999999",
    )
    assert edge["origin"] == "auto_crawled"
    assert edge["sign"] == 1
    assert edge["validation_status"] == "UNREVIEWED"


def test_conflict_detection(updater):
    # Use a real edge from the graph to test conflict detection
    if len(updater.links) == 0:
        pytest.skip("No edges in graph")
    edge = updater.links[0]
    existing_sign = edge.get("sign", 0)
    # If existing sign is non-zero, test with opposite sign
    if existing_sign != 0:
        new_sign = -existing_sign
        conflict = updater.detect_conflict(edge_index=0, new_sign=new_sign, new_pmid="99999999")
        assert conflict is not None
        assert conflict["edge_index"] == 0
    else:
        # sign=0 means neutral, no conflict possible
        conflict = updater.detect_conflict(edge_index=0, new_sign=1, new_pmid="99999999")
        assert conflict is None


def test_no_conflict_same_sign(updater):
    if len(updater.links) == 0:
        pytest.skip("No edges in graph")
    edge = updater.links[0]
    existing_sign = edge.get("sign", 0)
    conflict = updater.detect_conflict(edge_index=0, new_sign=existing_sign, new_pmid="99999999")
    assert conflict is None


def test_conflict_out_of_bounds(updater):
    conflict = updater.detect_conflict(edge_index=999999, new_sign=-1, new_pmid="99999999")
    assert conflict is None


def test_update_report():
    report = UpdateReport()
    assert report.new_nodes == 0
    assert report.new_edges == 0
