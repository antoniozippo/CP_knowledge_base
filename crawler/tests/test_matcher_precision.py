# crawler/tests/test_matcher_precision.py
# Entity matching must prefer a missed merge over a wrong one: a wrong merge
# attaches evidence to the wrong node. Synthetic cases pin the rules; the
# real-graph table pins the false merges observed in the first survey.

import json

import pytest
import yaml

from crawler import matcher as matcher_module
from crawler.classify import normalize_label
from crawler.tokens import is_spelling_variant, skeleton
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


# --- context-specific curated nodes (crawler/context_nodes.yaml) ---------------------

def _build_ctx(tmp_path, monkeypatch, labels, ctx_ids):
    cfg = tmp_path / "context_nodes.yaml"
    cfg.write_text(yaml.safe_dump({"context_nodes": [{"id": i, "note": "test"} for i in ctx_ids]}))
    monkeypatch.setattr(matcher_module, "CONTEXT_NODES_PATH", cfg)
    return _build(tmp_path, monkeypatch, labels)


def test_general_name_does_not_merge_into_a_context_node(tmp_path, monkeypatch):
    m = _build_ctx(tmp_path, monkeypatch, {"c": "Cannabidiol (CBD) as PPARγ Agonist", "p": "PPARγ"}, ["c"])
    assert m.match_entity("cannabidiol").status == "NO_MATCH"
    assert m.match_entity("CBD").status == "NO_MATCH"          # would hit the "(CBD)" group otherwise


def test_context_node_is_still_reached_by_its_exact_label(tmp_path, monkeypatch):
    m = _build_ctx(tmp_path, monkeypatch, {"c": "Cannabidiol (CBD) as PPARγ Agonist"}, ["c"])
    result = m.match_entity("Cannabidiol (CBD) as PPARγ Agonist")
    assert (result.status, result.matched_node_id) == ("EXACT", "c")


def test_context_node_is_still_reached_through_an_alias(tmp_path, monkeypatch):
    cfg = tmp_path / "context_nodes.yaml"
    cfg.write_text(yaml.safe_dump({"context_nodes": [{"id": "c"}]}))
    monkeypatch.setattr(matcher_module, "CONTEXT_NODES_PATH", cfg)
    m = _build(tmp_path, monkeypatch, {"c": "ERK5 Pathway (CX3CL1 context)"}, aliases={"CX3CL1-ERK5": ["ERK5 Pathway (CX3CL1 context)"]})
    assert m.match_entity("CX3CL1-ERK5").matched_node_id == "c"


def test_general_name_falls_back_to_the_general_node_not_the_context_one(tmp_path, monkeypatch):
    labels = {"ctx": "NF-κB Pathway (Bradykinin Context)", "gen": "NF-κB"}
    m = _build_ctx(tmp_path, monkeypatch, labels, ["ctx"])
    assert m.match_entity("NF-κB signaling").matched_node_id == "gen"


def test_context_node_is_not_a_fuzzy_target(tmp_path, monkeypatch):
    m = _build_ctx(tmp_path, monkeypatch, {"c": "ERK5 Pathway Context"}, ["c"])
    assert m.match_entity("ERK5 Pathway Contexts").status == "NO_MATCH"


def test_every_context_node_in_the_config_exists_in_the_real_graph(curated_graph_file):
    ids = EntityMatcher(graph_path=str(curated_graph_file)).context_node_ids
    nodes = {n["id"] for n in json.loads(curated_graph_file.read_text())["nodes"]}
    assert ids and ids <= nodes, sorted(ids - nodes)


@pytest.mark.parametrize("name", [
    "cannabidiol", "Cannabidiol", "CBD", "NF-κB pathway", "NF-κB signaling", "ERK5",
    "mitochondrial dysfunction", "MAPK pathway", "JAK/STAT3 signaling", "Nrf2/HO-1",
])
def test_real_graph_general_names_do_not_land_on_a_context_node(real, name):
    assert real.match_entity(name).matched_node_id not in real.context_node_ids


@pytest.mark.parametrize("name, expected", [
    ("spinal microglia", "Spinal Microglia (Activated)"),
    ("chronic pain", "Chronic Pain Neurobiology"),
    ("CaMKII", "CaMKII (LTP Kinase"),
    ("pyroptosis", "Pyroptosis (P2X7-GSDMD"),
])
def test_real_graph_nodes_whose_qualifier_is_not_a_context_still_merge(real, name, expected):
    assert (real.match_entity(name).matched_label or "").startswith(expected)


# --- fuzzy rule: a spelling variant, never a different short identifier ----------------

@pytest.mark.parametrize("a, b", [
    ("caspase3", "caspase-3"), ("TREM-2", "TREM2"), ("neuro-inflammation", "Neuroinflammation"),
    ("NFκB", "NF-κB"), ("Rho/Rock pathway", "RhoA/ROCK Pathway"), ("SST2A receptor", "SSTR2a Receptor"),
    ("parvalbumin interneurons", "Parvalbumin (PV) Interneurons"),
])
def test_spelling_variants_are_recognised(a, b):
    assert is_spelling_variant(skeleton(a), skeleton(b)) or is_spelling_variant(skeleton(a), skeleton(b.split("(")[0] + b.split(")")[-1]))


