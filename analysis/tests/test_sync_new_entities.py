import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import sync_new_entities as sne


def _write(tmp_path, nodes, links, name="graph_v2.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"nodes": nodes, "links": links}))
    return p


def test_syncs_only_missing_document_nodes(tmp_path):
    raw = {
        "nodes": [
            {"id": "a", "label": "NKCC1 (SLC12A2)", "file_type": "document", "community": 1},
            {"id": "rat_x", "label": "rationale thing", "file_type": "rationale", "community": 1},
            {"id": "b", "label": "KCC2", "file_type": "document", "community": 1},
        ],
        "links": [],
    }
    v2p = _write(tmp_path, [{"id": "b", "label": "KCC2", "file_type": "document"}], [])
    rawp = _write(tmp_path, raw["nodes"], raw["links"], name="raw.json")
    summary = sne.sync(str(v2p), str(rawp))
    assert summary["added"] == 1 and summary["ids"] == ["a"]
    out = json.loads(v2p.read_text())
    assert len(out["nodes"]) == 2
    new = out["nodes"][1]
    assert new["entity_type"] in ("channel", "molecule", "receptor")
    assert new["compartment"] in ("dorsal_horn", "DRG", "peripheral", "other", "systemic")
    assert new["tier"] == "peripheral"


def test_idempotent_and_degree_aware(tmp_path):
    nodes = [
        {"id": "a", "label": "NKCC1 (SLC12A2)", "file_type": "document", "community": 1},
        {"id": "b", "label": "KCC2", "file_type": "document", "community": 1},
    ]
    links = [{"source": "b", "target": "a"}] * 5
    v2p = _write(tmp_path, [nodes[1]], links)
    rawp = _write(tmp_path, nodes, links, name="raw.json")
    s1 = sne.sync(str(v2p), str(rawp))
    assert s1["added"] == 1
    out = json.loads(v2p.read_text())
    nkcc = [n for n in out["nodes"] if n["id"] == "a"][0]
    assert nkcc["tier"] == "mid"  # degree 5
    s2 = sne.sync(str(v2p), str(rawp))
    assert s2["added"] == 0
