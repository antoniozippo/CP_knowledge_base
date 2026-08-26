import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import sync_new_entities as sne


def _write(tmp_path, nodes, links, name="graph_v2.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"nodes": nodes, "links": links}))
    return p


def _raw_graph_fixture():
    raw_nodes = [
        {"id": "kcc2_survivor", "label": "KCC2", "file_type": "document", "community": 1},
        {"id": "old_dup", "label": "KCC2 (SLC12A5)", "file_type": "document", "community": 1},
        {"id": "new_mol", "label": "Interleukin-34", "file_type": "document", "community": 2},
        {"id": "new_cell", "label": "Spinal Microglia (Activated)", "file_type": "document", "community": 2},
    ]
    raw_links = [
        {"source": "old_dup", "target": "new_mol", "relation": "activates", "confidence": "EXTRACTED"},
        {"source": "new_cell", "target": "new_mol", "relation": "causes", "confidence": "EXTRACTED"},
        {"source": "old_dup", "target": "new_mol", "relation": "references", "confidence": "EXTRACTED"},
        {"source": "new_cell", "target": "new_cell", "relation": "activates", "confidence": "EXTRACTED"},
    ]
    return raw_nodes, raw_links


def _survivor():
    return {"id": "kcc2_survivor", "label": "KCC2", "file_type": "document",
            "entity_type": "molecule", "compartment": "other", "tier": "mid"}


def test_merge_sources_skipped_and_links_canonicalized(tmp_path):
    raw_nodes, raw_links = _raw_graph_fixture()
    v2p = _write(tmp_path, [_survivor()], [])
    rawp = _write(tmp_path, raw_nodes, raw_links, name="raw.json")
    summary = sne.sync(str(v2p), str(rawp), with_links=True)
    assert summary["skipped_merge_sources"] == 1  # old_dup folded into kcc2_survivor
    assert sorted(summary["added_node_ids"]) == ["new_cell", "new_mol"]
    assert summary["added_links"] == 3  # self-loop dropped; three links imported (one redirects to survivor)
    out = json.loads(v2p.read_text())
    imported = [(l["source"], l["target"], l["sign"]) for l in out["links"] if l.get("sign") in (1, -1)]
    # merge-source endpoint redirected onto its survivor
    assert ("kcc2_survivor", "new_mol", 1) in imported
    assert ("new_cell", "new_mol", 1) in imported
    ids = {n["id"] for n in out["nodes"]}
    assert "old_dup" not in ids
    tiers = {n["id"]: n["tier"] for n in out["nodes"]}
    assert tiers["new_mol"] == "mid"  # degree 3 post-import (2 neighbors via 3 links)
    s2 = sne.sync(str(v2p), str(rawp), with_links=True)
    assert s2["added_nodes"] == 0 and s2["added_links"] == 0  # idempotent


def test_without_links_keeps_topology_untouched(tmp_path):
    raw_nodes, raw_links = _raw_graph_fixture()
    v2p = _write(tmp_path, [_survivor()], [])
    rawp = _write(tmp_path, raw_nodes, raw_links, name="raw.json")
    summary = sne.sync(str(v2p), str(rawp), with_links=False)
    assert summary["added_nodes"] == 2 and summary["added_links"] == 0
    out = json.loads(v2p.read_text())
    assert len(out["links"]) == 0
    tiers = {n["id"]: n["tier"] for n in out["nodes"]}
    assert tiers["new_mol"] == "peripheral"


def test_syncs_only_missing_document_nodes(tmp_path):
    raw_nodes = [
        {"id": "a", "label": "NKCC1 (SLC12A2)", "file_type": "document", "community": 1},
        {"id": "rat_x", "label": "rationale thing", "file_type": "rationale", "community": 1},
        {"id": "b", "label": "KCC2", "file_type": "document", "community": 1},
    ]
    v2p = _write(tmp_path, [_survivor()], [])
    rawp = _write(tmp_path, raw_nodes, [], name="raw.json")
    summary = sne.sync(str(v2p), str(rawp))
    assert summary["added_nodes"] == 1
    out = json.loads(v2p.read_text())
    new = [n for n in out["nodes"] if n["id"] == "a"][0]
    assert new["entity_type"] in ("channel", "molecule", "receptor")
    assert new["compartment"] in ("dorsal_horn", "DRG", "peripheral", "other", "systemic")
    assert new["tier"] == "peripheral"


def test_neutral_sign_zero_links_importable_after_quarantine_feature(tmp_path):
    raw_nodes, raw_links = _raw_graph_fixture()
    raw_links.append({"source": "old_dup", "target": "new_mol",
                      "relation": "regulates", "confidence": "EXTRACTED"})
    v2p = _write(tmp_path, [_survivor()], [])
    rawp = _write(tmp_path, raw_nodes, raw_links, name="raw.json")
    summary = sne.sync(str(v2p), str(rawp), with_links=True)
    assert summary["added_links"] == 4  # includes sign-0 regulates link
