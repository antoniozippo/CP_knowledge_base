import math

import pytest

from simulator.engine.rule_fallback import (
    BASELINE_PULL_BETA,
    DEVIATION_GAIN,
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


def pkt(sign, weight, sender_state, sender_baseline, source_id="src", tick=0):
    return InfluencePacket(
        source_id=source_id,
        sign=sign,
        weight=weight,
        sender_state=sender_state,
        sender_baseline=sender_baseline,
        tick=tick,
    )


def test_module_constants_documented_values():
    assert DEVIATION_GAIN == 0.8
    assert STATE_RELAX_ALPHA == 0.35
    assert BASELINE_PULL_BETA == 0.02


def test_compute_influence_is_deviation_weighted():
    packets = [pkt(+1, 0.5, 0.8, 0.3), pkt(-1, 0.25, 0.4, 0.8)]
    assert compute_influence(packets) == pytest.approx(0.5 * 1 * 0.5 - 0.25 * 1 * (-0.4))
    assert compute_influence(packets) == pytest.approx(0.35)


def test_compute_influence_empty_is_zero():
    assert compute_influence([]) == 0.0


def test_rest_state_preserved_exactly():
    card = make_card(baseline=0.42)
    packets = [pkt(+1, 1.0, 0.7, 0.7), pkt(-1, 0.5, 0.2, 0.2)]
    assert rule_next_state(card, 0.42, packets) == 0.42
    assert rule_next_state(card, 0.42, []) == 0.42


def test_rule_next_state_full_formula_numeric():
    card = make_card(baseline=0.2)
    current = 0.2
    packets = [pkt(+1, 1.0, 1.0, 0.3)]
    excitation = (1.0 - 0.3) + 0.3
    target = min(1.0, max(0.0, 0.2 + 0.8 * math.tanh(excitation)))
    expected = current + 0.35 * (target - current)
    expected += 0.02 * (card.baseline_state - current)
    result = rule_next_state(card, current, packets, drug_pressure=0.3)
    assert result == pytest.approx(expected)
    assert result == pytest.approx(0.41324636, abs=1e-7)


def test_positive_deviation_chain_propagates_sign_correctly():
    card = make_card(baseline=0.5)
    rest = rule_next_state(card, 0.5, [])
    excited = rule_next_state(card, 0.5, [pkt(+1, 0.9, 0.9, 0.4)])
    inhibited = rule_next_state(card, 0.5, [pkt(-1, 0.9, 0.9, 0.4)])
    assert excited > rest > inhibited


def test_drug_pressure_shifts_up_and_down():
    card = make_card(baseline=0.5)
    base = rule_next_state(card, 0.4, [])
    boosted = rule_next_state(card, 0.4, [], drug_pressure=1.0)
    suppressed = rule_next_state(card, 0.4, [], drug_pressure=-1.0)
    assert boosted > base > suppressed


def test_target_clamps_and_output_bounded_at_extremes():
    card = make_card(baseline=0.9)
    hi = rule_next_state(card, 0.9, [pkt(+1, 1.0, 1.0, 0.0)], drug_pressure=50.0)
    lo = rule_next_state(card, 0.0, [pkt(-1, 1.0, 1.0, 1.0)], drug_pressure=-50.0)
    assert 0.0 <= hi <= 1.0
    assert 0.0 <= lo <= 1.0
    saturated = 0.9 + STATE_RELAX_ALPHA * (min(1.0, 0.9 + DEVIATION_GAIN) - 0.9)
    saturated += BASELINE_PULL_BETA * (0.9 - 0.9)
    assert hi == pytest.approx(saturated)


def test_sender_baseline_defaults_keep_packet_contract():
    p = InfluencePacket(source_id="s", sign=1, weight=1.0, sender_state=0.5, tick=0)
    assert p.sender_baseline == 0.5
