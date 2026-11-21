"""Tests for analysis/scripts/build_explorer.py on a small hand-built graph."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_explorer as be  # noqa: E402
import graph_inference as gi  # noqa: E402


def node(nid, label=None, etype="molecule", crawled=False):
    n = {"id": nid, "label": label or nid, "entity_type": etype}
    if crawled:
        n["file_type"] = "crawled"
    return n


def link(s, t, sign, **kw):
    base = {"source": s, "target": t, "sign": sign, "relation": "r", "origin": None, "confidence_score": 0.9}
    base.update(kw)
    return base


GRAPH = {
    "nodes": [node("d", "drugX (a drug)", "drug", crawled=True), node("a", "TNF"), node("b", "IL-6"),
              node("pain", "Mechanical Allodynia", "symptom"), node("lps", "LPS")],
    "links": [link("d", "a", -1, origin="auto_crawled", quote="drugX lowers TNF.", source_pmid="11", crawler_evidence=[{"pmid": "12"}]),
              link("d", "b", -1, validation_status="CONFIRMED", source_ref="b.md", quote="drugX lowers IL-6."),
              link("a", "pain", 1), link("b", "pain", 1), link("a", "b", 1), link("b", "a", 1), link("lps", "a", 1)],
}


def build():
    return be.build_data(GRAPH, "/nonexistent.csv")


def test_rows_and_edge_endpoints_are_consistent():
    nodes, edges, findings = build()
    assert all(0 <= e[0] < len(nodes) and 0 <= e[1] < len(nodes) and e[2] in (-1, 1) for e in edges)
    assert findings["meta"]["nodes"] == len(nodes) and findings["meta"]["links"] == len(edges)
    assert all(0 <= c < len(nodes) for c in findings["meta"]["core"])


def test_node_flags_mark_drugs_inducers_and_pain_outcomes():
    nodes, _, _ = build()
    flags = {n[0]: n[4] for n in nodes}
    assert flags["d"] & 1 and not flags["d"] & 4
    assert flags["lps"] & 2                              # nothing acts on it
    assert flags["pain"] & 4 and flags["pain"] & 8       # a pain outcome in the core set
    assert not flags["a"] & 1


def test_edge_provenance_and_status_are_exported():
    nodes, edges, _ = build()
    names = [n[0] for n in nodes]
    by = {(names[e[0]], names[e[1]]): e for e in edges}
    crawled = by[("d", "a")]
    assert crawled[4] == 0 and crawled[5] == "PMID 11" and crawled[7] == "unreviewed" and crawled[8] == 1
    curated = by[("d", "b")]
    assert curated[4] == 1 and curated[5] == "b.md" and curated[7] == "confirmed"


def test_finding_paths_are_real_chains_of_edges():
    nodes, edges, findings = build()
    rows = findings["double_edged"] + findings["pain_raising"] + findings["candidates"]
    chains = [r["path"] for r in rows] + [r["path"] for r in findings["loops"].get("pairs", []) if "path" in r]
    for path in [r["path"] for r in rows if r["path"]]:
        for k, nxt in zip(path, path[1:]):
            assert edges[k][1] == edges[nxt][0]          # each link starts where the last one ended
        assert nodes[edges[path[-1]][1]][4] & 8          # and the last node is a core pain outcome


def test_loops_are_reported_with_node_rows():
    _, _, findings = build()
    pair = findings["loops"]["pairs"][0]
    assert len(pair["nodes"]) == 2 and pair["weight"] > 0


def test_write_site_writes_the_three_data_files_and_the_page(tmp_path):
    nodes, edges, findings = build()
    be.write_site(tmp_path, nodes, edges, findings)
    assert json.loads((tmp_path / "nodes.json").read_text()) == nodes
    assert json.loads((tmp_path / "edges.json").read_text()) == edges
    assert json.loads((tmp_path / "findings.json").read_text())["meta"]["links"] == len(edges)
    assert "Pain Graph Explorer" in (tmp_path / "index.html").read_text()
    assert (tmp_path / "local.html").read_text().startswith("<!doctype html>")


def test_the_page_script_parses(tmp_path):
    # the page is one inline script: a syntax error breaks it for every viewer
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node is not installed")
    script = be.TEMPLATE.read_text().split("<script>", 1)[1].rsplit("</script>", 1)[0]
    js = tmp_path / "page.js"
    js.write_text(script)
    result = subprocess.run([node_bin, "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
