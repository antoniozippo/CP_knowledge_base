# crawler/tests/test_matcher_precision.py
# Entity matching must prefer a missed merge over a wrong one: a wrong merge
# attaches evidence to the wrong node. Synthetic cases pin the rules; the
# real-graph table pins the false merges observed in the first survey.

import json

import pytest
import yaml

from crawler import matcher as matcher_module
from crawler.classify import normalize_label
from crawler.matcher import EntityMatcher


def _build(tmp_path, monkeypatch, labels, edges=(), aliases=None, crawled=None, crawled_first=False):
    """labels: {node_id: label}; edges: [(source_id, target_id)] for degree;
    crawled: {node_id: label} of nodes the crawler itself created."""
    nodes = [{"id": i, "label": lab, "norm_label": lab.lower()} for i, lab in labels.items()]
    # the updater stores crawled nodes under its normalized key ("Nav1.6" -> "nav1 6")
    extra = [{"id": i, "label": lab, "norm_label": normalize_label(lab), "file_type": "crawled"}
             for i, lab in (crawled or {}).items()]
    nodes = extra + nodes if crawled_first else nodes + extra
    links = [{"source": s, "target": t, "relation": "r", "sign": 0} for s, t in edges]
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"nodes": nodes, "links": links}))
    alias_path = tmp_path / "aliases.yaml"
    alias_path.write_text(yaml.safe_dump(aliases or {}))
    monkeypatch.setattr(matcher_module, "ALIASES_PATH", alias_path)
    return EntityMatcher(graph_path=str(graph))


# --- generic words never justify a merge --------------------------------------

@pytest.mark.parametrize("name", ["Zorblax-9 kinase", "Zorblax9 protein", "receptor", "Kinase"])
def test_names_sharing_only_generic_words_do_not_merge(tmp_path, monkeypatch, name):
    m = _build(tmp_path, monkeypatch, {"p": "PKC (Protein Kinase C)", "m": "MARCKS Protein",
                                       "l": "LAMP2A (Chaperone-Mediated Autophagy Receptor)"})
    assert m.match_entity(name).status == "NO_MATCH"


# --- label coverage and ranking ------------------------------------------------

def test_name_covering_a_small_part_of_a_long_label_does_not_merge(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"x": "IL-6/gp130/JAK2 Axis"})
    assert m.match_entity("JAK2").status == "NO_MATCH"


def test_more_specific_name_is_not_merged_into_a_broader_node(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"b": "BDNF"})
    assert m.match_entity("BDNF Val66Met Polymorphism").status == "NO_MATCH"


def test_higher_coverage_beats_higher_degree(tmp_path, monkeypatch):
    labels = {"down": "KCC2 Downregulation (Impaired GABAergic Inhibition)",
              "kcc2": "KCC2 (Potassium-Chloride Cotransporter 2)", "o": "Other"}
    m = _build(tmp_path, monkeypatch, labels, edges=[("down", "o")] * 5 + [("kcc2", "o")])
    assert m.match_entity("KCC2").matched_node_id == "kcc2"


def test_degree_breaks_ties_between_identical_heads(tmp_path, monkeypatch):
    labels = {"a": "KCC2 (SLC12A5 chloride cotransporter)", "b": "KCC2 (Potassium-Chloride Cotransporter 2)",
              "o": "Other"}
    m = _build(tmp_path, monkeypatch, labels, edges=[("a", "o")] + [("b", "o")] * 3)
    assert m.match_entity("KCC2").matched_node_id == "b"


def test_generic_suffix_and_plural_variants_still_merge(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"k": "KCC2 (Potassium-Chloride Cotransporter 2)",
                                       "a": "Astrocyte (Reactive)"})
    assert m.match_entity("KCC2 transporter").matched_node_id == "k"
    assert m.match_entity("Astrocytes").matched_node_id == "a"


# --- parenthetical text -------------------------------------------------------

def test_parenthetical_symbol_acts_as_an_alias(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "Nav1.7 (SCN9A) Voltage-Gated Sodium Channel"})
    assert m.match_entity("SCN9A").matched_node_id == "n"


def test_words_inside_a_description_are_not_aliases(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"k": "Kalirin-7 (GEF for Rac1/RhoG)"})
    assert m.match_entity("Rac1").status == "NO_MATCH"


def test_parenthetical_qualified_by_a_generic_word_is_not_an_alias(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"d": "Simvastatin (RhoA Inhibitor)"})
    assert m.match_entity("RhoA").status == "NO_MATCH"


# --- digits -------------------------------------------------------------------

