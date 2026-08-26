import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import rescue_rationale_entities as rre


def test_select_promotions_guards():
    nodes = [
        {"id": "doc_cgrp", "label": "CGRP Channel", "file_type": "document"},
        {"id": "rat_cav", "label": "Cav3.2 T-type Calcium Channel", "file_type": "rationale"},
        {"id": "rat_case", "label": "cav3.2 t-type calcium channel", "file_type": "rationale"},
        {"id": "rat_meta", "label": "Rationale: why Cav3.2 matters", "file_type": "rationale"},
        {"id": "rat_proc", "label": "Cav3.2 Glycosylation in diabetic neuropathy", "file_type": "rationale"},
        {"id": "rat_axis", "label": "PPARgamma Protection of KCC2 via BDNF Reduction", "file_type": "rationale"},
    ]
    doc_norms = {rre.normalize_label(n["label"]) for n in nodes if n["file_type"] == "document"}
    promote, skipped = rre.select_promotions(nodes, doc_norms)
    assert promote == ["rat_cav"]
    reasons = {s["id"]: s["reason"] for s in skipped}
    assert reasons["rat_case"].startswith("normalized-label duplicate")
    assert reasons["rat_meta"] == "meta label"
    assert reasons["rat_proc"] == "process-like label"
    assert "non-entity" in reasons["rat_axis"] or reasons["rat_axis"]


def test_curated_skips_honored():
    nodes = [{"id": "shared_tnfa", "label": "TNF-alpha (pro-inflammatory cytokine)",
              "file_type": "rationale"}]
    promote, skipped = rre.select_promotions(nodes, set())
    assert promote == [] and skipped[0]["reason"].startswith("curated")


def test_rescue_flips_filetype_and_tier(tmp_path):
    nodes = [
        {"id": "doc_x", "label": "KCC2", "file_type": "document"},
        {"id": "rat_hub", "label": "P2X7 Receptor (P2RX7)", "file_type": "rationale"},
    ]
    links = [{"source": n["id"], "target": "doc_x"} for n in nodes for _ in range(20)]
    p = tmp_path / "graph_v2.json"
    p.write_text(json.dumps({"nodes": nodes, "links": links}))
    summary = rre.rescue(str(p))
    out = json.loads(p.read_text())
    promoted = [n for n in out["nodes"] if n["id"] == "rat_hub"][0]
    assert summary["promoted"] == 1 and promoted["file_type"] == "document"
    assert promoted["tier"] == "hub"  # degree ~40
    # idempotent
    s2 = rre.rescue(str(p))
    assert s2["promoted"] == 0
