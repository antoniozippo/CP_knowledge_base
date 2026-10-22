# crawler/tests/test_relation_type.py
# relation_type derivation (matcher) and conflict recording (updater + ConflictManager),
# on a small synthetic graph so the cases do not depend on the real data.

import json

import pytest

from crawler.conflict import ConflictManager
from crawler.matcher import EntityMatcher
from crawler.records import EdgeMatch
from crawler.updater import GraphUpdater


def _node(node_id, label):
    return {"id": node_id, "label": label, "norm_label": label.lower()}


def _link(relation, sign, status=None, source="a", target="b"):
    link = {"source": source, "target": target, "relation": relation, "sign": sign,
            "confidence_score": 0.5}
    if status:
        link["validation_status"] = status
    return link


def _write_graph(tmp_path, links):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({
        "nodes": [_node("a", "Alpha"), _node("b", "Beta")],
        "links": links,
    }))
    return str(path)


def _match(tmp_path, links, predicate="downregulates", sign=-1, subject="a", obj="b"):
    matcher = EntityMatcher(graph_path=_write_graph(tmp_path, links))
    return matcher.match_edge(subject, predicate, obj, sign=sign)


# --- matcher: pair matching and relation_type -------------------------------

def test_same_pair_different_predicate_and_same_sign_confirms(tmp_path):
    m = _match(tmp_path, [_link("inhibits", -1)], predicate="downregulates", sign=-1)
    assert (m.status, m.relation_type, m.existing_edge_index) == ("EXISTS", "CONFIRMS", 0)


def test_opposite_sign_contradicts(tmp_path):
    m = _match(tmp_path, [_link("activates", 1)], predicate="downregulates", sign=-1)
    assert (m.status, m.relation_type) == ("EXISTS", "CONTRADICTS")


def test_unsigned_existing_edge_extended_by_signed_evidence(tmp_path):
    m = _match(tmp_path, [_link("conceptually_related_to", 0)], sign=-1)
    assert (m.status, m.relation_type) == ("EXISTS", "EXTENDS")


def test_unsigned_new_evidence_confirms_without_contradicting(tmp_path):
    m = _match(tmp_path, [_link("activates", 1)], predicate="interacts_with", sign=0)
    assert (m.status, m.relation_type) == ("EXISTS", "CONFIRMS")


def test_prefers_same_predicate_among_several_edges(tmp_path):
    links = [_link("activates", 1), _link("downregulates", -1)]
    m = _match(tmp_path, links, predicate="downregulates", sign=-1)
    assert m.existing_edge_index == 1


def test_prefers_signed_edge_over_unsigned_when_no_predicate_matches(tmp_path):
    links = [_link("conceptually_related_to", 0), _link("activates", 1)]
    m = _match(tmp_path, links, predicate="modulates", sign=1)
    assert (m.existing_edge_index, m.relation_type) == (1, "CONFIRMS")


def test_reverse_direction_only_is_inverse_with_no_relation_type(tmp_path):
    m = _match(tmp_path, [_link("activates", 1, source="b", target="a")])
    assert (m.status, m.relation_type) == ("INVERSE", "")


def test_no_edge_between_pair_is_new_with_no_relation_type(tmp_path):
    m = _match(tmp_path, [])
    assert (m.status, m.relation_type) == ("NEW", "")


# --- updater: conflict recording --------------------------------------------

def _edge_match(relation_type, sign, idx=0, pmid="777", quote="evidence"):
    return EdgeMatch(
        subject_id="a", predicate="downregulates", object_id="b", status="EXISTS",
        existing_edge_index=idx, sign=sign, evidence_quote=quote, source_pmid=pmid,
        relation_type=relation_type,
    )


def _updater(tmp_path, links):
    manager = ConflictManager(conflicts_path=str(tmp_path / "conflicts.yaml"))
    return GraphUpdater(graph_path=_write_graph(tmp_path, links), conflict_manager=manager), manager


def test_contradicting_a_confirmed_edge_records_human_review_conflict(tmp_path):
    updater, manager = _updater(tmp_path, [_link("activates", 1, status="CONFIRMED")])
    report = updater.update([], [_edge_match("CONTRADICTS", -1)], [])

    assert report.conflicts == 1
    (c,) = manager.get_pending()
    assert (c.subject_label, c.object_label) == ("Alpha", "Beta")
    assert (c.current_sign, c.new_sign, c.new_pmid) == (1, -1, "777")
    assert c.new_evidence_quote == "evidence"
    assert c.recommendation == "HUMAN_REVIEW"


def test_conflict_never_changes_the_existing_edge(tmp_path):
    updater, _ = _updater(tmp_path, [_link("activates", 1, status="CONFIRMED")])
    updater.update([], [_edge_match("CONTRADICTS", -1)], [])
    edge = updater.links[0]
    assert (edge["sign"], edge["validation_status"], edge["confidence_score"]) == (1, "CONFIRMED", 0.5)


def test_contradicting_an_unreviewed_edge_is_recorded_as_auto_update(tmp_path):
    updater, manager = _updater(tmp_path, [_link("activates", 1)])
    updater.update([], [_edge_match("CONTRADICTS", -1)], [])
    assert manager.get_pending()[0].recommendation == "AUTO_UPDATE"


def test_supporting_evidence_for_a_refuted_edge_goes_to_human_review(tmp_path):
    updater, manager = _updater(tmp_path, [_link("activates", 1, status="REFUTED")])
    report = updater.update([], [_edge_match("CONFIRMS", 1)], [])

    assert report.conflicts == 1
    assert report.updated_edges == 0
    assert updater.links[0]["validation_status"] == "REFUTED"
    assert manager.get_pending()[0].recommendation == "HUMAN_REVIEW"


def test_confirming_an_unreviewed_edge_bumps_score_without_conflict(tmp_path):
    updater, manager = _updater(tmp_path, [_link("activates", 1)])
    report = updater.update([], [_edge_match("CONFIRMS", 1)], [])

    assert (report.updated_edges, report.conflicts) == (1, 0)
    assert updater.links[0]["validation_status"] == "CONFIRMED"
    assert updater.links[0]["confidence_score"] == pytest.approx(0.55)
    assert manager.get_pending() == []


def test_extends_bumps_score_twice(tmp_path):
    updater, _ = _updater(tmp_path, [_link("conceptually_related_to", 0)])
    updater.update([], [_edge_match("EXTENDS", -1)], [])
    assert updater.links[0]["confidence_score"] == pytest.approx(0.60)


def test_conflicts_are_counted_without_a_conflict_manager(tmp_path):
    updater = GraphUpdater(graph_path=_write_graph(tmp_path, [_link("activates", 1, status="CONFIRMED")]))
    report = updater.update([], [_edge_match("CONTRADICTS", -1)], [])
    assert report.conflicts == 1


def test_same_conflict_is_not_recorded_twice(tmp_path):
    updater, manager = _updater(tmp_path, [_link("activates", 1, status="CONFIRMED")])
    updater.update([], [_edge_match("CONTRADICTS", -1)], [])
    updater.update([], [_edge_match("CONTRADICTS", -1)], [])
    assert len(manager.conflicts) == 1
