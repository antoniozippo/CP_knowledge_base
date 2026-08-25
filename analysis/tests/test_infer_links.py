"""Tests for infer_links: structural novel-edge candidates (co-occurrence + signed triads)."""

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "analysis" / "scripts" / "infer_links.py"
REAL_GRAPH = REPO_ROOT / "graphify-out" / "graph_v2.json"

sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import infer_links as il  # noqa: E402


def make_node(node_id, label, community, entity_type="concept", compartment="other", tier="mid"):
    return {
        "label": label,
        "file_type": "document",
        "source_file": f"{node_id}.md",
        "source_location": None,
        "community": community,
        "norm_label": label.lower(),
        "id": node_id,
        "entity_type": entity_type,
        "compartment": compartment,
        "tier": tier,
    }


def make_link(source, target, sign=0, confidence_score=1.0):
    return {
        "relation": "conceptually_related_to",
        "confidence": "EXTRACTED",
        "confidence_score": confidence_score,
        "source_file": "fixture.md",
        "source_location": None,
        "weight": 1.0,
        "source": source,
        "target": target,
        "sign": sign,
    }


@pytest.fixture
def cooccur_graph():
    """Hand-computable co-occurrence fixture.

    Undirected projection: a-z1, b-z1, a-z2, c-z2.
    Gamma(a)={z1,z2}, Gamma(c)={z2} -> common={z2}, deg(z2)=2.
      adamic_adar(a,c) = 1/ln(2); jaccard(a,c) = 1/2.
    """
    nodes = [
        make_node("a", "Alpha", 0, entity_type="molecule"),
        make_node("b", "Beta", 0),
        make_node("c", "Gamma Node", 1, entity_type="receptor"),
        make_node("z1", "Shared One", 2),
        make_node("z2", "Shared Two", 2),
        make_node("m1", "Triad One", 3),
        make_node("m2", "Triad Mid", 4),
        make_node("m3", "Triad Three", 5),
    ]
    links = [
        make_link("a", "z1"),
        make_link("z1", "b"),
        make_link("a", "z2"),
        make_link("c", "z2"),
        make_link("m1", "m2", sign=1),
        make_link("m2", "m3", sign=1),
    ]
    return {"directed": True, "multigraph": True, "nodes": nodes, "links": links}


# ---------------------------------------------------------------------------
# normalize_label / near-duplicate handling
# ---------------------------------------------------------------------------


def test_normalize_label_strips_parentheticals_and_case():
    assert il.normalize_label("BDNF (brain-derived neurotrophic factor)") == "bdnf"
    assert il.normalize_label("  PV   Interneurons! ") == "pv interneurons"


def test_near_duplicate_labels_excluded(cooccur_graph):
    g = copy.deepcopy(cooccur_graph)
    g["nodes"].append(make_node("dup_a", "TrkB (full name)", 3))
    g["nodes"].append(make_node("dup_b", "trkb", 4))
    # dup_a - h - dup_b: structurally the strongest possible candidate.
    g["links"].append(make_link("dup_a", "h"))
    g["links"].append(make_link("h", "dup_b"))

    cands = il.infer_cooccurrence_candidates(g["nodes"], g["links"], top_n=50)
    offending = [
        c for c in cands if {c["node_a"], c["node_b"]} == {"dup_a", "dup_b"}
    ]
    assert offending == []


# ---------------------------------------------------------------------------
# Co-occurrence candidates
# ---------------------------------------------------------------------------


def test_no_existing_link_pairs_proposed(cooccur_graph):
    existing = {
        frozenset((l["source"], l["target"])) for l in cooccur_graph["links"]
    }
    cands = il.infer_cooccurrence_candidates(
        cooccur_graph["nodes"], cooccur_graph["links"], top_n=100
    )
    for c in cands:
        assert frozenset((c["node_a"], c["node_b"])) not in existing


def test_adamic_adar_and_jaccard_hand_computed(cooccur_graph):
    cands = il.infer_cooccurrence_candidates(
        cooccur_graph["nodes"], cooccur_graph["links"], top_n=100
    )
    ac = [
        c for c in cands if {c["node_a"], c["node_b"]} == {"a", "c"}
    ]
    assert len(ac) == 1
    rec = ac[0]
    assert rec["adamic_adar"] == pytest.approx(1.0 / math.log(2))
    assert rec["jaccard"] == pytest.approx(0.5)
    assert rec["shared_neighbors"] == ["Shared Two"]
    assert rec["evidence_basis"] == "structure"
    # metadata propagation + endpoint canonicalisation
    assert {rec["community_a"], rec["community_b"]} == {0, 1}
    assert {rec["entity_type_a"], rec["entity_type_b"]} == {"molecule", "receptor"}
    assert "tier_a" in rec and "compartment_a" in rec


