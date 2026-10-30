"""Tests for analysis/scripts/split_nodes.py (curated node splits)."""

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import split_nodes as sn  # noqa: E402


def node(nid, label, tier="mid"):
    return {"id": nid, "label": label, "file_type": "document", "community": 1,
            "entity_type": "molecule", "compartment": "other", "tier": tier,
            "merged_from": ["old_id"], "norm_label": label.lower()}


def link(s, t, relation="activates", sign=1):
    return {"source": s, "target": t, "relation": relation, "sign": sign}


def graph():
    return {
        "nodes": [node("k", "Kalirin-7", tier="hub"), node("anx", "Anxiety"),
                  node("rac1", "Rac1"), node("nmdar", "NMDAR")],
        "links": [link("k", "anx", "loss_causes", -1), link("k", "rac1"),
                  link("nmdar", "k", "downregulates", -1), link("k", "anx", "rationale_for", -1)],
    }


SPLIT = {"source": "k", "new_node": {"id": "k_acc", "label": "ACC Kalirin-7", "compartment": "ACC"},
         "source_ref": "theme_10#F10.1", "move_with": ["anx", "nmdar"]}


def test_listed_links_move_in_both_directions_others_stay():
    out, summary = sn.apply_splits(graph(), [SPLIT])
    pairs = [(l["source"], l["target"], l["relation"]) for l in out["links"]]
    assert pairs == [("k_acc", "anx", "loss_causes"), ("k", "rac1", "activates"),
                     ("nmdar", "k_acc", "downregulates"), ("k_acc", "anx", "rationale_for")]
    assert summary.moved_links == 3 and summary.applied == ["k_acc"]


def test_new_node_copies_source_with_overrides_and_provenance():
    out, _ = sn.apply_splits(graph(), [SPLIT])
    new = next(n for n in out["nodes"] if n["id"] == "k_acc")
    assert new["label"] == "ACC Kalirin-7" and new["compartment"] == "ACC"
    assert new["entity_type"] == "molecule" and new["file_type"] == "document"
    assert new["norm_label"] == "acc kalirin-7"
    assert new["merged_from"] == [] and new["split_from"] == "k"
    assert new["split_source_ref"] == "theme_10#F10.1"


def test_tiers_recomputed_from_new_degrees():
    out, _ = sn.apply_splits(graph(), [SPLIT])
    tiers = {n["id"]: n["tier"] for n in out["nodes"]}
    # k keeps 1 neighbour (rac1), k_acc gets 2 (anx, nmdar): both below mid threshold 3
    assert tiers["k"] == "peripheral" and tiers["k_acc"] == "peripheral"


def test_input_not_mutated_and_rerun_is_noop():
    g = graph()
    out, _ = sn.apply_splits(g, [SPLIT])
    assert g == graph()
    again, summary = sn.apply_splits(out, [SPLIT])
    assert summary.applied == [] and summary.skipped == ["k_acc"]
    assert again["links"] == out["links"]


def test_unlinked_move_target_rejected():
    bad = {**SPLIT, "move_with": ["anx", "ghost"]}
    with pytest.raises(ValueError, match="ghost"):
        sn.apply_splits(graph(), [bad])


def test_curated_splits_are_applied_to_committed_graph():
    """Corpus guard: graph_v2.json reflects every split in node_splits.yaml."""
    splits = yaml.safe_load((REPO_ROOT / "analysis/claims/node_splits.yaml").read_text())
    g = json.loads((REPO_ROOT / "graphify-out/graph_v2.json").read_text())
    ids = {n["id"] for n in g["nodes"]}
    for split in splits:
        new_id = split["new_node"]["id"]
        assert new_id in ids, f"split {new_id} not applied"
        for other in split["move_with"]:
            between_source = [l for l in g["links"]
                              if {l["source"], l["target"]} == {split["source"], other}]
            assert not between_source, f"{split['source']}-{other} link not moved to {new_id}"
