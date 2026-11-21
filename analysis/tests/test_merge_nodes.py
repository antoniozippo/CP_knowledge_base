"""Tests for analysis/scripts/merge_nodes.py on small hand-built graphs."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import merge_nodes as mn  # noqa: E402


def node(nid, label=None):
    return {"id": nid, "label": label or nid, "tier": "peripheral"}


def link(s, t, sign=1, relation="activates", **kw):
    return {"source": s, "target": t, "sign": sign, "relation": relation, **kw}


def crawled(s, t, sign=1, relation="activates", pmid="1", evidence=None):
    ev = [{"pmid": p, "quote": f"q{p}"} for p in (evidence or [pmid])]
    return link(s, t, sign, relation, origin="auto_crawled", source_pmid=pmid, quote=f"q{pmid}", crawler_evidence=ev)


MERGE = [{"survivor": "keep", "absorbs": ["gone"]}]


def graph(links, extra_nodes=()):
    ids = {"keep", "gone"} | {x for l in links for x in (l["source"], l["target"])} | set(extra_nodes)
    return {"nodes": [node(i) for i in sorted(ids)], "links": links}


def test_links_move_to_the_survivor_and_the_absorbed_node_goes():
    g, s = mn.apply_merges(graph([link("a", "gone", -1, "inhibits"), link("gone", "b")]), MERGE)
    assert {n["id"] for n in g["nodes"]} == {"keep", "a", "b"}
    assert [(l["source"], l["target"]) for l in g["links"]] == [("a", "keep"), ("keep", "b")]
    assert s.moved_links == 2 and s.applied == ["keep"]
    assert next(n for n in g["nodes"] if n["id"] == "keep")["merged_from"] == ["gone"]


def test_duplicate_links_fold_into_one_and_keep_every_paper():
    g, s = mn.apply_merges(graph([crawled("a", "keep", pmid="1"), crawled("a", "gone", pmid="2", evidence=["2", "3"])]), MERGE)
    (l,) = g["links"]
    assert [e["pmid"] for e in l["crawler_evidence"]] == ["1", "2", "3"]
    assert l["source_pmid"] == "1" and s.folded_links == 1


def test_a_curated_link_wins_over_a_crawled_duplicate():
    g, _ = mn.apply_merges(graph([crawled("a", "keep", pmid="7"), link("a", "gone", source_ref="note.md")]), MERGE)
    (l,) = g["links"]
    assert l.get("origin") != "auto_crawled" and l["source_ref"] == "note.md"
    assert [e["pmid"] for e in l["crawler_evidence"]] == ["7"]          # the crawled paper becomes its evidence


def test_links_that_differ_in_sign_or_relation_stay_apart():
    links = [crawled("a", "keep", 1, "activates"), crawled("a", "gone", -1, "inhibits"), crawled("a", "gone", 0, "binds")]
    g, s = mn.apply_merges(graph(links), MERGE)
    assert len(g["links"]) == 3 and s.folded_links == 0


def test_a_link_between_the_two_nodes_is_dropped():
    g, s = mn.apply_merges(graph([link("keep", "gone"), link("a", "keep")]), MERGE)
    assert [(l["source"], l["target"]) for l in g["links"]] == [("a", "keep")] and s.dropped_self_loops == 1


def test_duplicates_elsewhere_in_the_graph_are_left_alone():
    links = [link("x", "y"), link("x", "y"), link("a", "gone")]
    g, _ = mn.apply_merges(graph(links), MERGE)
    assert len(g["links"]) == 3


def test_the_merge_is_idempotent_and_leaves_the_input_untouched():
    g0 = graph([link("a", "gone")])
    before = json.dumps(g0)
    g1, _ = mn.apply_merges(g0, MERGE)
    g2, s2 = mn.apply_merges(g1, MERGE)
    assert json.dumps(g0) == before
    assert g2 == g1 and s2.applied == [] and s2.skipped == ["keep"]


def test_links_the_conflict_log_points_at_are_never_removed():
    links = [crawled("a", "keep", pmid="1"), crawled("a", "gone", pmid="2")]
    with pytest.raises(ValueError, match="conflict log"):
        mn.apply_merges(graph(links), MERGE, protect_through=1)
    mn.apply_merges(graph(links), MERGE, protect_through=0)          # removing position 1 is fine


def test_an_unknown_survivor_is_an_error():
    with pytest.raises(ValueError, match="unknown survivor"):
        mn.apply_merges(graph([]), [{"survivor": "nope", "absorbs": ["gone"]}])


def test_the_survivor_tier_is_recomputed():
    links = [link(f"n{i}", "gone") for i in range(12)]
    g, _ = mn.apply_merges(graph(links), MERGE)
    assert next(n for n in g["nodes"] if n["id"] == "keep")["tier"] != "peripheral"


def test_crawled_links_do_not_raise_the_survivor_tier():
    links = [crawled(f"n{i}", "gone", pmid=str(i)) for i in range(12)]
    g, _ = mn.apply_merges(graph(links), MERGE)
    assert next(n for n in g["nodes"] if n["id"] == "keep")["tier"] == "peripheral"