def test_fuzzy_match_rejects_names_that_differ_only_in_digits(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"c": "Caspase-3"})
    assert m.match_entity("Caspase-1").status == "NO_MATCH"


def test_numbered_family_members_are_kept_apart(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"a": "IL-6 (Interleukin-6)", "b": "IL-10 (Interleukin-10)"})
    assert m.match_entity("IL-6").matched_node_id == "a"
    assert m.match_entity("IL-10").matched_node_id == "b"


# --- alias registry -----------------------------------------------------------

def test_circular_alias_entries_resolve_to_the_graph_node(tmp_path, monkeypatch):
    aliases = {"KCC2": ["SLC12A5", "KCC2"], "SLC12A5": ["KCC2"]}
    m = _build(tmp_path, monkeypatch, {"k": "KCC2 (Potassium-Chloride Cotransporter 2)"}, aliases=aliases)
    result = m.match_entity("SLC12A5")
    assert (result.status, result.matched_node_id) == ("ALIAS", "k")


def test_alias_resolves_through_a_multiword_alias(tmp_path, monkeypatch):
    aliases = {"KALRN": ["Kalirin-7", "Kalirin7"]}
    m = _build(tmp_path, monkeypatch, {"k": "Kalirin-7 (GEF for Rac1/RhoG)"}, aliases=aliases)
    result = m.match_entity("KALRN")
    assert (result.status, result.matched_node_id) == ("ALIAS", "k")


def test_alias_never_crosses_into_a_sibling_gene(tmp_path, monkeypatch):
    aliases = {"P2RX4": ["P2X4"], "P2RX7": ["P2X7"]}
    m = _build(tmp_path, monkeypatch, {"a": "P2X4 Receptor", "b": "P2X7 Receptor"}, aliases=aliases)
    assert m.match_entity("P2RX4").matched_node_id == "a"
    assert m.match_entity("P2RX7").matched_node_id == "b"


# --- class qualifiers: "X receptor / inhibitors / antagonists / neurons" is not X ----

@pytest.mark.parametrize("name, label", [
    ("CGRP receptor", "CGRP (Calcitonin Gene-Related Peptide)"),
    ("CGRP receptor antagonists", "CGRP (Calcitonin Gene-Related Peptide)"),
    ("TRPV1 antagonists", "TRPV1 (Transient Receptor Potential Vanilloid 1)"),
    ("TRPV1 agonists", "TRPV1 (Transient Receptor Potential Vanilloid 1)"),
    ("ROCK inhibitors", "ROCK (ROCK1/ROCK2)"),
    ("COX-2 inhibitors", "COX-2 (Cyclooxygenase-2)"),
    ("NLRP3 inhibitor", "MCC950 (NLRP3 Inhibitor)"),
    ("spinal dorsal horn neurons", "Spinal Dorsal Horn Kalirin-7"),
    ("Nav1.8+ neurons", "Nav1.8 (SCN10A voltage-gated sodium channel)"),
    ("TNF-alpha receptor", "TNF-α (Pro-Inflammatory Cytokine)"),
])
def test_name_with_a_class_qualifier_does_not_merge_into_a_node_without_it(tmp_path, monkeypatch, name, label):
    m = _build(tmp_path, monkeypatch, {"n": label})
    assert m.match_entity(name).status == "NO_MATCH"


@pytest.mark.parametrize("name, label", [
    ("TrkB receptor", "TrkB Receptor (TrkB.FL)"),
    ("TLR4 receptor", "TLR4 (Toll-like Receptor 4)"),           # "receptor" in the description
    ("dorsal horn neurons", "Dorsal Horn Neurons"),
    ("TRPV1 antagonists", "TRPV1 Antagonists (class)"),
    ("CGRP receptor", "CGRP Receptor (CLR/RAMP1 Heterodimer)"),
])
def test_name_with_a_class_qualifier_still_merges_into_a_node_that_has_it(tmp_path, monkeypatch, name, label):
    m = _build(tmp_path, monkeypatch, {"n": label})
    assert m.match_entity(name).matched_node_id == "n"


def test_class_qualifier_picks_the_receptor_node_over_the_ligand_node(tmp_path, monkeypatch):
    labels = {"lig": "CGRP (Calcitonin Gene-Related Peptide)", "rec": "CGRP Receptor (CLR/RAMP1 Heterodimer)", "o": "Other"}
    m = _build(tmp_path, monkeypatch, labels, edges=[("lig", "o")] * 5)   # the ligand has the higher degree
    assert m.match_entity("CGRP receptor").matched_node_id == "rec"
    assert m.match_entity("CGRP").matched_node_id == "lig"