def test_cross_community_restriction():
    nodes = [
        make_node("p", "P", 5),
        make_node("q", "Q", 5),
        make_node("r", "R", 6),
        make_node("u", "U", 7),
        make_node("v", "V", 7),
    ]
    links = [
        make_link("p", "u"),
        make_link("p", "v"),
        make_link("q", "u"),
        make_link("q", "v"),
        make_link("r", "u"),
        make_link("r", "v"),
    ]
    cands = il.infer_cooccurrence_candidates(nodes, links, top_n=100)
    pairs = [frozenset((c["node_a"], c["node_b"])) for c in cands]
    # (p,q): identical structure to (p,r) but same community -> excluded.
    assert frozenset(("p", "q")) not in pairs
    assert frozenset(("p", "r")) in pairs
    pr = next(c for c in cands if {c["node_a"], c["node_b"]} == {"p", "r"})
    assert pr["jaccard"] == pytest.approx(1.0)
    assert pr["adamic_adar"] == pytest.approx(2.0 / math.log(3))
    # every proposed pair is genuinely cross-community
    assert all(c["community_a"] != c["community_b"] for c in cands)


def test_shared_neighbors_capped_at_eight():
    nodes = [
        make_node("p", "P", 0),
        make_node("q", "Q", 1),
    ] + [make_node(f"s{i}", f"S{i}", 2) for i in range(10)]
    links = [make_link("p", f"s{i}") for i in range(10)]
    links += [make_link("q", f"s{i}") for i in range(10)]
    cands = il.infer_cooccurrence_candidates(nodes, links, top_n=10)
    pq = [c for c in cands if {c["node_a"], c["node_b"]} == {"p", "q"}]
    assert len(pq) == 1
    assert len(pq[0]["shared_neighbors"]) == 8


def test_top_n_limit_respected(cooccur_graph):
    cands = il.infer_cooccurrence_candidates(
        cooccur_graph["nodes"], cooccur_graph["links"], top_n=2
    )
    assert len(cands) <= 2


# ---------------------------------------------------------------------------
# Signed triad closure
# ---------------------------------------------------------------------------


def _triad_nodes():
    return [
        make_node("a", "A", 0),
        make_node("b", "B", 1),
        make_node("c", "C", 2),
    ]


def test_triad_plus_times_plus_is_positive():
    nodes = _triad_nodes()
    links = [make_link("a", "b", sign=1), make_link("b", "c", sign=1)]
    cands = il.infer_triad_candidates(nodes, links)
    assert len(cands) == 1
    rec = cands[0]
    assert {rec["node_a"], rec["node_c"]} == {"a", "c"}
    assert rec["inferred_sign"] == 1
    assert rec["evidence_basis"] == "triad"


def test_triad_minus_times_minus_is_positive():
    nodes = _triad_nodes()
    links = [make_link("a", "b", sign=-1), make_link("b", "c", sign=-1)]
    cands = il.infer_triad_candidates(nodes, links)
    assert len(cands) == 1
    assert cands[0]["inferred_sign"] == 1


def test_triad_plus_times_minus_is_negative():
    nodes = _triad_nodes()
    links = [make_link("a", "b", sign=1), make_link("b", "c", sign=-1)]
    cands = il.infer_triad_candidates(nodes, links)
    assert len(cands) == 1
    assert cands[0]["inferred_sign"] == -1


def test_triad_zero_sign_links_ignored():
    nodes = _triad_nodes()
    links = [make_link("a", "b", sign=0), make_link("b", "c", sign=0)]
    assert il.infer_triad_candidates(nodes, links) == []


def test_triad_existing_link_between_endpoints_excluded():
    nodes = _triad_nodes()
    links = [
        make_link("a", "b", sign=1),
        make_link("b", "c", sign=1),
        make_link("a", "c", sign=0),  # already linked -> no candidate
    ]
    assert il.infer_triad_candidates(nodes, links) == []


def test_triad_support_aggregation_and_caps():
    nodes = [make_node("a", "A", 0), make_node("c", "C", 1)]
    nodes += [make_node(f"v{i}", f"V{i}", 2) for i in range(6)]
    links = []
    for i in range(6):
        links.append(make_link("a", f"v{i}", sign=1))
        links.append(make_link(f"v{i}", "c", sign=1, confidence_score=0.3))
    cands = il.infer_triad_candidates(nodes, links)
    assert len(cands) == 1
    rec = cands[0]
    assert rec["n_support"] == 6
    assert len(rec["support_paths"]) == 5  # hard cap
    assert rec["inferred_sign"] == 1
    assert rec["min_confidence"] == pytest.approx(0.3)
    for sp in rec["support_paths"]:
        assert set(sp.keys()) == {"via", "s1", "s2"}
        assert sp["s1"] == 1 and sp["s2"] == 1


