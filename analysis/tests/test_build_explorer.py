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
    "links": [link("d", "a", -1, origin="auto_crawled", quote="drugX lowers TNF.", source_pmid="11", crawler_evidence=[{"pmid": "11"}, {"pmid": "12"}]),     # its own paper and one more
              link("d", "b", -1, validation_status="CONFIRMED", source_ref="b.md", quote="drugX lowers IL-6."),
              link("a", "pain", 1), link("b", "pain", 1), link("a", "b", 1), link("b", "a", 1), link("lps", "a", 1)],
}


def build():
    return be.build_data(GRAPH, "/nonexistent.csv")


def test_rows_and_edge_endpoints_are_consistent():
    data = build()
    nodes, edges = data["nodes"], data["edges"]
    signed = [e for e in edges if e[2] != 0]
    assert all(0 <= e[0] < len(nodes) and 0 <= e[1] < len(nodes) for e in edges)
    assert edges[:len(signed)] == signed                      # signed links come first, in the order graph_inference uses
    meta = data["findings"]["meta"]
    assert meta["nodes"] == len(nodes) and meta["links"] == len(signed) and meta["unsigned"] == len(edges) - len(signed)
    assert all(0 <= c < len(nodes) for c in meta["core"])


def test_node_flags_mark_drugs_inducers_and_pain_outcomes():
    flags = {n[0]: n[4] for n in build()["nodes"]}
    assert flags["d"] & 1 and not flags["d"] & 4
    assert flags["lps"] & 2                              # nothing acts on it
    assert flags["pain"] & 4 and flags["pain"] & 8       # a pain outcome in the core set
    assert not flags["a"] & 1


def test_node_slugs_are_short_stable_names():
    nodes = build()["nodes"]
    slugs = [n[7] for n in nodes]
    assert all(len(s) == 8 and set(s) <= set("0123456789abcdef") for s in slugs) and len(set(slugs)) == len(slugs)
    assert [n[7] for n in build()["nodes"]] == slugs      # the same on every build, so share links survive a rebuild


def test_edge_provenance_and_status_are_exported():
    data = build()
    names = [n[0] for n in data["nodes"]]
    by = {(names[e[0]], names[e[1]]): e for e in data["edges"]}
    crawled = by[("d", "a")]
    assert crawled[4] == 0 and crawled[5] == "PMID 11" and crawled[7] == "unreviewed"
    assert crawled[8] == 1                                  # two papers in its evidence list: one more than its own
    curated = by[("d", "b")]
    assert curated[4] == 1 and curated[5] == "b.md" and curated[7] == "confirmed" and curated[8] == 0
    assert len({e[11] for e in data["edges"]}) == len(data["edges"])      # link keys are unique


def test_unsigned_links_are_exported_with_their_relation_and_never_scored():
    graph = {"nodes": GRAPH["nodes"], "links": GRAPH["links"] + [link("a", "b", 0, relation="binds")]}
    data = be.build_data(graph, "/nonexistent.csv")
    unsigned = [e for e in data["edges"] if e[2] == 0]
    assert len(unsigned) == 1 and unsigned[0][9] == "binds"
    assert data["findings"]["meta"]["links"] == len(data["edges"]) - 1


def test_finding_paths_are_real_chains_of_edges():
    data = build()
    nodes, edges, findings = data["nodes"], data["edges"], data["findings"]
    rows = findings["double_edged"] + findings["pain_raising"] + findings["candidates"]
    for path in [r["path"] for r in rows if r["path"]]:
        for k, nxt in zip(path, path[1:]):
            assert edges[k][1] == edges[nxt][0]          # each link starts where the last one ended
        assert nodes[edges[path[-1]][1]][4] & 8          # and the last node is a core pain outcome


def test_loops_are_reported_with_node_rows():
    pair = build()["findings"]["loops"]["pairs"][0]
    assert len(pair["nodes"]) == 2 and pair["weight"] > 0


def test_families_hold_rows_for_every_evidence_level():
    fams = build()["families"]
    assert fams["evidence"] == ["all", "corroborated", "curated"]
    assert fams["families"][0]["key"] == "any"
    for f in fams["families"]:
        for ev in fams["evidence"]:
            rows = fams["rows"][f"{f['key']}|{ev}"]
            assert set(rows) == {"drugs", "targets"}
    drug_rows = fams["rows"]["any|all"]["drugs"]
    assert [r[0] for r in drug_rows] and all(len(r) == 6 for r in drug_rows)


def test_the_corroborated_level_drops_single_paper_links():
    fams = build()["families"]
    # drugX reaches pain through one curated link (to IL-6) and one two-paper crawled link (to TNF): both survive
    both = [r for r in fams["rows"]["any|corroborated"]["drugs"] if r[4] == 2]
    assert both
    curated_only = fams["rows"]["any|curated"]["drugs"]
    assert all(r[4] <= 1 for r in curated_only)             # only the curated hop remains


def test_review_rows_rank_unreviewed_links_and_carry_flags():
    data = build()
    rows = data["review"]["rows"]
    edges = data["edges"]
    assert rows and all(edges[r[0]][4] == 0 for r in rows)      # crawled links only
    assert [r[1] for r in rows] == sorted((r[1] for r in rows), reverse=True)
    assert data["review"]["flags"]["one_paper"] == be.F_ONE_PAPER


def test_a_quote_naming_both_nodes_is_not_flagged_but_one_naming_neither_is():
    assert be.mentions("TNF-\u03b1 raised pain", "Tumor Necrosis Factor Alpha (TNF-\u03b1)")
    assert be.mentions("tumor necrosis factor alpha", "TNF-alpha")
    assert not be.mentions("this raised pain", "TRPV1 (Transient Receptor Potential Vanilloid 1)")


def test_write_site_writes_the_data_files_and_the_page(tmp_path):
    data = build()
    be.write_site(tmp_path, data)
    assert json.loads((tmp_path / "nodes.json").read_text()) == data["nodes"]
    assert json.loads((tmp_path / "edges.json").read_text()) == data["edges"]
    for name in ("findings", "families", "review"):
        assert json.loads((tmp_path / f"{name}.json").read_text()) == json.loads(json.dumps(data[name]))
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