@pytest.mark.parametrize("a, b", [
    ("EP2 receptor", "Tie2 receptor"), ("MT2 receptor", "Tie2 receptor"), ("PAC1 receptor", "EphA1 receptor"),
    ("tenascin-C", "Tenascin-R"), ("Rho GTPase", "RhoA GTPase"), ("Caspase-1", "Caspase-3"),
    ("lamina I spino-PAG projection neurons", "Lamina I Spinoparabrachial Projection Neurons"),
    ("RhoA/YAP signaling pathway", "RhoA/ROCK Signalling Pathway"),
])
def test_different_short_identifiers_are_not_spelling_variants(a, b):
    assert not is_spelling_variant(skeleton(a), skeleton(b))


@pytest.mark.parametrize("name, label", [
    ("EP2 receptor", "Tie2 Receptor"), ("MT2 receptor", "Tie2 Receptor"), ("PAC1 receptor", "EphA1 Receptor"),
    ("tenascin-C", "Tenascin-R"),
])
def test_fuzzy_rule_does_not_merge_short_identifiers_that_differ(tmp_path, monkeypatch, name, label):
    m = _build(tmp_path, monkeypatch, {"n": label})
    assert m.match_entity(name).status == "NO_MATCH"


def test_fuzzy_rule_still_merges_a_spelling_variant(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "Caspase-3", "o": "Parvalbumin (PV) Interneurons"})
    assert m.match_entity("caspase3").matched_node_id == "n"
    assert m.match_entity("parvalbumin interneurons").matched_node_id == "o"


# --- a "(...)" group is an alias only for a symbol or an expansion, not a description ----

@pytest.mark.parametrize("name, label", [
    ("neurite outgrowth", "DRG Kalirin-7 (Neurite Outgrowth)"),
    ("cognitive deficits", "Hippocampus Kalirin-7 (Cognitive Deficits)"),
    ("diabetic neuropathy", "O-GlcNAc Glycosylation of Cav3.2 (diabetic neuropathy)"),
    ("pain chronification", "CXCL12/CXCR4 Positive-Feedback Loop (pain chronification)"),
])
def test_a_descriptive_parenthetical_phrase_is_not_an_alias(tmp_path, monkeypatch, name, label):
    m = _build(tmp_path, monkeypatch, {"n": label})
    assert m.match_entity(name).status == "NO_MATCH"


@pytest.mark.parametrize("name, label", [
    ("SCN9A", "Nav1.7 (SCN9A)"),                                  # a symbol in the group
    ("TNF-alpha", "Tumor Necrosis Factor Alpha (TNF-α)"),         # one-word symbol, multi-word head
    ("IGF1R", "IGF1 Receptor (IGF1R)"),
    ("Potassium-Chloride Cotransporter", "KCC2 (Potassium-Chloride Cotransporter)"),   # expansion of a one-word head
])
def test_a_symbol_or_expansion_in_parentheses_is_still_an_alias(tmp_path, monkeypatch, name, label):
    m = _build(tmp_path, monkeypatch, {"n": label})
    assert m.match_entity(name).matched_node_id == "n"


# --- reviewed no-merge pairs (crawler/no_merge.yaml) ---------------------------------

def _build_nm(tmp_path, monkeypatch, labels, pairs):
    cfg = tmp_path / "no_merge.yaml"
    cfg.write_text(yaml.safe_dump({"no_merge": [{"node": n, "names": names, "reason": "test"} for n, names in pairs.items()]}))
    monkeypatch.setattr(matcher_module, "NO_MERGE_PATH", cfg)
    return _build(tmp_path, monkeypatch, labels)


def test_a_listed_pair_is_not_merged_by_the_loose_rules(tmp_path, monkeypatch):
    m = _build_nm(tmp_path, monkeypatch, {"s": "Spared Nerve Injury (SNI) Model"}, {"s": ["nerve injury"]})
    assert m.match_entity("nerve injury").status == "NO_MATCH"
    assert m.match_entity("Nerve Injury").status == "NO_MATCH"            # matched lowercased


def test_a_listed_pair_does_not_affect_other_names_or_nodes(tmp_path, monkeypatch):
    labels = {"s": "Spared Nerve Injury (SNI) Model", "c": "Chronic Constriction Injury (CCI) Model"}
    m = _build_nm(tmp_path, monkeypatch, labels, {"s": ["nerve injury"]})
    assert m.match_entity("spared nerve injury").matched_node_id == "s"
    assert m.match_entity("chronic constriction injury").matched_node_id == "c"


def test_a_listed_pair_is_still_reached_by_exact_label(tmp_path, monkeypatch):
    m = _build_nm(tmp_path, monkeypatch, {"n": "Nerve Injury"}, {"n": ["nerve injury"]})
    assert m.match_entity("nerve injury").status == "EXACT"


def test_the_listed_pairs_exist_in_the_real_graph(curated_graph_file):
    m = EntityMatcher(graph_path=str(curated_graph_file))
    assert m._no_merge, "no_merge.yaml is empty or missing"
    assert {node for _, node in m._no_merge} <= set(m.nodes_by_id), sorted({n for _, n in m._no_merge} - set(m.nodes_by_id))