def test_triad_n_support_counts_distinct_intermediates():
    nodes = _triad_nodes()
    links = [
        make_link("a", "b", sign=1),
        make_link("b", "c", sign=1),
        # reverse orientation through the SAME intermediate -> not new support
        make_link("c", "b", sign=1),
        make_link("b", "a", sign=1),
    ]
    cands = il.infer_triad_candidates(nodes, links)
    assert len(cands) == 1
    assert cands[0]["n_support"] == 1


def test_triad_mixed_sign_support_majority_wins():
    nodes = [make_node("a", "A", 0), make_node("c", "C", 1)]
    nodes += [make_node(nid, nid.upper(), 2) for nid in ("b1", "b2", "b3")]
    links = [
        make_link("a", "b1", sign=1),
        make_link("b1", "c", sign=1),  # +x+ = +
        make_link("a", "b2", sign=-1),
        make_link("b2", "c", sign=-1),  # -x- = +
        make_link("a", "b3", sign=1),
        make_link("b3", "c", sign=-1),  # +x- = -
    ]
    cands = il.infer_triad_candidates(nodes, links)
    assert len(cands) == 1
    rec = cands[0]
    assert rec["inferred_sign"] == 1  # 2 supporting paths vs 1
    assert rec["n_support"] == 2


def test_triad_near_duplicate_labels_excluded():
    nodes = [
        make_node("x1", "GABA (acid)", 0),
        make_node("x2", "gaba", 1),
        make_node("m", "Mid", 2),
    ]
    links = [
        make_link("x1", "m", sign=1),
        make_link("m", "x2", sign=1),
    ]
    assert il.infer_triad_candidates(nodes, links) == []


# ---------------------------------------------------------------------------
# Output assembly, determinism, CLI
# ---------------------------------------------------------------------------


def test_determinism_same_input_same_output(cooccur_graph):
    g = copy.deepcopy(cooccur_graph)
    out1 = il.build_output(g, top_cooccur=20, top_triad=20, source_graph="fixture.json")
    out2 = il.build_output(copy.deepcopy(g), top_cooccur=20, top_triad=20, source_graph="fixture.json")
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_cli_runs_on_fixture_and_assigns_stable_ids(tmp_path, cooccur_graph):
    graph_path = tmp_path / "g.json"
    graph_path.write_text(json.dumps(cooccur_graph))
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"

    for out_path in (out1, out2):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--graph", str(graph_path), "--output", str(out_path)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "Co-occurrence" in proc.stdout
        assert "triad" in proc.stdout.lower()

    data1 = json.loads(out1.read_text())
    data2 = json.loads(out2.read_text())
    assert out1.read_bytes() == out2.read_bytes()  # deterministic

    assert data1["summary"]["n_cooccurrence_candidates"] >= 1
    assert data1["summary"]["n_triad_candidates"] >= 1
    lc_ids = [c["id"] for c in data1["cooccurrence_candidates"]]
    tc_ids = [c["id"] for c in data1["triad_candidates"]]
    assert lc_ids == [f"LC-{i:04d}" for i in range(1, len(lc_ids) + 1)]
    assert tc_ids == [f"TC-{i:04d}" for i in range(1, len(tc_ids) + 1)]


@pytest.mark.skipif(not REAL_GRAPH.exists(), reason="real graph not present")
def test_real_graph_smoke(tmp_path):
    out_path = tmp_path / "real_out.json"
    rc = il.main(["--graph", str(REAL_GRAPH), "--output", str(out_path)])
    assert rc == 0
    data = json.loads(out_path.read_text())

    n_co = len(data["cooccurrence_candidates"])
    n_tc = len(data["triad_candidates"])
    assert n_co == data["summary"]["n_cooccurrence_candidates"]
    assert n_tc == data["summary"]["n_triad_candidates"]

    node_ids = set()
    for cand_class in ("cooccurrence_candidates", "triad_candidates"):
        for rec in data[cand_class]:
            node_ids.update({rec["node_a"], rec.get("node_b") or rec["node_c"]})
            assert rec["evidence_basis"] in ("structure", "triad")

    graph_ids = {n["id"] for n in json.loads(REAL_GRAPH.read_text())["nodes"]}
    assert node_ids <= graph_ids

    for rec in data["cooccurrence_candidates"]:
        assert rec["community_a"] != rec["community_b"]
        assert len(rec["shared_neighbors"]) <= 8
