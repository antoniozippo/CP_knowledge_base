"""Deterministic rule-based state transition used when the LLM path is
unavailable or disabled.

Deviation-propagation dynamics (all constants module-level): senders
influence targets only through deviation from their OWN baseline, so a
system at rest stays exactly at rest.
    excitation E_i = sum(weight * sign * (sender_state - sender_baseline))
                   + drug_pressure
    target_i       = clamp01(baseline_i + DEVIATION_GAIN * tanh(E_i))
    next           = current + STATE_RELAX_ALPHA * (target - current)
    next          += BASELINE_PULL_BETA * (baseline - current)
    clamp to [0, 1]
"""

import math

from simulator.schemas import AgentCard, InfluencePacket

DEVIATION_GAIN = 0.8
STATE_RELAX_ALPHA = 0.35
BASELINE_PULL_BETA = 0.02


def compute_influence(packets: list[InfluencePacket]) -> float:
    return sum(
        packet.weight * packet.sign * (packet.sender_state - packet.sender_baseline)
        for packet in packets
    )


def rule_next_state(
    card: AgentCard,
    current: float,
    packets: list[InfluencePacket],
    drug_pressure: float = 0.0,
) -> float:
    excitation = compute_influence(packets) + drug_pressure
    target = min(
        1.0, max(0.0, card.baseline_state + DEVIATION_GAIN * math.tanh(excitation))
    )
    relaxed = current + STATE_RELAX_ALPHA * (target - current)
    pulled = relaxed + BASELINE_PULL_BETA * (card.baseline_state - current)
    return min(1.0, max(0.0, pulled))
