# crawler/tests/test_matcher_precision.py
# Entity matching must prefer a missed merge over a wrong one: a wrong merge
# attaches evidence to the wrong node. Synthetic cases pin the rules; the
# real-graph table pins the false merges observed in the first survey.

import json

import pytest
import yaml

from crawler import matcher as matcher_module
from crawler.matcher import EntityMatcher


def _build(tmp_path, monkeypatch, labels, edges=(), aliases=None):
    """labels: {node_id: label}; edges: [(source_id, target_id)] for degree."""
    nodes = [{"id": i, "label": lab, "norm_label": lab.lower()} for i, lab in labels.items()]
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


# --- real graph: false merges seen in the survey -------------------------------

@pytest.fixture(scope="module")
def real():
    return EntityMatcher(graph_path="graphify-out/graph_v2.json")


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