def test_class_qualifier_blocks_the_fuzzy_rule_too(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "P2X7 Receptor Antagonist"})
    assert m.match_entity("P2X7 Receptor Antagonists").matched_node_id == "n"      # same qualifiers
    assert m.match_entity("P2X7 Receptor Agonist").status == "NO_MATCH"            # one letter's worth of fuzz, opposite meaning


def test_exact_label_still_wins_over_the_qualifier_rule(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "CGRP inhibitors"})
    assert m.match_entity("CGRP inhibitors").status == "EXACT"


# --- auto-crawled nodes are reached by exact label only ------------------------
# Their labels are free text; a short name must not merge into a longer one.

def test_short_name_does_not_merge_into_a_longer_crawled_label(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"b": "BDNF"},
               crawled={"c1": "spinal cord injury", "c2": "dorsal root ganglion electrical stimulation"})
    assert m.match_entity("spinal cord").status == "NO_MATCH"
    assert m.match_entity("dorsal root ganglion").status == "NO_MATCH"


def test_near_spelling_does_not_fuzzy_merge_into_a_crawled_label(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"b": "BDNF"}, crawled={"c": "Substance P release"})
    assert m.match_entity("Substance P releas").status == "NO_MATCH"


def test_crawled_node_is_found_by_its_exact_label(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"b": "BDNF"}, crawled={"c": "Nav1.6"})
    result = m.match_entity("Nav1.6")
    assert (result.status, result.matched_node_id) == ("EXACT", "c")


def test_crawled_node_is_found_despite_punctuation(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"b": "BDNF"}, crawled={"c": "feed-forward inhibition"})
    assert m.match_entity("Feed forward inhibition").matched_node_id == "c"


def test_every_crawled_node_in_the_real_graph_resolves_to_itself():
    # Otherwise the next crawl would create a duplicate of a node it already made.
    m = EntityMatcher(graph_path="graphify-out/graph_v2.json")
    for node in (n for n in m.nodes if matcher_module.is_crawled(n)):
        hit = m.match_entity(node["label"])
        assert hit.matched_node_id == node["id"] or not matcher_module.is_crawled(
            m.nodes_by_id[hit.matched_node_id]), node["label"]


@pytest.mark.parametrize("crawled_first", [False, True])
def test_curated_node_wins_a_label_collision(tmp_path, monkeypatch, crawled_first):
    m = _build(tmp_path, monkeypatch, {"curated": "Nav1.7"}, crawled={"crawled": "Nav1.7"},
               crawled_first=crawled_first)
    assert m.match_entity("Nav1.7").matched_node_id == "curated"


def test_curated_nodes_still_match_loosely_next_to_crawled_ones(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"r": "RhoA GTPase"}, crawled={"c": "RhoA signalling in spinal cord"})
    assert m.match_entity("RhoA").matched_node_id == "r"


# --- real graph: false merges seen in the survey -------------------------------

@pytest.fixture(scope="module")
def real(curated_graph_file):
    return EntityMatcher(graph_path=str(curated_graph_file))


@pytest.mark.parametrize("name", [
    "Receptor", "kinase", "Zorblax-9 kinase", "Zorblax9 protein",
    "dorsal root ganglion", "spinal cord", "Caspase-2", "Nav1.6",
])
def test_real_graph_has_no_false_merge_for(real, name):
    assert real.match_entity(name).status == "NO_MATCH"


@pytest.mark.parametrize("name, wrong", [
    ("JAK1", "baricitinib"), ("JAK2", "axis"), ("STAT3", "axis"),
    ("Rac1", "kalirin"), ("CGRP receptor", "tie2"), ("KCC2", "downregulation"),
    ("RhoA", "simvastatin"),
])
def test_real_graph_does_not_merge_into_the_wrong_node(real, name, wrong):
    label = (real.match_entity(name).matched_label or "").lower()
    assert wrong not in label


def test_real_graph_resolves_slc12a5_to_the_kcc2_transporter(real):
    result = real.match_entity("SLC12A5")
    assert result.status == "ALIAS"
    assert result.matched_label.startswith("KCC2")
    assert "downregulation" not in result.matched_label.lower()


@pytest.mark.parametrize("name, expected", [
    ("IL-6", "IL-6"), ("Caspase-1", "Caspase-1"), ("Nav1.7", "Nav1.7"),
    ("TNF-alpha", "Tumor Necrosis Factor"), ("TrkB receptor", "TrkB"),
    ("RhoA", "RhoA GTPase"), ("Kalirin", "Kalirin-7"),
])
def test_real_graph_still_resolves_legitimate_names(real, name, expected):
    assert (real.match_entity(name).matched_label or "").startswith(expected)
