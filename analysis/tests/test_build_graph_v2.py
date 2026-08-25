"""Tests for build_graph_v2: entity dedup, node enrichment, signed edges."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "analysis" / "scripts" / "build_graph_v2.py"
REAL_INPUT = REPO_ROOT / "graphify-out" / "graph.json"

sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import build_graph_v2 as bg  # noqa: E402


def make_node(id_, label, file_type="document", community=0):
    return {
        "label": label,
        "file_type": file_type,
        "source_file": f"{id_}.md",
        "source_location": None,
        "author": None,
        "contributor": None,
        "community": community,
        "norm_label": label.lower(),
        "id": id_,
    }


def make_link(source, target, relation, confidence="EXTRACTED", weight=1.0):
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": 1.0,
        "rationale": None,
        "weight": weight,
        "source_file": "fixture.md",
        "source_location": None,
    }


@pytest.fixture
def fixture_graph():
    nodes = [
        make_node("docA_foo", "Foo (Bar Transporter 2)", community=1),
        make_node("rat_foo", "Foo (ABC1 transporter)", file_type="rationale", community=2),
        make_node("docC_baz", "Baz kinase", community=3),
        make_node("docD_drug", "Fasudil"),
        make_node("docE_sym", "Mechanical allodynia"),
        make_node("docF_cell", "DRG satellite glia"),
        make_node("docG_barrier", "Blood-brain barrier tight junction"),
        make_node("docH_acc", "Anterior cingulate cortex neurons"),
        make_node("docI_dh", "Spinal dorsal horn lamina V"),
        make_node("docJ_sys", "Circulating IL-6 cytokines"),
        make_node("docK_peri", "Peripheral nerve neuroma"),
    ]
    links = [
        make_link("docA_foo", "docC_baz", "activates"),
        make_link("rat_foo", "docC_baz", "inhibits", confidence="INFERRED"),
        make_link("rat_foo", "docA_foo", "references"),
        make_link("docD_drug", "docC_baz", "promotes"),
        make_link("docD_drug", "docE_sym", "references"),
    ]
    return {
        "directed": True,
        "multigraph": True,
        "graph": {},
        "nodes": nodes,
        "links": links,
        "hyperedges": [],
    }


class TestNormalizeLabel:
    def test_strips_parenthetical_qualifiers_and_punctuation(self):
        assert bg.normalize_label("Foo (Bar Transporter 2)") == "foo"

    def test_gene_synonym_maps_to_canonical_token(self):
        assert bg.normalize_label("SLC12A5") == "kcc2"

    def test_en_dash_and_case_folded(self):
        assert bg.normalize_label("BDNF–TrkB–KCC2 Cascade") == "bdnf trkb kcc2 cascade"

    def test_full_name_folds_to_acronym(self):
        assert bg.normalize_label("Brain-Derived Neurotrophic Factor (BDNF)") == "bdnf"

    def test_british_spelling_folds_to_american(self):
        assert bg.normalize_label("Central sensitisation") == "central sensitization"

    def test_qualifier_parenthetical_does_not_cause_acronym_merge(self):
        assert bg.normalize_label("Fasudil (ROCK Inhibitor)") == "fasudil"


class TestClassifiers:
    @pytest.mark.parametrize(
        "label,expected",
        [
            ("Nav1.7 sodium channel", "channel"),
            ("TRPV1", "channel"),
            ("KCC2 (SLC12A5 chloride cotransporter)", "channel"),
            ("TrkB receptor", "receptor"),
            ("Microglia", "cell_type"),
            ("PV interneuron", "cell_type"),
            ("Fasudil", "drug"),
            ("CLP257 (KCC2 Enhancer)", "drug"),
            ("MCC950", "drug"),
            ("Mechanical allodynia", "symptom"),
            ("Thermal hyperalgesia", "symptom"),
            ("Anxiety-like behavior", "symptom"),
            ("WNK-SPAK pathway (KCC2 regulation)", "pathway"),
            ("BDNF signaling", "pathway"),
            ("Central sensitization", "process"),
            ("Blood-brain barrier", "structure"),
            ("Perineuronal nets (PNNs)", "structure"),
            ("BDNF", "molecule"),
            ("IL-6", "molecule"),
            ("Totally unknown thing", "concept"),
        ],
    )
    def test_entity_type_rules(self, label, expected):
        assert bg.classify_entity_type(label) == expected

    @pytest.mark.parametrize(
        "label,expected",
        [
            ("DRG neurons", "DRG"),
            ("Dorsal Root Ganglia satellite cells", "DRG"),
            ("Spinal dorsal horn lamina V", "dorsal_horn"),
            ("ACC pyramidal neurons", "ACC"),
            ("Anterior cingulate cortex", "ACC"),
            ("BBB endothelial tight junctions", "barrier"),
            ("BSCB permeability", "barrier"),
            ("Peripheral nerve neuroma", "peripheral"),
            ("Nociceptor terminals", "peripheral"),
            ("Circulating IL-6 cytokines", "systemic"),
            ("Something unrelated", "other"),
        ],
    )
    def test_compartment_rules(self, label, expected):
        assert bg.classify_compartment(label) == expected


class TestTier:
    @pytest.mark.parametrize(
        "degree,expected",
        [(15, "hub"), (20, "hub"), (14, "mid"), (3, "mid"), (2, "peripheral"), (0, "peripheral")],
    )
    def test_thresholds(self, degree, expected):
        assert bg.assign_tier(degree) == expected


class TestBuildGraph:
    def test_duplicates_merged_with_provenance(self, fixture_graph):
        out, _summary = bg.build_graph(fixture_graph)
        by_id = {n["id"]: n for n in out["nodes"]}
        assert len(out["nodes"]) == len(fixture_graph["nodes"]) - 1
        assert "rat_foo" not in by_id
        survivor = by_id["docA_foo"]
        assert survivor["merged_from"] == ["rat_foo"]
        assert survivor["community"] == 1

    def test_acronym_and_full_name_merge(self):
        nodes = [
            make_node("full", "Brain-Derived Neurotrophic Factor (BDNF)", community=5),
            make_node("acr", "BDNF (Brain-Derived Neurotrophic Factor)", community=7),
        ]
        graph = {"directed": True, "multigraph": True, "graph": {},
                 "nodes": nodes, "links": [], "hyperedges": []}
        out, _summary = bg.build_graph(graph)
        assert len(out["nodes"]) == 1
        assert out["nodes"][0]["merged_from"] == ["acr"]
        assert out["nodes"][0]["community"] == 5

    def test_edges_redirected_no_self_loops(self, fixture_graph):
        out, summary = bg.build_graph(fixture_graph)
        assert len(out["links"]) == 4
        assert summary["links_dropped_self_loop"] == 1
        endpoints = {(l["source"], l["target"]) for l in out["links"]}
        assert ("docA_foo", "docC_baz") in endpoints
        for link in out["links"]:
            assert link["source"] != link["target"]

    def test_node_enrichment_fields_present(self, fixture_graph):
        out, _summary = bg.build_graph(fixture_graph)
        by_id = {n["id"]: n for n in out["nodes"]}
        for nid, etype, comp in [
            ("docA_foo", "channel", "other"),
            ("docC_baz", "molecule", "other"),
            ("docD_drug", "drug", "other"),
            ("docE_sym", "symptom", "other"),
            ("docF_cell", "cell_type", "DRG"),
            ("docG_barrier", "structure", "barrier"),
            ("docH_acc", "cell_type", "ACC"),
            ("docI_dh", "structure", "dorsal_horn"),
            ("docJ_sys", "molecule", "systemic"),
            ("docK_peri", "structure", "peripheral"),
        ]:
            assert by_id[nid]["entity_type"] == etype, nid
            assert by_id[nid]["compartment"] == comp, nid
        tiers = {n["tier"] for n in out["nodes"]}
        assert tiers <= {"hub", "mid", "peripheral"}

    def test_sign_mapping_and_field_passthrough(self, fixture_graph):
        out, _summary = bg.build_graph(fixture_graph)
        signs = {l["relation"]: l["sign"] for l in out["links"]}
        assert signs["activates"] == 1
        assert signs["inhibits"] == -1
        assert signs["promotes"] == 1
        assert signs["references"] == 0
        inhibited = next(l for l in out["links"] if l["relation"] == "inhibits")
        assert inhibited["confidence"] == "INFERRED"
        assert inhibited["weight"] == 1.0
        for link in out["links"]:
            assert link["sign"] in (-1, 0, 1)
            assert isinstance(link["relation"], str)

    def test_tier_reflects_post_merge_degree(self):
        nodes = [make_node(f"n{i}", f"Node {i}") for i in range(17)]
        links = [make_link(f"n{i}", "n0", "activates") for i in range(1, 16)]
        links.append(make_link("n16", "n15", "references"))
        links.append(make_link("n13", "n15", "references"))
        graph = {
            "directed": True,
            "multigraph": True,
            "graph": {},
            "nodes": nodes,
            "links": links,
            "hyperedges": [],
        }
        out, _summary = bg.build_graph(graph)
        by_id = {n["id"]: n for n in out["nodes"]}
        assert by_id["n0"]["tier"] == "hub"
        assert by_id["n15"]["tier"] == "mid"
        assert by_id["n16"]["tier"] == "peripheral"

    def test_input_not_mutated(self, fixture_graph):
        snapshot = json.dumps(fixture_graph)
        bg.build_graph(fixture_graph)
        assert json.dumps(fixture_graph) == snapshot


class TestRealGraphSmoke:
    @pytest.mark.skipif(not REAL_INPUT.exists(), reason="real graph.json not present")
    def test_full_pipeline_on_real_graph(self, tmp_path):
        out_path = tmp_path / "graph_v2.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--input", str(REAL_INPUT), "--output", str(out_path)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr
        assert out_path.exists()

        raw = json.loads(REAL_INPUT.read_text())
        out = json.loads(out_path.read_text())
        assert set(["directed", "multigraph", "graph", "nodes", "links"]) <= set(out)
        assert out.get("hyperedges") is not None
        assert len(out["nodes"]) < len(raw["nodes"])

        for link in out["links"]:
            assert link["sign"] in (-1, 0, 1)

        for node in out["nodes"]:
            assert node["entity_type"] in {
                "molecule", "receptor", "channel", "cell_type", "pathway",
                "process", "structure", "drug", "symptom", "concept",
            }
            assert node["compartment"] in {
                "DRG", "dorsal_horn", "ACC", "barrier", "peripheral", "systemic", "other",
            }
            assert node["tier"] in {"hub", "mid", "peripheral"}

        doc_keys = [
            bg.normalize_label(n["label"])
            for n in out["nodes"]
            if n.get("file_type") == "document"
        ]
        assert len(doc_keys) == len(set(doc_keys))

        kcc2_nodes = [n for n in out["nodes"] if bg.normalize_label(n["label"]) == "kcc2"]
        assert len(kcc2_nodes) == 1
        assert "merged_from" in kcc2_nodes[0]
