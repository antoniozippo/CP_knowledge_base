"""Tests for reverse_edges: curated edge-direction corrections.

Each entry names one stored signed link (source, target, relation, sign)
whose relation describes an action of the target on the source. `reverse`
swaps endpoints keeping relation/sign; `neutralize` zeroes the sign when the
corrected orientation already exists. Every entry carries a verbatim dossier
quote, and re-running the tool is idempotent.
"""

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REVERSALS_YAML = REPO_ROOT / "analysis" / "claims" / "edge_reversals.yaml"
GRAPH_PATH = REPO_ROOT / "graphify-out" / "graph_v2.json"

sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import reverse_edges as rev  # noqa: E402


def make_node(node_id, entity_type="molecule"):
    return {"id": node_id, "label": node_id, "file_type": "document", "entity_type": entity_type}


def make_link(source, target, relation, sign, **extra):
    link = {
        "relation": relation,
        "confidence": "EXTRACTED",
        "source_file": "fixture.md",
        "source_location": None,
        "source": source,
        "target": target,
        "sign": sign,
    }
    link.update(extra)
    return link


def make_entry(source, target, relation, sign, action="reverse"):
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "sign": sign,
        "action": action,
        "quote": "Fasudil: A clinically approved ROCK inhibitor",
        "source_file": "fixture.md",
        "source_location": "L41",
    }


@pytest.fixture
def graph():
    return {
        "nodes": [
            make_node("rock"),
            make_node("fasudil", "drug"),
            make_node("rac1"),
            make_node("nsc", "drug"),
            make_node("ang2"),
            make_node("bbb", "structure"),
        ],
        "links": [
            make_link("rock", "fasudil", "inhibits", -1, validation_status="CONFIRMED"),
            make_link("rac1", "nsc", "inhibits", -1),
            make_link("bbb", "ang2", "disrupts", -1),
            make_link("ang2", "bbb", "disrupts", 1, origin="dynamic_closure"),
        ],
    }


def test_reverse_swaps_endpoints_and_keeps_relation_sign_status(graph):
    new_graph, summary = rev.apply_edge_reversals(
        graph, [make_entry("rock", "fasudil", "inhibits", -1)]
    )
    link = new_graph["links"][0]
    assert (link["source"], link["target"]) == ("fasudil", "rock")
    assert link["relation"] == "inhibits"
    assert link["sign"] == -1
    assert link["validation_status"] == "CONFIRMED"
    assert link["confidence"] == "EXTRACTED"
    assert summary.reversed == 1 and summary.neutralized == 0


def test_reverse_records_provenance(graph):
    new_graph, _ = rev.apply_edge_reversals(
        graph, [make_entry("rock", "fasudil", "inhibits", -1)]
    )
    link = new_graph["links"][0]
    assert link["correction"] == "reversed"
    assert link["original_source"] == "rock"
    assert link["original_target"] == "fasudil"
    assert link["original_sign"] == -1
    assert link["correction_quote"] == "Fasudil: A clinically approved ROCK inhibitor"
    assert link["correction_source_ref"] == "fixture.md:L41"


def test_input_graph_is_not_mutated(graph):
    before = copy.deepcopy(graph)
    rev.apply_edge_reversals(graph, [make_entry("rock", "fasudil", "inhibits", -1)])
    assert graph == before


def test_link_order_is_preserved(graph):
    new_graph, _ = rev.apply_edge_reversals(
        graph, [make_entry("rac1", "nsc", "inhibits", -1)]
    )
    assert [l["relation"] for l in new_graph["links"]] == [l["relation"] for l in graph["links"]]
    assert new_graph["links"][1]["source"] == "nsc"


def test_neutralize_zeroes_sign_and_keeps_direction(graph):
    new_graph, summary = rev.apply_edge_reversals(
        graph, [make_entry("bbb", "ang2", "disrupts", -1, action="neutralize")]
    )
    link = new_graph["links"][2]
    assert (link["source"], link["target"]) == ("bbb", "ang2")
    assert link["sign"] == 0
    assert link["original_sign"] == -1
    assert link["correction"] == "neutralized_duplicate"
    assert summary.neutralized == 1


def test_reverse_onto_existing_signed_pair_raises(graph):
    with pytest.raises(ValueError, match="use action: neutralize"):
        rev.apply_edge_reversals(graph, [make_entry("bbb", "ang2", "disrupts", -1)])


def test_idempotent_rerun_changes_nothing(graph):
    entries = [
        make_entry("rock", "fasudil", "inhibits", -1),
        make_entry("bbb", "ang2", "disrupts", -1, action="neutralize"),
    ]
    once, _ = rev.apply_edge_reversals(graph, entries)
    twice, summary = rev.apply_edge_reversals(once, entries)
    assert twice == once
    assert summary.already_applied == 2
    assert summary.reversed == 0 and summary.neutralized == 0


