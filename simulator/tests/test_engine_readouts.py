import pytest

from simulator.readouts import (
    BARRIER_ENTITY_TYPES,
    BARRIER_LABELS,
    INFLAMMATION_ENTITY_TYPES,
    INFLAMMATION_LABELS,
    PAIN_ENTITY_TYPES,
    PAIN_LABELS,
    compute_readouts,
)
from simulator.schemas import AgentCard, AgentTier, Readout


def card(cid, label, entity_type="molecule", baseline=0.5):
    return AgentCard(
        id=cid,
        label=label,
        entity_type=entity_type,
        compartment="other",
        tier=AgentTier.MID,
        community=0,
        baseline_state=baseline,
    )


def test_label_sets_and_entity_restrictions():
    assert PAIN_LABELS == ["allodynia", "hyperalgesia", "pain"]
    assert PAIN_ENTITY_TYPES == {"symptom"}
    assert INFLAMMATION_LABELS == ["tnf", "il-1", "il-6", "nlrp3", "prostaglandin", "pge2"]
    assert INFLAMMATION_ENTITY_TYPES == {"molecule", "receptor", "channel", "pathway", "process"}
    assert BARRIER_LABELS == [
        "blood-brain barrier",
        "blood-spinal cord barrier",
        "bbb",
        "bscb",
        "barrier integrity",
        "vascular permeability",
    ]
    assert BARRIER_ENTITY_TYPES == {"structure"}


def test_pain_restricted_to_symptom_entities():
    cards = {
        "s": card("s", "Mechanical Hyperalgesia", entity_type="symptom", baseline=0.2),
        "c": card("c", "Pain-Related Anxiety concept", entity_type="concept", baseline=0.9),
        "m": card("m", "pain pathway molecule", entity_type="molecule", baseline=0.8),
    }
    states = {"s": 0.2, "c": 0.9, "m": 0.8}
    r = compute_readouts(states, cards)
    assert r.pain_score == pytest.approx(0.2)


def test_inflammation_entity_types_gate_matching():
    cards = {
        "mol": card("mol", "TNF-alpha", entity_type="molecule", baseline=0.6),
        "rec": card("rec", "TNFR1 receptor", entity_type="receptor", baseline=0.4),
        "sym": card("sym", "TNF-driven pain symptom", entity_type="symptom", baseline=0.95),
        "con": card("con", "NLRP3 concept", entity_type="concept", baseline=0.85),
    }
    states = {"mol": 0.6, "rec": 0.4, "sym": 0.95, "con": 0.85}
    r = compute_readouts(states, cards)
    assert r.inflammation_index == pytest.approx(0.5)


def test_barrier_requires_structure_entity():
    cards = {
        "st": card("st", "Blood-Brain Barrier (BBB)", entity_type="structure", baseline=0.3),
        "mo": card("mo", "BBB tight junction proteins", entity_type="molecule", baseline=0.99),
        "pa": card("pa", "bbb remodeling pathway", entity_type="pathway", baseline=0.01),
    }
    states = {"st": 0.3, "mo": 0.99, "pa": 0.01}
    r = compute_readouts(states, cards)
    assert r.barrier_integrity == pytest.approx(1.0 - 0.3)


def test_pain_and_inflammation_means():
    cards = {
        "a": card("a", "Mechanical Hyperalgesia", "symptom", 0.2),
        "b": card("b", "TNF-alpha molecule", "molecule", 0.6),
        "c": card("c", "PGE2 synthase", "molecule", 0.8),
        "d": card("d", "Unrelated Potassium Channel", "channel", 0.9),
    }
    states = {"a": 0.2, "b": 0.6, "c": 0.8, "d": 0.9}
    r = compute_readouts(states, cards)
    assert isinstance(r, Readout)
    assert r.pain_score == pytest.approx(0.2)
    assert r.inflammation_index == pytest.approx((0.6 + 0.8) / 2)


def test_barrier_inversion():
    cards = {
        "b1": card("b1", "Blood-Brain Barrier (BBB)", "structure", 0.3),
        "b2": card("b2", "blood-spinal cord barrier", "structure", 0.7),
        "x": card("x", "Calpain", "molecule", 0.99),
    }
    states = {"b1": 0.3, "b2": 0.7, "x": 0.99}
    r = compute_readouts(states, cards)
    assert r.barrier_integrity == pytest.approx(1.0 - 0.5)


def test_empty_match_sets_use_zero_mean_convention():
    cards = {"z": card("z", "Potassium Channel", "channel")}
    states = {"z": 0.77}
    r = compute_readouts(states, cards)
    assert r.pain_score == 0.0
    assert r.inflammation_index == 0.0
    assert r.barrier_integrity == pytest.approx(1.0)


def test_deterministic_regardless_of_dict_order():
    cards_a = {
        "a": card("a", "Allodynia", "symptom", 0.1),
        "b": card("b", "BBB", "structure", 0.2),
        "c": card("c", "IL-6", "molecule", 0.3),
    }
    cards_b = dict(reversed(list(cards_a.items())))
    states = {"a": 0.1, "b": 0.2, "c": 0.3}
    assert compute_readouts(states, cards_a) == compute_readouts(states, cards_b)
