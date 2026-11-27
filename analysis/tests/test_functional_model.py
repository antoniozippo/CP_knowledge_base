"""Tests for analysis/scripts/functional_model.py: the engines and the baselines on tiny networks."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import functional_model as fm  # noqa: E402


def test_the_normalized_hill_function_is_anchored():
    m = fm.NetfluxModel(["a"], [], set())
    assert m.hill(np.array([0.0]), 1.0)[0] == pytest.approx(0.0)
    assert m.hill(np.array([0.5]), 1.0)[0] == pytest.approx(0.5)
    assert m.hill(np.array([1.0]), 0.8)[0] == pytest.approx(0.8)


@pytest.mark.parametrize("logic", ["or", "or-scaled", "mean"])
def test_removing_an_activator_lowers_its_target_and_removing_an_inhibitor_raises_it(logic):
    nodes = ["a", "b", "c", "d"]
    links = [("a", "b", 1, 1.0), ("c", "d", -1, 1.0)]
    m = fm.NetfluxModel(nodes, links, set(), basal=0.2, logic=logic)
    assert m.effect("a", "b", 0.0) < 0
    assert m.effect("c", "d", 0.0) > 0
    assert m.effect("a", "b", 1.0) > 0


def test_or_logic_saturates_a_hub_and_averaging_does_not():
    # thirty well-activated inputs, as at PAIN, TNF or TRPV1 in the canonical network
    nodes = ["hub"] + [f"x{i}" for i in range(30)]
    links = [(f"x{i}", "hub", 1, 1.0) for i in range(30)]
    or_model = fm.NetfluxModel(nodes, links, set(), basal=0.5, logic="or")
    mean_model = fm.NetfluxModel(nodes, links, set(), basal=0.5, logic="mean")
    assert fm.sign_of(or_model.effect("x0", "hub", 0.0)) == 0      # one of thirty inputs: no visible change
    assert mean_model.effect("x0", "hub", 0.0) < -1e-3


def test_exogenous_nodes_are_off_until_clamped():
    m = fm.NetfluxModel(["drug", "t"], [("drug", "t", -1, 1.0)], {"drug"}, basal=0.3)
    base = m.steady_state()
    assert base[m.index["drug"]] == 0.0
    assert m.effect("drug", "t", 1.0) < 0


def test_a_clamp_holds():
    m = fm.NetfluxModel(["a", "b"], [("a", "b", 1, 1.0)], set())
    y = m.steady_state({"a": 0.0})
    assert y[m.index["a"]] == 0.0


def test_boolean_chain_follows_its_activator():
    m = fm.BooleanModel(["a", "b", "c"], [("a", "b", 1, 1.0), ("b", "c", -1, 1.0)], set())
    assert m.effect("a", "b", 0.0) == pytest.approx(-1.0)
    assert m.effect("a", "c", 0.0) == pytest.approx(1.0)
    t = fm.BooleanModel(["a", "b", "x"], [("a", "b", 1, 1.0), ("x", "b", -1, 1.0)], set(), "threshold")
    assert t.effect("x", "b", 0.0) == pytest.approx(1.0)        # 1 activator vs 0 inhibitors once x is off


def test_static_effect_sums_signed_paths_and_skips_drugs():
    links = [("a", "b", -1, 1.0), ("b", "r", 1, 1.0), ("a", "r", -1, 0.5), ("a", "d", 1, 1.0), ("d", "r", 1, 1.0)]
    total = fm.static_effect(links, "a", "r", decay=0.5)
    assert total == pytest.approx(-0.5 - 0.5 + 0.5)                # a-|b->r, a-|r, a->d->r
    assert fm.static_effect(links, "a", "r", decay=0.5, avoid={"d"}) == pytest.approx(-1.0)


def test_a_case_cannot_use_a_link_whose_only_paper_is_its_own():
    crawled = {"source": "a", "target": "b", "sign": 1, "tiers": ["T1"], "papers": ["1"]}
    assert not fm.usable_for(crawled, "1") and fm.usable_for(crawled, "2")
    assert fm.usable_for({**crawled, "papers": ["1", "3"]}, "1")
    assert fm.usable_for({**crawled, "tiers": ["P"], "papers": []}, "1")
    assert fm.usable_for({**crawled, "target_annotation": True}, "1")


def test_select_links_filters_tiers_and_weights_them():
    network = {"links": [{"source": "a", "target": "b", "sign": 1, "tiers": ["T3"], "papers": ["1"]},
                         {"source": "b", "target": "c", "sign": -1, "tiers": ["P"]}]}
    assert fm.select_links(network, tiers={"P"}) == [("b", "c", -1, 1.0)]
    weighted = fm.select_links(network, tier_weights={"T3": 0.5, "P": 0.6})
    assert weighted == [("a", "b", 1, 0.5), ("b", "c", -1, 0.6)]
