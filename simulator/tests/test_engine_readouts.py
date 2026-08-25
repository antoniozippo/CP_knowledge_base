import pytest

from simulator.readouts import (
    BARRIER_LABELS,
    INFLAMMATION_LABELS,
    PAIN_LABELS,
    compute_readouts,
)
from simulator.schemas import AgentCard, AgentTier, Readout


def card(cid, label, baseline=0.5):
    return AgentCard(
        id=cid,
        label=label,
        entity_type="molecule",
        compartment="other",
        tier=AgentTier.MID,
        community=0,
        baseline_state=baseline,
    )


def test_label_sets_contents():
    assert PAIN_LABELS == ["allodynia", "hyperalgesia", "pain"]
    assert INFLAMMATION_LABELS == ["tnf", "il-1", "il-6", "nlrp3", "prostaglandin", "pge2"]
    assert BARRIER_LABELS == [
        "blood-brain barrier",
        "blood-spinal cord barrier",
        "bbb",
        "bscb",
        "barrier integrity",
        "vascular permeability",
    ]


def test_pain_and_inflammation_means():
    cards = {
        "a": card("a", "Mechanical Hyperalgesia", 0.2),
        "b": card("b", "TNF-alpha molecule", 0.6),
        "c": card("c", "PGE2 synthase", 0.8),
        "d": card("d", "Unrelated Potassium Channel", 0.9),
    }
    states = {"a": 0.2, "b": 0.6, "c": 0.8, "d": 0.9}
    r = compute_readouts(states, cards)
    assert r.pain_score == pytest.approx(0.2)
    assert r.inflammation_index == pytest.approx((0.6 + 0.8) / 2)
    assert isinstance(r, Readout)


def test_barrier_inversion():
    cards = {
        "b1": card("b1", "Blood-Brain Barrier (BBB)", 0.3),
        "b2": card("b2", "blood-spinal cord barrier", 0.7),
        "x": card("x", "Calpain", 0.99),
    }
    states = {"b1": 0.3, "b2": 0.7, "x": 0.99}
    r = compute_readouts(states, cards)
    assert r.barrier_integrity == pytest.approx(1.0 - 0.5)


def test_empty_match_sets_use_zero_mean_convention():
    cards = {"z": card("z", "Potassium Channel")}
    states = {"z": 0.77}
    r = compute_readouts(states, cards)
    assert r.pain_score == 0.0
    assert r.inflammation_index == 0.0
    assert r.barrier_integrity == pytest.approx(1.0)


def test_matching_is_case_insensitive_substring():
    cards = {"p": card("p", "NeuroPATHIC PAIN model"), "t": card("t", "Tnf Receptor 1")}
    states = {"p": 0.4, "t": 0.44}
    r = compute_readouts(states, cards)
    assert r.pain_score == pytest.approx(0.4)
    assert r.inflammation_index == pytest.approx(0.44)


def test_deterministic_regardless_of_dict_order():
    cards_a = {
        "a": card("a", "Allodynia", 0.1),
        "b": card("b", "BBB", 0.2),
        "c": card("c", "IL-6", 0.3),
    }
    cards_b = dict(reversed(list(cards_a.items())))
    states = {"a": 0.1, "b": 0.2, "c": 0.3}
    assert compute_readouts(states, cards_a) == compute_readouts(states, cards_b)
