"""Tests for add_closure_edges: evidence-backed dynamic-closure edge curation.

Each proposal must carry a verbatim quote from a named repo file; endpoints
resolve against document-type graph nodes only (exact id, case-insensitive
id, norm_label). Existing (source, target) pairs are never duplicated, so
re-running the tool is idempotent.
"""

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "analysis" / "scripts" / "add_closure_edges.py"

sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import add_closure_edges as ace  # noqa: E402


def make_node(node_id, label, entity_type="molecule", tier="mid"):
    return {
        "label": label,
        "file_type": "document",
        "source_file": f"{node_id}.md",
        "source_location": None,
        "community": 0,
        "norm_label": label.lower(),
        "id": node_id,
        "entity_type": entity_type,
        "compartment": "other",
        "tier": tier,
    }


def make_rationale_node(node_id, label):
    node = make_node(node_id, label)
    node["file_type"] = "rationale"
    return node


def base_graph():
    nodes = [
        make_node("kcc2_card", "KCC2 (Potassium-Chloride Cotransporter)", entity_type="channel"),
        make_node("allo_card", "Mechanical Allodynia", entity_type="symptom"),
        make_node("microglia_card", "Microglia", entity_type="cell_type"),
        make_node("bdnf_card", "Brain-Derived Neurotrophic Factor (BDNF)"),
        # non-document nodes must never be endpoint targets
        make_rationale_node("kcc2_rationale", "kcc2 rationale shadow"),
    ]
    links = [
        {
            "relation": "conceptually_related_to",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": "fixture.md",
            "source_location": None,
            "weight": 1.0,
            "source": "microglia_card",
            "target": "bdnf_card",
            "sign": 0,
            "validation_status": None,
        }
    ]
    return {"directed": False, "multigraph": False, "graph": {}, "nodes": nodes, "links": links}


@pytest.fixture
def graph():
    return base_graph()


def proposal(source="KCC2 (Potassium-Chloride Cotransporter)", target="Mechanical Allodynia",
             relation="causes", sign=-1):
    return {
        "source_label": source,
        "target_label": target,
        "relation": relation,
        "sign": sign,
        "quote": "loss of KCC2 collapses the chloride gradient causing allodynia.",
        "source_file": "KCC2.md",
        "confidence": "INFERRED_CLOSURE",
    }


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------

def test_resolves_exact_label_to_document_id(graph):
    resolved = ace.resolve_proposal_endpoints(proposal(), graph["nodes"])
    assert resolved["source"] == "kcc2_card"
    assert resolved["target"] == "allo_card"


def test_resolves_case_insensitive_id_and_norm_label(graph):
    by_id = ace.resolve_proposal_endpoints(
        proposal(source="KCC2_CARD"), graph["nodes"]
    )
    assert by_id["source"] == "kcc2_card"
    by_norm = ace.resolve_proposal_endpoints(
        proposal(target="Mechanical ALLODYNIA"), graph["nodes"]
    )
    assert by_norm["target"] == "allo_card"


def test_resolution_never_targets_non_document_nodes(graph):
    original = copy.deepcopy(graph)
    proposals = [proposal(source="kcc2 rationale shadow")]
    with pytest.raises(ValueError, match="unresolved"):
        ace.apply_closure_edges(graph, proposals)
    assert graph == original


def test_unresolved_endpoint_raises_without_mutation(graph):
    original = copy.deepcopy(graph)
    proposals = [proposal(target="Nonexistent Symptom")]
    with pytest.raises(ValueError, match="Nonexistent Symptom"):
        ace.apply_closure_edges(graph, proposals)
    assert graph == original


# ---------------------------------------------------------------------------
# application mechanics
# ---------------------------------------------------------------------------

def test_applied_link_has_provenance_fields(graph):
    new_graph, summary = ace.apply_closure_edges(graph, [proposal()])
    link = new_graph["links"][-1]
    assert link["source"] == "kcc2_card"
    assert link["target"] == "allo_card"
    assert link["relation"] == "causes"
    assert link["sign"] == -1
    assert link["confidence"] == "INFERRED_CLOSURE"
    assert link["weight"] is None
    # review-verdict / model-score keys must be absent, not null: graph
    # tooling treats key presence as a contract
    assert "validation_status" not in link
    assert "confidence_score" not in link
    assert link["origin"] == "dynamic_closure"
    assert link["quote"].startswith("loss of KCC2")
    assert link["source_ref"] == "KCC2.md"
    assert summary.added == 1
    assert summary.skipped_duplicates == 0
    assert len(summary.unresolved) == 0


def test_existing_signed_pair_is_skipped_as_duplicate(graph):
    proposals = [
        proposal(relation="causes", sign=-1),
        proposal(relation="sustains", sign=-1),  # same pair, different relation
    ]
    _, summary = ace.apply_closure_edges(graph, proposals)
    assert summary.added == 1
    assert summary.skipped_duplicates == 1