@pytest.mark.parametrize(
    "entry, message",
    [
        (make_entry("rock", "nsc", "inhibits", -1), "no matching link"),
        (make_entry("rock", "fasudil", "activates", -1), "no matching link"),
        (make_entry("rock", "fasudil", "inhibits", 1), "stored sign is -1"),
        (make_entry("rock", "ghost", "inhibits", -1), "unknown node ghost"),
    ],
)
def test_unresolvable_entry_raises(graph, entry, message):
    with pytest.raises(ValueError, match=message):
        rev.apply_edge_reversals(graph, [entry])


def test_one_bad_entry_aborts_whole_batch(graph):
    entries = [
        make_entry("rock", "fasudil", "inhibits", -1),
        make_entry("rock", "nsc", "inhibits", -1),
    ]
    with pytest.raises(ValueError):
        rev.apply_edge_reversals(graph, entries)


def test_ambiguous_parallel_links_raise(graph):
    graph["links"].append(make_link("rock", "fasudil", "inhibits", -1))
    with pytest.raises(ValueError, match="ambiguous"):
        rev.apply_edge_reversals(graph, [make_entry("rock", "fasudil", "inhibits", -1)])


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("action", "flip", "action must be one of"),
        ("sign", 0, "sign must be -1 or 1"),
        ("quote", "x" * 401, "exceeds 400 chars"),
        ("quote", None, "missing fields: quote"),
    ],
)
def test_entry_validation(graph, field, value, message):
    entry = make_entry("rock", "fasudil", "inhibits", -1)
    entry[field] = value
    with pytest.raises(ValueError, match=message):
        rev.apply_edge_reversals(graph, [entry])


def test_cli_writes_then_check_passes(graph, tmp_path, capsys):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph))
    reversals_path = tmp_path / "reversals.yaml"
    reversals_path.write_text(yaml.safe_dump([make_entry("rock", "fasudil", "inhibits", -1)]))
    args = ["--graph", str(graph_path), "--reversals", str(reversals_path)]

    assert rev.main(args + ["--check"]) == 1
    assert json.loads(graph_path.read_text()) == graph
    assert rev.main(args) == 0
    assert json.loads(graph_path.read_text())["links"][0]["source"] == "fasudil"
    assert rev.main(args + ["--check"]) == 0
    assert "already_applied=1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# corpus guards over the curated file and the committed graph
# ---------------------------------------------------------------------------

def curated_entries():
    entries = yaml.safe_load(REVERSALS_YAML.read_text())
    assert entries, "edge_reversals.yaml unexpectedly empty"
    return entries


def test_every_curated_quote_is_verbatim_byte_substring():
    for idx, entry in enumerate(curated_entries()):
        source = REPO_ROOT / entry["source_file"]
        assert source.exists(), f"entry #{idx}: missing source_file {entry['source_file']}"
        assert str(entry["quote"]).encode("utf-8") in source.read_bytes(), (
            f"entry #{idx} ({rev._describe(entry)}): quote is not a verbatim "
            f"byte substring of {entry['source_file']}"
        )


def test_curated_source_location_points_at_quote_line():
    for idx, entry in enumerate(curated_entries()):
        lines = (REPO_ROOT / entry["source_file"]).read_text().splitlines()
        line_no = int(str(entry["source_location"]).lstrip("L"))
        assert entry["quote"] in lines[line_no - 1], (
            f"entry #{idx} ({rev._describe(entry)}): quote not on {entry['source_location']}"
        )


def test_committed_graph_has_every_curated_reversal_applied():
    graph = json.loads(GRAPH_PATH.read_text())
    new_graph, summary = rev.apply_edge_reversals(graph, curated_entries())
    assert summary.reversed == 0 and summary.neutralized == 0, (
        "graph_v2.json is missing curated reversals; run "
        "python3 analysis/scripts/reverse_edges.py"
    )
    assert summary.already_applied == len(curated_entries())
    assert new_graph == graph


def test_committed_graph_corrections_match_curated_quotes():
    graph = json.loads(GRAPH_PATH.read_text())
    by_original = {
        (l["original_source"], l["original_target"], l["relation"]): l
        for l in graph["links"]
        if "correction" in l
    }
    entries = curated_entries()
    assert len(by_original) == len(entries)
    for entry in entries:
        link = by_original[(entry["source"], entry["target"], entry["relation"])]
        assert link["correction_quote"] == entry["quote"]
