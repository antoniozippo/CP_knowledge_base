import math

import pytest

from simulator.engine.rule_fallback import (
    BASELINE_PULL_BETA,
    SIGMOID_GAIN_K,
    STATE_RELAX_ALPHA,
    compute_influence,
    rule_next_state,
)
from simulator.schemas import AgentCard, AgentTier, InfluencePacket


def make_card(baseline=0.5):
    return AgentCard(
        id="n1",
        label="node one",
        entity_type="molecule",
        compartment="other",
        tier=AgentTier.MID,
        community=0,
        baseline_state=baseline,
    )


def pkt(sign, weight, sender_state, source_id="src", tick=0):
    return InfluencePacket(
        source_id=source_id, sign=sign, weight=weight, sender_state=sender_state, tick=tick
    )


def test_module_constants_documented_values():
    assert SIGMOID_GAIN_K == 3.0
    assert STATE_RELAX_ALPHA == 0.35
    assert BASELINE_PULL_BETA == 0.02


def test_compute_influence_hand_computed():
    packets = [pkt(+1, 0.5, 0.8), pkt(-1, 0.25, 0.4)]
    assert compute_influence(packets) == pytest.approx(0.5 * 1 * 0.8 - 0.25 * 1 * 0.4)
    assert compute_influence(packets) == pytest.approx(0.3)


def test_compute_influence_empty_is_zero():
    assert compute_influence([]) == 0.0


def test_rule_next_state_full_formula_numeric():
    card = make_card(baseline=0.5)
    current = 0.2
    packets = [pkt(+1, 1.0, 1.0)]
    influence = 1.0
    target = 1.0 / (1.0 + math.exp(-3.0 * (influence + 0.5)))
    expected = 0.2 + 0.35 * (target - 0.2)
    expected += 0.02 * (0.5 - 0.2)
    result = rule_next_state(card, current, packets, drug_pressure=0.5)
    assert result == pytest.approx(expected)
    assert result == pytest.approx(0.48215457, abs=1e-7)


def test_rule_next_state_at_rest_stays_put():
    card = make_card(baseline=0.5)
    assert rule_next_state(card, 0.5, []) == pytest.approx(0.5)


def test_rule_next_state_positive_drug_raises_state():
    card = make_card(baseline=0.5)
    base = rule_next_state(card, 0.4, [])
    boosted = rule_next_state(card, 0.4, [], drug_pressure=1.0)
    assert boosted > base


def test_rule_next_state_clamps_extremes():
    card = make_card(baseline=1.0)
    hi = rule_next_state(card, 1.0, [pkt(+1, 1.0, 1.0)], drug_pressure=100.0)
    lo = rule_next_state(card, 0.0, [pkt(-1, 1.0, 1.0)], drug_pressure=-100.0)
    assert 0.0 <= hi <= 1.0
    assert 0.0 <= lo <= 1.0
