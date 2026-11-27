"""Tests for analysis/scripts/build_perturbation_cases.py: parsing rules and case logic."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_perturbation_cases as bp  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return bp.Config()


class SG:
    """The parts of graph_inference.SignedGraph that make_case uses."""
    pain = {"allo"}
    drugs = {"drugx"}


def ground_from(table):
    return lambda name: table.get(name, (None, None))


CTX = {"models": {"CCI"}, "other": set(), "species": {"rat"}, "paper_type": "primary"}


def case(cfg, subject, obj, sign, quote, table, ctx=CTX, obj_node="allo", obj_label="mechanical allodynia"):
    rel = {"subject": subject, "predicate": "x", "object": obj, "sign": sign, "evidence_quote": quote}
    rclass, inverted = bp.readout_of(obj_node, obj_label, SG, cfg)
    return bp.make_case("1", rel, obj_node, obj_label, rclass, inverted, ctx, SG, ground_from(table), cfg)


def test_an_agent_names_its_target_as_the_actor(cfg):
    assert bp.parse_actor("TLR4 siRNA", cfg) == ("TLR4", "loss")
    assert bp.parse_actor("P2X7R antagonist", cfg) == ("P2X7R", "loss")
    assert bp.parse_actor("knockdown of MLKL", cfg) == ("MLKL", "loss")
    assert bp.parse_actor("anti-NGF antibody", cfg) == ("NGF", "loss")
    assert bp.parse_actor("mGluR5 overexpression", cfg) == ("mGluR5", "gain")
    assert bp.parse_actor("MCC950", cfg) == ("MCC950", None)


def test_antagonistic_role_is_not_a_loss_experiment(cfg):
    assert bp.perturbation_from_quote("GLP-1 analogs play an antagonistic role in regulating TRPV1", cfg) is None
    assert bp.perturbation_from_quote("Knockdown of SPP1 increased the PWT", cfg) == "loss"
    assert bp.perturbation_from_quote("overexpressing Clec7a exacerbated allodynia", cfg) == "gain"


def test_a_knockdown_that_relieves_pain_implies_the_actor_drives_pain(cfg):
    c = case(cfg, "MLKL", "mechanical allodynia", 1, "MLKL siRNA could partially alleviate allodynia induced by CCI in rats",
             {"MLKL": ("mlkl", "MLKL")})
    assert (c["perturbation"], c["implied_sign"], c["observed_change"], c["status"]) == ("loss", 1, -1, "primary")


def test_an_agent_subject_flips_the_sign_back_to_the_actor(cfg):
    # "TLR4 siRNA inhibits allodynia" (-1): TLR4 itself drives pain (+1)
    c = case(cfg, "TLR4 siRNA", "mechanical allodynia", -1, "TLR4 siRNA reduced allodynia after CCI in rats",
             {"TLR4": ("tlr4", "TLR4")})
    assert (c["actor_node"], c["perturbation"], c["implied_sign"], c["observed_change"]) == ("tlr4", "loss", 1, -1)


def test_a_withdrawal_threshold_is_an_inverted_pain_readout(cfg):
    c = case(cfg, "drugX", "paw withdrawal threshold", 1, "drugX raised the paw withdrawal threshold in CCI rats",
             {"drugX": ("drugx", "drugX")}, obj_node="pwt", obj_label="paw withdrawal threshold")
    assert c["readout_class"] == "pain" and c["inverted"] == 1
    assert (c["perturbation"], c["implied_sign"], c["observed_change"]) == ("drug", -1, -1)


def test_antinociception_counts_as_less_pain(cfg):
    rclass, inverted = bp.readout_of("anti", "antinociception", SG, cfg)
    assert (rclass, inverted) == ("pain", True)


def test_context_comes_from_the_quote_and_the_readout_label(cfg):
    table = {"drugX": ("drugx", "drugX")}
    c = case(cfg, "drugX", "allodynia", -1, "drugX reduced allodynia in CFA mice", table)
    assert c["status"] == "excluded: other model (quote)"
    c = case(cfg, "drugX", "oxaliplatin-induced mechanical allodynia", -1, "drugX reduced allodynia", table,
             obj_label="oxaliplatin-induced mechanical allodynia")
    assert c["status"] == "excluded: other model (quote)"
    c = case(cfg, "drugX", "allodynia", -1, "drugX reduced allodynia in BV2 cells", table)
    assert c["status"] == "excluded: cell culture (quote)"
    c = case(cfg, "drugX", "allodynia", -1, "drugX reduced allodynia", table,
             ctx={"models": set(), "other": set(), "species": {"rat"}, "paper_type": "primary"})
    assert c["status"] == "excluded: other or unstated model"


def test_null_results_and_ungrounded_actors_are_excluded(cfg):
    c = case(cfg, "drugX", "allodynia", -1, "drugX did not alter allodynia after CCI", {"drugX": ("drugx", "drugX")})
    assert c["status"] == "excluded: null result"
    c = case(cfg, "unknown", "allodynia", -1, "inhibitor of unknown reduced allodynia after CCI", {})
    assert c["status"] == "excluded: actor not in graph"


def test_a_drug_acting_on_its_named_target_is_not_a_test(cfg):
    cfg.markers.setdefault("trpv1", "TRPV1")
    c = case(cfg, "drugX", "TRPV1", -1, "the TRPV1 antagonist drugX reduced responses after CCI in rats",
             {"drugX": ("drugx", "drugX")}, obj_node="trpv1", obj_label="TRPV1")
    assert c["status"] == "excluded: drug and its own target"


def test_repeats_merge_and_the_split_holds_out_the_latest_papers():
    base = {"actor_node": "a", "actor": "a", "perturbation": "loss", "readout_node": "r", "status": "primary",
            "implied_sign": 1, "flags": ""}
    cases = [dict(base, pmid="10"), dict(base, pmid="10"), dict(base, pmid="20"), dict(base, pmid="30"), dict(base, pmid="40")]
    merged = bp.merge_repeats(cases)
    assert len(merged) == 4 and merged[0]["repeats"] == 2
    cut = bp.assign_split(merged, 0.25)
    assert cut == 40 and [c["split"] for c in merged] == ["build", "build", "build", "test"]
