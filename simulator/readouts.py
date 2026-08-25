"""Population readouts computed from agent states and card labels.

Matching is lowercase substring against card labels AND restricted per
readout to appropriate entity types (pain reports are symptoms; inflam-
mation mediators are molecular species/pathways; barriers are anatomical
structures). Matched-id sets are sorted so results are deterministic
regardless of dict insertion order. Empty match convention: a mean over
an empty match set is defined as 0.0, so pain_score/inflammation_index
report 0.0 when nothing matches; barrier nodes model leak/disruption by
HIGH activity, therefore barrier_integrity = 1 - mean(matched barrier
states), which yields 1.0 when no barrier node matches (no modeled
disruption).
"""

from simulator.schemas import AgentCard, Readout

PAIN_LABELS = ["allodynia", "hyperalgesia", "pain"]
PAIN_ENTITY_TYPES = {"symptom"}
INFLAMMATION_LABELS = ["tnf", "il-1", "il-6", "nlrp3", "prostaglandin", "pge2"]
INFLAMMATION_ENTITY_TYPES = {"molecule", "receptor", "channel", "pathway", "process"}
BARRIER_LABELS = [
    "blood-brain barrier",
    "blood-spinal cord barrier",
    "bbb",
    "bscb",
    "barrier integrity",
    "vascular permeability",
]
BARRIER_ENTITY_TYPES = {"structure"}


def _matched_ids(
    labels: list[str],
    allowed_types: set[str],
    cards_by_id: dict[str, AgentCard],
) -> list[str]:
    return sorted(
        cid
        for cid, card in cards_by_id.items()
        if card.entity_type in allowed_types and any(s in card.label.lower() for s in labels)
    )


def _mean_or_zero(ids: list[str], states_by_id: dict[str, float]) -> float:
    if not ids:
        return 0.0
    return sum(states_by_id[cid] for cid in ids) / len(ids)


def compute_readouts(
    states_by_id: dict[str, float], cards_by_id: dict[str, AgentCard]
) -> Readout:
    pain_ids = _matched_ids(PAIN_LABELS, PAIN_ENTITY_TYPES, cards_by_id)
    inflammation_ids = _matched_ids(
        INFLAMMATION_LABELS, INFLAMMATION_ENTITY_TYPES, cards_by_id
    )
    barrier_ids = _matched_ids(BARRIER_LABELS, BARRIER_ENTITY_TYPES, cards_by_id)
    pain = _mean_or_zero(pain_ids, states_by_id)
    inflammation = _mean_or_zero(inflammation_ids, states_by_id)
    barrier_integrity = 1.0 - _mean_or_zero(barrier_ids, states_by_id)
    return Readout(
        pain_score=pain,
        barrier_integrity=barrier_integrity,
        inflammation_index=inflammation,
    )
