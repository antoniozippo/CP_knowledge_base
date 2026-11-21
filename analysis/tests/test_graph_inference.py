"""Tests for analysis/scripts/graph_inference.py on small hand-built graphs."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import graph_inference as gi  # noqa: E402


def node(nid, label=None, etype="molecule", crawled=False):
    n = {"id": nid, "label": label or nid, "entity_type": etype}
    if crawled:
        n["file_type"] = "crawled"
    return n


def link(s, t, sign, **kw):
    base = {"source": s, "target": t, "sign": sign, "relation": "r", "origin": None}
    base.update(kw)
    return base


def crawled(s, t, sign, quote="X acts on Y.", pmid="1", **kw):
    return link(s, t, sign, origin="auto_crawled", quote=quote, source_pmid=pmid, **kw)


def build(nodes, links, review=None):
    return gi.SignedGraph({"nodes": nodes, "links": links}, review_path=review or "/nonexistent.csv")


PAIN = node("pain", "Mechanical Allodynia", "symptom")


def test_path_sign_is_the_product_of_the_link_signs():
    sg = build([node("d", "drugX", "drug"), node("a"), PAIN],
               [link("d", "a", -1), link("a", "pain", 1)])
    (path,) = sg.paths("d", {"pain"}, 4, sg.distance_to({"pain"}))
    assert gi.path_sign(path) == -1                    # lowers a, a raises pain: analgesic


def test_two_inhibitory_links_make_a_pain_raising_path():
    sg = build([node("d", "drugX", "drug"), node("a"), PAIN],
               [link("d", "a", -1), link("a", "pain", -1)])
    (path,) = sg.paths("d", {"pain"}, 4, sg.distance_to({"pain"}))
    assert gi.path_sign(path) == 1


def test_a_path_stops_at_the_first_pain_node_and_never_crosses_another_drug():
    nodes = [node("d", "drugX", "drug"), node("e", "drugY", "drug"), node("a"), PAIN, node("pain2", "Cold Allodynia", "symptom")]
    links = [link("d", "pain", -1), link("pain", "pain2", 1), link("d", "e", 1), link("e", "pain2", 1), link("d", "a", 1), link("a", "pain2", 1)]
    sg = build(nodes, links)
    paths = sg.paths("d", {"pain", "pain2"}, 4, sg.distance_to({"pain", "pain2"}))
    ends = sorted(p[-1][1] for p in paths)
    assert ends == ["pain", "pain2"]                   # direct, and via a; not through pain, not via drugY
    assert all(all(e[0] != "e" for e in p) for p in paths)


def test_path_weight_decays_with_length():
    sg = build([node("d", "drugX", "drug"), node("a"), node("b"), PAIN],
               [link("d", "pain", -1, confidence_score=0.8), link("d", "a", -1, confidence_score=0.8),
                link("a", "b", 1, confidence_score=0.8), link("b", "pain", 1, confidence_score=0.8)])
    short, long_ = sorted(sg.paths("d", {"pain"}, 4, sg.distance_to({"pain"})), key=len)
    assert gi.path_weight(long_) < gi.path_weight(short)


def test_a_hub_fanning_out_to_many_pain_nodes_cannot_inflate_a_score():
    pains = [node(f"p{i}", f"Allodynia {i}", "symptom") for i in range(10)]
    sg = build([node("d", "drugX", "drug"), node("hub")] + pains,
               [link("d", "hub", -1)] + [link("hub", p["id"], 1) for p in pains])
    sg.core = {p["id"] for p in pains}
    r = gi.drug_effects(sg)["d"]
    per, score, neg, pos = gi.summarise(r["paths"], sg)
    assert len(per) == 10 and neg == 10
    assert score >= -10                                # each outcome counts at most 1 (tanh)
    assert r["agreement"] == 1.0


def test_refuted_review_wrong_and_null_result_links_are_excluded(tmp_path):
    review = tmp_path / "review.csv"
    with open(review, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pmid", "quote", "verdict"])
        w.writerow(["7", "Wrong link.", "WRONG"])
        w.writerow(["8", "Fine link.", "OK"])
    sg = build([node("a"), node("b"), node("c"), node("d"), PAIN],
               [link("a", "b", 1, validation_status="REFUTED"),
                crawled("a", "c", 1, quote="Wrong link.", pmid="7"),
                crawled("a", "d", 1, quote="Dispensable for allodynia.", pmid="9"),
                crawled("a", "pain", 1, quote="Fine link.", pmid="8")], review=str(review))
    assert [(e[0], e[1]) for e in sg.edges] == [("a", "pain")]
    assert dict(sg.excluded) == {"refuted": 1, "review_wrong": 1, "null_result_wording": 1}


def test_unsigned_links_are_not_in_the_signed_graph():
    sg = build([node("a"), node("b")], [link("a", "b", 0)])
    assert sg.edges == []


def test_a_hedged_crawled_link_weighs_less_than_a_plain_one():
    plain = gi.link_weight(crawled("a", "b", 1, quote="A raises B."))
    hedged = gi.link_weight(crawled("a", "b", 1, quote="A may raise B."))
    assert hedged < plain
    assert gi.link_weight(link("a", "b", 1, validation_status="CONFIRMED")) > plain


def test_outcome_nodes_include_disease_concepts_but_not_affect_or_mindmap_nodes():
    nodes = [node("np", "Neuropathic Pain", "concept"), node("cpn", "Chronic Pain Neurobiology (Mind Map)", "concept"),
             node("anx", "Pain-Related Anxiety", "symptom"), node("ma", "Mechanical Allodynia", "symptom"),
             node("ab", "Pain Antibody X", "symptom")]
    sg = build(nodes, [])
    assert sg.pain == {"np", "ma"}


def test_feedback_loop_sign_is_the_product_of_its_links():
    nodes = [node("a"), node("b"), node("c")]
    sg = build(nodes, [link("a", "b", -1), link("b", "c", -1), link("c", "a", 1)])      # two inhibitory
    (loop,) = [c for c in gi.feedback_loops(sg) if len(c["nodes"]) == 3]
    assert loop["sign"] == 1                           # even number of inhibitory links: amplifying
    sg2 = build(nodes, [link("a", "b", -1), link("b", "c", 1), link("c", "a", 1)])
    (loop2,) = [c for c in gi.feedback_loops(sg2) if len(c["nodes"]) == 3]
    assert loop2["sign"] == -1                         # odd: self-limiting


def test_leave_one_out_removes_only_the_drugs_own_pain_link():
    nodes = [node("d", "drugX", "drug"), node("a"), PAIN]
    sg = build(nodes, [link("d", "pain", -1), link("d", "a", 1), link("a", "pain", 1)])
    sg.core = {"pain"}
    full = gi.drug_effects(sg)["d"]
    loo = gi.drug_effects(sg, skip_direct=True)["d"]
    assert full["direct"] == [-1] and len(full["paths"]) == 2
    assert len(loo["paths"]) == 1 and loo["net"] > 0   # only d -> a -> pain remains; the direct link's own sign is hidden


def test_inducers_are_nodes_nothing_acts_on():
    nodes = [node("lps", "LPS"), node("tlr4", "TLR4", "receptor"), node("drug", "drugX", "drug"), PAIN,
             node("cci", "Chronic Constriction Injury (CCI) Model", "concept")]
    sg = build(nodes, [link("lps", "tlr4", 1), link("tlr4", "pain", 1), link("drug", "tlr4", -1), link("cci", "pain", 1)])
    assert "lps" in sg.inducers and "cci" in sg.inducers
    assert "tlr4" not in sg.inducers and "drug" not in sg.inducers


def test_duplicate_nodes_pair_a_crawled_spelling_with_its_curated_node():
    nodes = [node("cur", "P2X7 Receptor (P2RX7)", "channel"), node("dup", "P2X7R", "channel", crawled=True),
             node("other", "P2X4 Receptor", "channel"), node("unrelated", "Calpain", "molecule", crawled=True)]
    sg = build(nodes, [link("dup", "cur", 1)])
    assert [(c, k) for c, k, _ in gi.duplicate_nodes(sg)] == [("dup", "cur")]


def test_two_hop_calibration_counts_a_direct_link_whose_sign_the_paths_reproduce():
    nodes = [node("a"), node("b"), node("c")]
    sg = build(nodes, [link("a", "c", -1), link("a", "b", -1), link("b", "c", 1)])     # path -1 matches direct -1
    cal = gi.calibration(sg)
    assert cal["two_hop"]["all"] == [1, 1]
    sg2 = build(nodes, [link("a", "c", 1), link("a", "b", -1), link("b", "c", 1)])     # path -1 contradicts direct +1
    assert gi.calibration(sg2)["two_hop"]["all"] == [0, 1]


def test_report_runs_end_to_end_on_a_small_graph():
    nodes = [node("d", "drugX", "drug"), node("a", "TNF"), node("b", "IL-6"), PAIN]
    links = [link("d", "a", -1, confidence_score=0.9), link("d", "b", -1, confidence_score=0.9),
             link("a", "pain", 1, confidence_score=0.9), link("b", "pain", 1, confidence_score=0.9),
             link("a", "b", 1), link("b", "a", 1)]
    sg, drugs, targets, choke, loops, cal = gi.build_report({"nodes": nodes, "links": links}, "/nonexistent.csv")
    md = gi.render_markdown(sg, drugs, targets, choke, loops, cal)
    for heading in ("## 0. Calibration", "## 1. Predicted drug effects", "## 2. Targets", "## 3. Chokepoints",
                    "## 4. Feedback loops", "## 5. Graph hygiene"):
        assert heading in md
    assert -1 < drugs["d"]["net"] < 0 and drugs["d"]["mediators"] == 2     # below the report's -1 candidate threshold
    assert any(len(c["nodes"]) == 2 and c["sign"] > 0 for c in loops)      # TNF <-> IL-6 reinforce each other
