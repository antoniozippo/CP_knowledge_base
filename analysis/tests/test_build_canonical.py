"""Tests for analysis/scripts/build_canonical.py: node consolidation, link filtering, coverage."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_canonical as bc  # noqa: E402
import build_perturbation_cases as bp  # noqa: E402
import graph_inference as gi  # noqa: E402

SYMBOLS = {"TNF", "P2RX7", "NLRP3", "CASP1", "TLR2", "TLR4", "PPARG", "SLC12A5", "SCN9A", "MMP9", "CAMP", "TRPV1"}
NODE_MAP = {"map": {"micro": "MICROGLIA"}, "unmapped": ["keep_me"],
            "synonyms": {"TNFA": "TNF", "TNFALPHA": "TNF", "TUMORNECROSISFACTORALPHA": "TNF", "KCC2": "SLC12A5"}}


def node(nid, label, etype="molecule", crawled=False):
    n = {"id": nid, "label": label, "entity_type": etype}
    if crawled:
        n["file_type"] = "crawled"
    return n


NODES = [
    node("tnf", "Tumor Necrosis Factor Alpha (TNF-α)"), node("tnf2", "TNF-α (Pro-Inflammatory Cytokine)"),
    node("p2x7", "P2X7 Receptor (P2RX7)"), node("casp", "Caspase-1 (NLRP3 executioner)"),
    node("tlr24", "TLR2/4"), node("ppar", "NF-κB Transrepression by PPARγ"), node("camp", "cAMP"),
    node("kcc2", "dorsal horn neuronal KCC2"), node("ma", "Mechanical Allodynia", "symptom"),
    node("pwt", "paw withdrawal threshold", "symptom"), node("trem", "TREM2 in Neuropathic Pain", "concept"),
    node("calpain", "Calpain", "molecule"), node("apt", "MMP-9 aptamer"), node("var", "SCN9A p.Ile234Thr"),
    node("micro", "Spinal Microglia (Activated)", "cell_type"), node("keep_me", "TRPV1"),
    node("drug", "drugX", "drug", crawled=True), node("trpv1", "TRPV1 (Transient Receptor Potential Vanilloid 1)"),
]


@pytest.fixture(scope="module")
def mapper():
    graph = {"nodes": NODES, "links": []}
    sg = gi.SignedGraph(graph, "/nonexistent.csv")
    return bc.Mapper(graph, sg, bp.Config(), SYMBOLS, NODE_MAP)


def test_a_label_naming_one_gene_becomes_its_symbol(mapper):
    assert mapper("tnf") == ("TNF", False) and mapper("tnf2") == ("TNF", False)       # duplicates collapse
    assert mapper("p2x7") == ("P2RX7", False)                                          # single-token bracket
    assert mapper("kcc2") == ("SLC12A5", False)                                        # location words dropped
    assert mapper("trpv1") == ("TRPV1", False)


def test_labels_that_are_not_one_gene_stay_apart(mapper):
    for nid in ("casp", "tlr24", "ppar", "camp", "apt", "var"):
        assert mapper(nid) == (nid, False), nid


def test_pain_behaviour_becomes_pain_and_thresholds_flip(mapper):
    assert mapper("ma") == ("PAIN", False)
    assert mapper("pwt") == ("PAIN", True)
    assert mapper("trem")[0] == "trem"                                                 # a topic, not a measurement
    assert mapper("calpain")[0] == "calpain"


def test_explicit_assignments_and_exclusions_win(mapper):
    assert mapper("micro") == ("MICROGLIA", False)
    assert mapper("keep_me") == ("keep_me", False)
    assert mapper("drug") == ("drug", False)


def test_a_target_statement_names_the_target():
    assert bc.names_target_role("the TRPV1 antagonist capsazepine reduced pain", "TRPV1 Channel", "TRPV1")
    assert bc.names_target_role("an inhibitor of NLRP3 was given", "NLRP3 Inflammasome", "NLRP3")
    assert not bc.names_target_role("HDAC6 inhibitor reversed the levels of TNF-α", "Tumor Necrosis Factor Alpha (TNF-α)", "TNF")


def crawled(s, t, sign, pmids, quote="q"):
    return {"source": s, "target": t, "sign": sign, "relation": "r", "origin": "auto_crawled", "source_pmid": pmids[0],
            "quote": quote, "crawler_evidence": [{"pmid": p, "quote": quote} for p in pmids]}


def test_literature_links_lose_test_era_papers_flip_into_thresholds_and_get_tiers(mapper):
    graph = {"nodes": NODES, "links": [
        crawled("drug", "pwt", 1, ["100"]),                 # raises the threshold: lowers PAIN
        crawled("drug", "tnf", -1, ["100", "900"]),         # the test-era paper goes, the link stays
        crawled("drug", "ma", -1, ["900"]),                 # only a test-era paper: dropped
        crawled("tnf", "tnf2", 1, ["100"]),                 # a self-loop once merged
        dict(crawled("tnf", "ma", 1, ["200"]), validation_status="REFUTED"),
    ]}
    edges, dropped = bc.literature_edges(graph, mapper, cutoff=500, in_context=lambda p: p == "100",
                                         review_path="/nonexistent.csv")
    assert set(edges) == {("drug", "PAIN", -1), ("drug", "TNF", -1)}
    assert edges[("drug", "TNF", -1)]["papers"] == {"100": True} and edges[("drug", "TNF", -1)]["tiers"] == {"T1"}
    assert dropped == {"only test-era papers": 1, "self-loop after merging": 1, "refuted": 1}


def test_coverage_leaves_out_the_cases_own_paper():
    ev = lambda papers, **kw: {"papers": {p: True for p in papers}, "tiers": {"T1"}, "curated": False, **kw}
    lit = {("a", "b", 1): ev(["1"]), ("b", "PAIN", 1): ev(["2"]), ("c", "PAIN", 1): ev(["3"])}
    net = bc.Network(lit, {}, {"T1"}, False)
    assert "PAIN" in net.dist("a", "9", 3)                       # another paper's case: reachable
    assert "PAIN" not in net.dist("a", "1", 3)                   # the case's own paper is the only a -> b link
    lit[("a", "b", 1)] = ev(["1"], target_annotation=True)       # a target statement stays usable
    assert "PAIN" in bc.Network(lit, {}, {"T1"}, False).dist("a", "1", 3)


def test_the_prior_only_joins_nodes_already_in_the_literature():
    ev = {"papers": {"1": True}, "tiers": {"T1"}, "curated": False}
    lit = {("a", "TNF", 1): ev}
    prior = {("TNF", "IL1B", 1): {"sources": "x", "curation_effort": 3}, ("a", "TNF", -1): {"sources": "y", "curation_effort": 3}}
    assert set(bc.Network(lit, prior, {"T1", "P"}, False).prior) == {("a", "TNF", -1)}
    assert len(bc.Network(lit, prior, {"T1", "P"}, True).prior) == 2
