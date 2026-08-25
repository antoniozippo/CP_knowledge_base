"""Deterministic rule-based state transition used when the LLM path is
unavailable or disabled.

Deviation-propagation dynamics (all constants module-level): senders
influence targets only through deviation from their OWN baseline, so a
system at rest stays exactly at rest.
    excitation E_i = sum(weight * sign * (sender_state - sender_baseline))
                    + drug_pressure
                    + drive_pressure
    target_i       = clamp01(baseline_i + DEVIATION_GAIN * tanh(E_i))
    next           = current + STATE_RELAX_ALPHA * (target - current)
    next          += BASELINE_PULL_BETA * (baseline - current)
    clamp to [0, 1]

drive_pressure is the scenario's tonic-driver contribution: for every
SustainedDrive active at this tick (start_tick <= tick < end_tick, None end
= whole horizon) the orchestrator adds
(value - baseline_agent) * DRIVE_GAIN, modeling constant pronociceptive
sources such as ectopic firing or sustained glial activation. A drive is a
positive deviation by construction: it can only push the agent above its
baseline.
"""

import math

from simulator.schemas import AgentCard, InfluencePacket

DEVIATION_GAIN = 0.8
STATE_RELAX_ALPHA = 0.35
BASELINE_PULL_BETA = 0.02
DRIVE_GAIN = 1.0


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
    drive_pressure: float = 0.0,
) -> float:
    excitation = compute_influence(packets) + drug_pressure + drive_pressure
    target = min(
        1.0, max(0.0, card.baseline_state + DEVIATION_GAIN * math.tanh(excitation))
    )
    relaxed = current + STATE_RELAX_ALPHA * (target - current)
    pulled = relaxed + BASELINE_PULL_BETA * (card.baseline_state - current)
    return min(1.0, max(0.0, pulled))
