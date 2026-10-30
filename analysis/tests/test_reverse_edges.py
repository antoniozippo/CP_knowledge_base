"""Tests for analysis/scripts/reverse_edges.py (curated edge-direction fixes)."""

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import reverse_edges as re_  # noqa: E402

REVERSALS_YAML = REPO_ROOT / "analysis/claims/edge_reversals.yaml"
REVIEW_YAML = REPO_ROOT / "analysis/claims/edge_direction_review.yaml"
GRAPH_JSON = REPO_ROOT / "graphify-out/graph_v2.json"


def node(nid, label, entity_type="molecule"):
    return {"id": nid, "label": label, "entity_type": entity_type, "file_type": "document"}


def link(s, t, relation, sign, **extra):
    return {"source": s, "target": t, "relation": relation, "sign": sign, **extra}


def graph():
    return {
        "nodes": [node("rock", "ROCK"), node("fas", "Fasudil (ROCK Inhibitor)", "drug"),
                  node("bbb", "BBB", "structure"), node("ang1", "Ang-1"), node("ang2", "Ang-2"),
                  node("tnf", "TNF")],
        "links": [
            link("rock", "fas", "inhibits", -1, validation_status="CONFIRMED", confidence="EXTRACTED"),
            link("bbb", "ang1", "stabilizes", 1),
            link("bbb", "ang2", "disrupts", -1),
            link("ang2", "bbb", "disrupts", 1, origin="dynamic_closure"),
            link("tnf", "rock", "activates", 1),
        ],
    }


def entry(s, t, rel, **extra):
    return {"source": s, "target": t, "relation": rel, "source_file": "RhoA-ROCK.md",
            "quote": "Fasudil: a ROCK inhibitor", **extra}


def test_link_is_swapped_keeping_relation_sign_and_verdict():
    out, summary = re_.apply_reversals(graph(), [entry("rock", "fas", "inhibits", note="EC-0100")])
    fixed = out["links"][0]
    assert (fixed["source"], fixed["target"], fixed["relation"], fixed["sign"]) == (
        "fas", "rock", "inhibits", -1)
    assert fixed["validation_status"] == "CONFIRMED" and fixed["confidence"] == "EXTRACTED"
    assert fixed["direction_corrected"] is True
    assert fixed["direction_quote"] == "Fasudil: a ROCK inhibitor"
    assert fixed["direction_ref"] == "RhoA-ROCK.md | EC-0100"
    assert "sign_before_reversal" not in fixed
    assert summary.reversed == ["rock -inhibits-> fas"] and summary.sign_overrides == 0


def test_sign_override_recorded():
    out, summary = re_.apply_reversals(graph(), [entry("bbb", "ang1", "stabilizes", sign=-1)])
    fixed = out["links"][1]
    assert (fixed["source"], fixed["target"], fixed["sign"]) == ("ang1", "bbb", -1)
    assert fixed["sign_before_reversal"] == 1 and summary.sign_overrides == 1


def test_reversal_onto_existing_same_sign_link_drops_the_stored_one():
    out, summary = re_.apply_reversals(graph(), [entry("bbb", "ang2", "disrupts", sign=1)])
    pairs = [(l["source"], l["target"]) for l in out["links"]]
    assert ("bbb", "ang2") not in pairs and pairs.count(("ang2", "bbb")) == 1
    assert summary.dropped_duplicates == ["bbb -disrupts-> ang2"] and summary.reversed == []


def test_reversal_onto_existing_link_of_other_sign_rejected():
    with pytest.raises(ValueError, match="another sign"):
        re_.apply_reversals(graph(), [entry("bbb", "ang2", "disrupts")])


def test_input_not_mutated_and_rerun_is_noop():
    g = graph()
    spec = [entry("rock", "fas", "inhibits"), entry("bbb", "ang2", "disrupts", sign=1)]
    out, _ = re_.apply_reversals(g, spec)
    assert g == graph()
    again, summary = re_.apply_reversals(out, spec)
    assert summary.reversed == [] and summary.dropped_duplicates == []
    assert len(summary.skipped) == 2 and again["links"] == out["links"]


def test_missing_link_and_unknown_node_rejected():
    with pytest.raises(ValueError, match="either direction"):
        re_.apply_reversals(graph(), [entry("tnf", "fas", "inhibits")])
    with pytest.raises(ValueError, match="ghost"):
        re_.apply_reversals(graph(), [entry("rock", "ghost", "inhibits")])


def test_entry_validation():
    with pytest.raises(ValueError, match="quote"):
        re_.apply_reversals(graph(), [{**entry("rock", "fas", "inhibits"), "quote": None}])
    with pytest.raises(ValueError, match="sign override"):
        re_.apply_reversals(graph(), [entry("rock", "fas", "inhibits", sign=0)])


def test_suspects_are_mechanism_to_intervention_links():
    suspects = re_.find_direction_suspects(graph())
    assert [(l["source"], l["target"]) for l in suspects] == [("rock", "fas")]
    out, _ = re_.apply_reversals(graph(), [entry("rock", "fas", "inhibits")])
    assert re_.find_direction_suspects(out) == []


def test_cli_writes_graph(tmp_path, capsys):
    graph_path, spec_path = tmp_path / "g.json", tmp_path / "r.yaml"
    graph_path.write_text(json.dumps(graph()))
    spec_path.write_text(yaml.safe_dump([entry("rock", "fas", "inhibits")]))
    assert re_.main(["--graph", str(graph_path), "--reversals", str(spec_path)]) == 0
    written = json.loads(graph_path.read_text())
    assert written["links"][0]["source"] == "fas"
    assert "reversed=1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# corpus guards
# ---------------------------------------------------------------------------

def _key(item):
    return item["source"], item["target"], item["relation"]


def test_every_curated_reversal_quote_is_verbatim():
    for item in yaml.safe_load(REVERSALS_YAML.read_text()):
        text = (REPO_ROOT / item["source_file"]).read_bytes()
        assert item["quote"].encode("utf-8") in text, (
            f"{_key(item)}: quote is not a verbatim substring of {item['source_file']}")


def test_curated_reversals_are_applied_to_committed_graph():
    """graph_v2.json reflects every entry: only the corrected direction exists."""
    g = json.loads(GRAPH_JSON.read_text())
    keys = {_key(l) for l in g["links"]}
    for item in yaml.safe_load(REVERSALS_YAML.read_text()):
        s, t, rel = _key(item)
        assert (s, t, rel) not in keys, f"{s} -{rel}-> {t} not reversed"
        assert (t, s, rel) in keys, f"corrected link {t} -{rel}-> {s} missing"


def test_every_audit_suspect_is_reviewed():
    g = json.loads(GRAPH_JSON.read_text())
    review = yaml.safe_load(REVIEW_YAML.read_text())
    reviewed = {_key(item) for item in review}
    unreviewed = [_key(l) for l in re_.find_direction_suspects(g) if _key(l) not in reviewed]
    assert not unreviewed, f"suspect links neither reversed nor reviewed: {unreviewed}"


def test_review_entries_name_live_links_not_reversed():
    g = json.loads(GRAPH_JSON.read_text())
    keys = {_key(l) for l in g["links"]}
    reversed_keys = {_key(item) for item in yaml.safe_load(REVERSALS_YAML.read_text())}
    for item in yaml.safe_load(REVIEW_YAML.read_text()):
        assert item["decision"] in {"keep", "review_direction", "review_sign"}
        assert _key(item) in keys, f"review entry {_key(item)} matches no stored link"
        assert _key(item) not in reversed_keys
