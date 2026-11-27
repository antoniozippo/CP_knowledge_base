"""Tests for analysis/scripts/calibration_baselines.py on small hand-built graphs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calibration_baselines as cb  # noqa: E402
import graph_inference as gi  # noqa: E402


def node(nid):
    return {"id": nid, "label": nid, "entity_type": "molecule"}


def crawled(s, t, sign, pmid):
    return {"source": s, "target": t, "sign": sign, "relation": "r", "origin": "auto_crawled",
            "source_pmid": pmid, "quote": f"{s} {t}", "crawler_evidence": [{"pmid": pmid, "quote": f"{s} {t}"}]}


def build(links):
    ids = sorted({x for l in links for x in (l["source"], l["target"])})
    return gi.SignedGraph({"nodes": [node(i) for i in ids], "links": links}, "/nonexistent.csv")


def test_cases_are_direct_links_with_a_two_hop_path():
    sg = build([crawled("a", "c", -1, "1"), crawled("a", "b", -1, "2"), crawled("b", "c", 1, "3")])
    cases = cb.evaluation_cases(sg.edges)
    assert len(cases) == 1
    k, paths = cases[0]
    assert (sg.edges[k][0], sg.edges[k][1]) == ("a", "c") and len(paths) == 1


def test_paths_from_the_direct_links_own_paper_are_not_independent():
    sg = build([crawled("a", "c", -1, "1"), crawled("a", "b", -1, "1"), crawled("b", "c", 1, "3")])
    (k, paths), = cb.evaluation_cases(sg.edges)
    assert cb.independent(sg.edges, k, paths) == []


def test_composition_is_credited_only_where_it_beats_the_source_baseline():
    # a's other out-links are all +1, so the source baseline says +1 for a -> c; the path says -1, rightly
    links = [crawled("a", "c", -1, "1"), crawled("a", "b", -1, "2"), crawled("b", "c", 1, "3"),
             crawled("a", "x", 1, "4"), crawled("a", "y", 1, "5"), crawled("a", "z", 1, "6")]
    sg = build(links)
    h = cb.head_to_head(sg.edges, cb.evaluation_cases(sg.edges), indep=False)
    assert h == {"n": 1, "composition": 1, "source": 0, "disagree": 1, "composition_right_when_disagree": 1}


def test_report_renders():
    sg = build([crawled("a", "c", -1, "1"), crawled("a", "b", -1, "2"), crawled("b", "c", 1, "3")])
    text = cb.render(cb.compare(sg, shuffles=2))
    assert "Majority sign" in text and "shuffled" in text


def test_wilson_interval_contains_the_estimate():
    lo, hi = cb.wilson(69, 120)
    assert lo < 69 / 120 < hi and 0.45 < lo < 0.5 and 0.65 < hi < 0.7