@pytest.mark.parametrize("name, wrong", [
    ("nerve injury", "Spared Nerve Injury"), ("chondroitin sulfate", "Proteoglycans"), ("T-type calcium channels", "Cav3.2"),
    ("matrix metalloproteinases", "Matrix Metalloproteinase"), ("SST interneurons", "Silencing"), ("PGC-1α", "PGC-1"),
    ("MPTP", "Permeability"), ("deep brain stimulation", "Stimulation of ACC"), ("EP2 receptor", "Tie2"), ("MT2 receptor", "Tie2"),
    ("PAC1 receptor", "EphA1"), ("tenascin-C", "Tenascin-R"), ("diabetic neuropathy", "O-GlcNAc"), ("neurite outgrowth", "Kalirin-7"),
    ("cognitive deficits", "Kalirin-7"), ("IGF1", "Receptor"), ("lamina I projection neurons", "Spinoparabrachial"), ("ACC LTP", "Presynaptic"),
])
def test_real_graph_review_findings_no_longer_merge(real, name, wrong):
    assert wrong.lower() not in (real.match_entity(name).matched_label or "").lower()


# --- one-word symbols written with other punctuation ----------------------------------------

@pytest.mark.parametrize("name, label", [
    ("MMP9", "Matrix Metalloproteinase-9 (MMP-9)"), ("VEGF-A", "Vascular Endothelial Growth Factor A (VEGFA)"),
    ("HIF-1α", "Hypoxia-Inducible Factor 1 Alpha (HIF1α)"), ("TLR-4", "TLR4 (Toll-like Receptor 4)"),
    ("Tnfα", "Tumor Necrosis Factor Alpha (TNF-α)"), ("COX2", "COX-2 (Cyclooxygenase-2)"),
    ("PSD95", "PSD-95 (Postsynaptic Density Scaffold Protein)"), ("Tie-2", "Tie2 Receptor"),
    ("P2X7R", "P2X7 Receptor (P2RX7)"), ("TIMP1", "TIMP-1"), ("IL1β", "IL-1beta (NLRP3 effector cytokine)"),
])
def test_a_symbol_spelled_with_other_punctuation_merges(tmp_path, monkeypatch, name, label):
    m = _build(tmp_path, monkeypatch, {"n": label, "o": "BDNF"})
    assert m.match_entity(name).matched_node_id == "n"


def test_a_receptor_symbol_stays_the_receptor_and_does_not_become_its_ligand(tmp_path, monkeypatch):
    labels = {"lig": "CSF1 (Colony-Stimulating Factor 1)", "rec": "CSF1R (receptor tyrosine kinase)", "o": "Other"}
    m = _build(tmp_path, monkeypatch, labels, edges=[("lig", "o")] * 6)      # the ligand is better connected
    assert m.match_entity("CSF1R").matched_node_id == "rec"
    assert m.match_entity("CSF-1").matched_node_id == "lig"


def test_a_trailing_receptor_r_is_dropped_only_when_no_node_owns_the_name(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "P2X4 Receptor"})
    assert m.match_entity("P2X4R").matched_node_id == "n"


def test_a_family_node_is_not_the_symbol_of_one_member(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "BCL-2 Family Proteins (BAX, BAK, BIM, BCL-2, BCL-xL)"})
    assert m.match_entity("Bcl2").status == "NO_MATCH"


def test_the_symbol_rule_does_not_touch_multi_word_names(tmp_path, monkeypatch):
    m = _build(tmp_path, monkeypatch, {"n": "TLR4 (Toll-like Receptor 4)"})
    assert m.match_entity("TLR 4 signaling cascade").status == "NO_MATCH"


def test_a_no_merge_entry_blocks_every_spelling_of_the_name(tmp_path, monkeypatch):
    labels = {"r": "IGF1 Receptor (IGF1R)", "l": "Insulin-like Growth Factor 1 (IGF1)"}
    m = _build_nm(tmp_path, monkeypatch, labels, {"r": ["igf1"]})
    for spelling in ("IGF1", "IGF-1", "igf-1"):
        assert m.match_entity(spelling).matched_node_id == "l"


@pytest.mark.parametrize("name, expected", [
    ("HIF-1α", "Hypoxia-Inducible Factor 1 Alpha"), ("P2X7R", "P2X7 Receptor"), ("P2X4R", "P2X4 Receptor"),
    ("MMP9", "MMP-9"), ("COX2", "COX-2"), ("TNFα", "Tumor Necrosis Factor Alpha"), ("IGF-1", "Insulin-like Growth Factor 1"),
    ("CSF1R", "CSF1R"), ("TLR-4", "TLR4"), ("PSD95", "PSD-95"), ("gepants", "Gepants"), ("CGRP receptor antagonists", "Gepants"),
    ("Protein kinase C", "PKC"),
])
def test_real_graph_duplicate_spellings_now_resolve_to_the_curated_node(real, name, expected):
    assert (real.match_entity(name).matched_label or "").startswith(expected)


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