def test_existing_neutral_link_does_not_block_signed_edge(graph):
    """A pre-existing sign-0 association on the same pair is not a causal
    channel; the signed closure edge must still be added."""
    graph["links"].append(
        {
            "relation": "conceptually_related_to",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": "fixture.md",
            "source_location": None,
            "weight": 1.0,
            "source": "kcc2_card",
            "target": "allo_card",
            "sign": 0,
            "validation_status": None,
        }
    )
    new_graph, summary = ace.apply_closure_edges(graph, [proposal()])
    assert summary.added == 1
    assert summary.skipped_duplicates == 0
    signed = [
        l for l in new_graph["links"]
        if (l["source"], l["target"]) == ("kcc2_card", "allo_card") and l["sign"] != 0
    ]
    assert len(signed) == 1


def test_intra_batch_duplicate_pairs_collapsed(graph):
    proposals = [proposal(), proposal()]
    new_graph, summary = ace.apply_closure_edges(graph, proposals)
    assert summary.added == 1
    assert summary.skipped_duplicates == 1
    pairs = [(l["source"], l["target"]) for l in new_graph["links"]]
    assert pairs.count(("kcc2_card", "allo_card")) == 1


def test_idempotent_rerun_adds_nothing(graph, tmp_path, capsys):
    graph_path = tmp_path / "graph.json"
    proposals_path = tmp_path / "closure.yaml"
    graph_path.write_text(json.dumps(graph))
    proposals_path.write_text(yaml.safe_dump([proposal()]))

    ace.main(["--graph", str(graph_path), "--proposals", str(proposals_path)])
    after_first = json.loads(graph_path.read_text())
    n_links_first = len(after_first["links"])

    ace.main(["--graph", str(graph_path), "--proposals", str(proposals_path)])
    after_second = json.loads(graph_path.read_text())
    assert len(after_second["links"]) == n_links_first
    assert "added=0" in capsys.readouterr().out


def test_cli_writes_graph_with_appended_links(graph, tmp_path):
    graph_path = tmp_path / "graph.json"
    proposals_path = tmp_path / "closure.yaml"
    graph_path.write_text(json.dumps(graph))
    proposals_path.write_text(yaml.safe_dump([proposal()]))
    ace.main(["--graph", str(graph_path), "--proposals", str(proposals_path)])
    written = json.loads(graph_path.read_text())
    assert any(l.get("origin") == "dynamic_closure" for l in written["links"])


# ---------------------------------------------------------------------------
# --update-quotes mode
# ---------------------------------------------------------------------------

def seeded_closure_graph():
    """Graph already containing one dynamic-closure link with stale metadata."""
    g = copy.deepcopy(base_graph())
    g["links"].append(
        {
            "relation": "causes",
            "confidence": "INFERRED_CLOSURE",
            "source_file": "KCC2.md",
            "source_location": None,
            "weight": None,
            "source": "kcc2_card",
            "target": "allo_card",
            "sign": -1,
            "origin": "dynamic_closure",
            "quote": "OLD correlation-flavored sentence.",
            "source_ref": "KCC2.md",
        }
    )
    return g


def test_update_quotes_rewrites_quote_and_source_ref_on_closure_links():
    g = seeded_closure_graph()
    p = proposal()
    p["quote"] = "NEW causal sentence with direct mechanism."
    p["source_file"] = "Mechanisms.md"
    new_graph, summary = ace.apply_closure_edges(
        g, [p], update_quotes=True
    )
    link = next(l for l in new_graph["links"] if l.get("origin") == "dynamic_closure")
    assert link["quote"] == "NEW causal sentence with direct mechanism."
    assert link["source_ref"] == "Mechanisms.md"
    assert summary.added == 0
    assert summary.updated == 1


def test_default_mode_leaves_existing_quote_metadata_untouched():
    g = seeded_closure_graph()
    p = proposal()
    p["quote"] = "NEW causal sentence."
    _, summary = ace.apply_closure_edges(g, [p])
    link = next(l for l in g["links"] if l.get("origin") == "dynamic_closure")
    assert link["quote"].startswith("OLD")
    assert summary.updated == 0


def test_update_quotes_never_touches_non_closure_links():
    g = seeded_closure_graph()
    # same pair, but extracted (non-closure) provenance — must stay intact
    g["links"].append(
        {
            "relation": "activates",
            "confidence": "EXTRACTED",
            "source_file": "elsewhere.md",
            "weight": 1.0,
            "source": "microglia_card",
            "target": "bdnf_card",
            "sign": 1,
        }
    )
    p = proposal(source="Microglia", target="Brain-Derived Neurotrophic Factor (BDNF)",
                 relation="activates", sign=1)
    p["quote"] = "REWROTE."
    p["source_file"] = "other.md"
    new_graph, _ = ace.apply_closure_edges(g, [p], update_quotes=True)
    extracted = next(l for l in new_graph["links"] if l.get("relation") == "activates")
    assert extracted.get("origin") is None
    assert "quote" not in extracted


