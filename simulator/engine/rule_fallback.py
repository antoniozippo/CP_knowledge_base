"""Deterministic rule-based state transition used when the LLM path is
unavailable or disabled.

Dynamics (all constants module-level):
    influence I = sum(weight * sign * sender_state) over inbound packets
    drug pressure p is added to I
    target      = sigmoid(SIGMOID_GAIN_K * (I + p))
    next        = current + STATE_RELAX_ALPHA * (target - current)
    next       += BASELINE_PULL_BETA * (baseline - current)
    clamp to [0, 1]
"""

import math

from simulator.schemas import AgentCard, InfluencePacket

SIGMOID_GAIN_K = 3.0
STATE_RELAX_ALPHA = 0.35
BASELINE_PULL_BETA = 0.02


def compute_influence(packets: list[InfluencePacket]) -> float:
    return sum(packet.weight * packet.sign * packet.sender_state for packet in packets)


def rule_next_state(
    card: AgentCard,
    current: float,
    packets: list[InfluencePacket],
    drug_pressure: float = 0.0,
) -> float:
    influence = compute_influence(packets)
    target = 1.0 / (1.0 + math.exp(-SIGMOID_GAIN_K * (influence + drug_pressure)))
    relaxed = current + STATE_RELAX_ALPHA * (target - current)
    pulled = relaxed + BASELINE_PULL_BETA * (card.baseline_state - current)
    return min(1.0, max(0.0, pulled))
