"""Endpoint resolution tests: dangling link endpoints must be resolved to
card-producing (document) node ids — exact, then case-insensitive, then
norm_label fallback — or dropped and counted in the build stats/manifest.
"""

import json

import simulator.build_cards as bc
from simulator.tests.test_build_cards import _node


def _endpoint_fixture(tmp_path):
    nodes = [
        _node("DOC_Alpha", "Alpha Document", tier="mid", source_file="A.md"),
        _node("Doc_Beta", "Beta Thing", entity_type="structure", tier="mid",
              source_file="B.md"),
        _node("doc_gamma", "Gamma Doc", tier="mid", source_file="G.md"),
        _node("doc_alpha", "Alpha Rationale Note", file_type="rationale",
              tier="peripheral", community=0),
        _node("rat_norm", "Beta Thing", file_type="rationale",
              tier="peripheral", community=0),
        _node("lost_cause", "Lost Cause Rationale", file_type="rationale",
              tier="peripheral", community=0),
    ]
    links = [
        {"source": "doc_alpha", "target": "Doc_Beta", "relation": "drives",
         "sign": 1, "confidence": "EXTRACTED"},
        {"source": "rat_norm", "target": "DOC_Alpha", "relation": "supports",
         "sign": 1, "confidence": "EXTRACTED"},
        {"source": "lost_cause", "target": "DOC_Alpha", "relation": "modulates",
         "sign": -1, "confidence": "EXTRACTED"},
        {"source": "Doc_Beta", "target": "lost_cause", "relation": "increases",
         "sign": 1, "confidence": "EXTRACTED"},
        {"source": "Doc_Beta", "target": "doc_gamma", "relation": "activates",
         "sign": 1, "confidence": "EXTRACTED"},
    ]
    (tmp_path / "graph.json").write_text(json.dumps({"nodes": nodes, "links": links}))
    (tmp_path / "claims.json").write_text(json.dumps([]))
    (tmp_path / "verdicts.json").write_text(json.dumps([]))
    return tmp_path


def load(root):
    return (
        json.loads((root / "graph.json").read_text()),
        json.loads((root / "claims.json").read_text()),
        json.loads((root / "verdicts.json").read_text()),
    )


def card_by_id(cards, card_id):
    return next(c for c in cards if c.id == card_id)


def test_case_insensitive_id_resolution_for_inbound_source(tmp_path):
    graph, claims, verdicts = load(_endpoint_fixture(tmp_path))
    cards, stats = bc.build_cards(graph, claims, verdicts)
    sources = [e.source_id for e in card_by_id(cards, "Doc_Beta").inbound_edges]
    assert "doc_alpha" not in sources
    assert "DOC_Alpha" in sources


def test_norm_label_fallback_resolves_to_document_card(tmp_path):
    graph, claims, verdicts = load(_endpoint_fixture(tmp_path))
    cards, stats = bc.build_cards(graph, claims, verdicts)
    sources = [e.source_id for e in card_by_id(cards, "DOC_Alpha").inbound_edges]
    assert "rat_norm" not in sources
    assert "Doc_Beta" in sources


def test_truly_unknown_endpoints_dropped_and_counted(tmp_path):
    graph, claims, verdicts = load(_endpoint_fixture(tmp_path))
    cards, stats = bc.build_cards(graph, claims, verdicts)
    assert [e.source_id for e in card_by_id(cards, "DOC_Alpha").inbound_edges] == ["Doc_Beta"]
    assert "lost_cause" not in card_by_id(cards, "Doc_Beta").outbound_ids
    assert stats["unresolved_endpoint_drops"] == 2


def test_manifest_reports_unresolved_endpoint_drops(tmp_path):
    graph, claims, verdicts = load(_endpoint_fixture(tmp_path))
    cards, stats = bc.build_cards(graph, claims, verdicts)
    entries = bc.write_cards(cards, tmp_path / "out")
    manifest = bc.build_manifest(entries, "sha", stats, cards)
    assert manifest["unresolved_endpoint_drops"] == 2