def test_source_ref_note_appended_to_link_source_ref():
    g = copy.deepcopy(base_graph())
    p = proposal()
    p["source_ref_note"] = "macrophage≈CNS-resident-macrophage/microglia mapping per dossier context"
    new_graph, summary = ace.apply_closure_edges(g, [p])
    link = new_graph["links"][-1]
    expected = "KCC2.md | macrophage≈CNS-resident-macrophage/microglia mapping per dossier context"
    assert link["source_ref"] == expected
    assert summary.added == 1


def test_cli_update_quotes_flag_rewrites_file(tmp_path, capsys):
    graph_path = tmp_path / "graph.json"
    proposals_path = tmp_path / "closure.yaml"
    graph_path.write_text(json.dumps(seeded_closure_graph()))
    p = proposal()
    p["quote"] = "NEW causal sentence with direct mechanism."
    proposals_path.write_text(yaml.safe_dump([p]))
    ace.main(["--graph", str(graph_path), "--proposals", str(proposals_path),
              "--update-quotes"])
    written = json.loads(graph_path.read_text())
    link = next(l for l in written["links"] if l.get("origin") == "dynamic_closure")
    assert link["quote"].startswith("NEW")
    assert "updated=1" in capsys.readouterr().out


def test_update_quotes_counts_only_real_changes():
    g = seeded_closure_graph()
    # align seeded metadata with the proposal: rewrite becomes a no-op
    closure = next(l for l in g["links"] if l.get("origin") == "dynamic_closure")
    p = proposal()
    closure["quote"] = p["quote"]
    closure["source_ref"] = p["source_file"]
    _, summary_same = ace.apply_closure_edges(g, [p], update_quotes=True)
    assert summary_same.updated == 0
    assert summary_same.skipped_duplicates == 1


def test_every_curated_closure_quote_is_verbatim_byte_substring():
    """Corpus guard: every proposal quote in closure_edges.yaml must be an
    exact byte substring of its source_file, and the applied graph link must
    match the proposal byte-for-byte (no silently stripped markers)."""
    proposals = yaml.safe_load(
        (REPO_ROOT / "analysis" / "claims" / "closure_edges.yaml").read_text()
    )
    assert proposals, "closure_edges.yaml unexpectedly empty"
    for idx, prop in enumerate(proposals):
        source = REPO_ROOT / prop["source_file"]
        assert source.exists(), f"proposal #{idx}: missing source_file {prop['source_file']}"
        quote_bytes = str(prop["quote"]).encode("utf-8")
        assert quote_bytes in source.read_bytes(), (
            f"proposal #{idx} ({prop['source_label']} -> {prop['target_label']}): "
            "quote is not a verbatim byte substring of {prop['source_file']}"
        )
    graph = json.loads((REPO_ROOT / "graphify-out" / "graph_v2.json").read_text())
    links_by_pair = {}
    for link in graph["links"]:
        if link.get("origin") == "dynamic_closure":
            links_by_pair[(link["source"], link["target"])] = link
    resolved_pairs = {
        (ace.resolve_label_to_id(p["source_label"], ace.build_document_indexes(graph["nodes"])),
         ace.resolve_label_to_id(p["target_label"], ace.build_document_indexes(graph["nodes"])))
        for p in proposals
    }
    missing = sorted(pair for pair in resolved_pairs if None in pair or pair not in links_by_pair)
    assert not missing, f"proposals not applied to graph: {missing}"
    for pair, link in links_by_pair.items():
        match = [
            p for p in proposals
            if (ace.resolve_label_to_id(p["source_label"], ace.build_document_indexes(graph["nodes"])),
                ace.resolve_label_to_id(p["target_label"], ace.build_document_indexes(graph["nodes"])))
            == pair
        ]
        if match:
            assert link["quote"].encode("utf-8") == str(match[0]["quote"]).encode("utf-8"), (
                f"graph link {pair} quote drifted from proposal"
            )


def test_quarantine_sign_zero_requires_validation_status():
    import pytest
    from add_closure_edges import _validate_proposal
    base = {"source_label": "A", "target_label": "B", "relation": "inhibits_x",
            "quote": "q", "source_file": "f.md", "sign": 0}
    with pytest.raises(ValueError, match="quarantine"):
        _validate_proposal(base, 0)
    _validate_proposal({**base, "validation_status": "REFUTED"}, 0)
    signed = {**base, "sign": -1}
    _validate_proposal(signed, 0)


def test_quarantine_entry_applied_inert_with_status(graph):
    import json
    from add_closure_edges import apply_closure_edges
    proposals = [{
        "category": "A5",
        "source_label": "KCC2 (Potassium-Chloride Cotransporter)",
        "target_label": "Mechanical Allodynia",
        "relation": "inhibits_mechanical_allodynia",
        "sign": 0,
        "validation_status": "REFUTED",
        "quote": "negative trial result",
        "source_file": "theme.md",
        "confidence": "INFERRED_CLOSURE",
    }]
    new_graph, summary = apply_closure_edges(json.loads(json.dumps(graph)), proposals)
    assert summary.added == 1
    link = [l for l in new_graph["links"] if l.get("origin") == "dynamic_closure"][0]
    assert link["sign"] == 0 and link["validation_status"] == "REFUTED"
