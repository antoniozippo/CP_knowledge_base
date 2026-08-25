"""Tests for Part C sustained drives: tonic scenario-level excitation.

A SustainedDrive adds a constant positive deviation contribution
(value − baseline_agent) * DRIVE_GAIN into the agent's inbound excitation
(before tanh) while start_tick <= tick < end_tick (end None = through the
whole horizon). Naive scenarios declare none, so their trajectories are
unchanged; audit entries stay emitter='rules' and the delta cache is
untouched.
"""

import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from simulator.engine.orchestrator import Orchestrator
from simulator.engine.rule_fallback import (
    BASELINE_PULL_BETA,
    DEVIATION_GAIN,
    DRIVE_GAIN,
    STATE_RELAX_ALPHA,
)
from simulator.schemas import (
    AgentCard,
    AgentTier,
    Perturbation,
    ScenarioConfig,
    SustainedDrive,
)


def lone_agent_card():
    return AgentCard(
        id="ectopic",
        label="Ectopic Firing Driver",
        entity_type="process",
        compartment="periphery",
        tier=AgentTier.MID,
        community=0,
        baseline_state=0.5,
    )


def scenario(sustained_drives, name="drive_scen", horizon=10):
    return ScenarioConfig(
        name=name,
        horizon_days=horizon,
        injury_model="SNI",
        injury_tick=0,
        sustained_drives=sustained_drives,
        # non-naive scenarios must seed explicitly; seeding at baseline keeps
        # the system at rest so only the drive moves it
        initial_perturbations=[Perturbation(agent_id="ectopic", value=0.5)],
    )


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def test_sustained_drive_schema_bounds_and_defaults():
    d = SustainedDrive(agent_id="x", value=0.85, start_tick=0)
    assert d.end_tick is None
    assert d.value == 0.85
    with pytest.raises(ValidationError):
        SustainedDrive(agent_id="x", value=1.5, start_tick=0)
    with pytest.raises(ValidationError):
        SustainedDrive(agent_id="x", value=0.5, start_tick=-1)


def test_sustained_drive_window_must_be_ordered():
    with pytest.raises(ValidationError):
        SustainedDrive(agent_id="x", value=0.5, start_tick=5, end_tick=5)
    with pytest.raises(ValidationError):
        SustainedDrive(agent_id="x", value=0.5, start_tick=7, end_tick=3)


def test_scenario_config_sustained_drives_default_empty_and_validated():
    sc = ScenarioConfig(name="plain", injury_model="naive")
    assert sc.sustained_drives == []
    sc2 = ScenarioConfig(
        name="with_drives",
        injury_model="CCI",
        injury_tick=1,
        sustained_drives=[{"agent_id": "y", "value": 0.9, "start_tick": 2}],
    )
    assert sc2.sustained_drives[0].start_tick == 2
    with pytest.raises(ValidationError):
        ScenarioConfig(
            name="bad",
            horizon_days=10,
            injury_model="CCI",
            injury_tick=1,
            sustained_drives=[{"agent_id": "y", "value": 0.9, "start_tick": 99}],
        )


def test_drive_gain_is_one_module_constant():
    assert DRIVE_GAIN == 1.0


# ---------------------------------------------------------------------------
# engine behavior
# ---------------------------------------------------------------------------

def test_unknown_drive_agent_rejected_at_orchestrator_init():
    bad = scenario([SustainedDrive(agent_id="ghost", value=0.8, start_tick=0)])
    with pytest.raises(ValueError, match="ghost"):
        Orchestrator([lone_agent_card()], bad, seed=0)


def test_drive_windowing_start_and_end():
    card = lone_agent_card()
    drive = SustainedDrive(agent_id="ectopic", value=0.85, start_tick=2, end_tick=5)
    logs = Orchestrator([card], scenario([drive], horizon=8)).run()
    # tick < start: no effect (world_after ticks 1..2 equal rest state 0.5)
    assert logs[0].world_after.states["ectopic"] == pytest.approx(0.5)
    assert logs[1].world_after.states["ectopic"] == pytest.approx(0.5)
    # active updates happen at source ticks 2,3,4 -> world_after 3..5 rising
    for idx in (2, 3, 4):
        assert logs[idx].world_after.states["ectopic"] > 0.5
    # after end (source ticks >= 5): orphan node relaxes back toward baseline
    tail = [logs[i].world_after.states["ectopic"] for i in (5, 6, 7)]
    assert tail[0] <= logs[4].world_after.states["ectopic"]
    assert all(v > 0.5 for v in tail)  # decaying but still above rest initially


def test_drive_magnitude_hand_check_first_step():
    card = lone_agent_card()
    drive = SustainedDrive(agent_id="ectopic", value=0.85, start_tick=0)
    logs = Orchestrator([card], scenario([drive], horizon=2)).run()
    contribution = (0.85 - 0.5) * DRIVE_GAIN
    expected_target = 0.5 + DEVIATION_GAIN * math.tanh(contribution)
    expected_state = 0.5 + STATE_RELAX_ALPHA * (expected_target - 0.5) + BASELINE_PULL_BETA * 0.0
    assert logs[0].world_after.states["ectopic"] == pytest.approx(expected_state)


def test_naive_scenario_untouched_by_drive_machinery():
    """A system at rest with no drives stays exactly at rest."""
    cards = [lone_agent_card()]
    sc = ScenarioConfig(name="naive_plain", horizon_days=6, injury_model="naive")
    logs = Orchestrator(cards, sc).run()
    for log in logs:
        assert log.world_after.states["ectopic"] == 0.5


def test_drive_audit_entries_are_rules_and_cache_unaffected():
    card = lone_agent_card()
    card = card.model_copy(update={"tier": AgentTier.HUB, "rule_gap_reason": "n/a"})
    drive = SustainedDrive(agent_id="ectopic", value=0.85, start_tick=0)
    logs = Orchestrator([card], scenario([drive], horizon=3)).run()
    for log in logs:
        for entry in log.audit:
            assert entry.emitter == "rules"
            assert entry.cache_hit is False
            assert entry.prompt_sha256 is None


def test_determinism_with_drives(tmp_path):
    card = lone_agent_card()
    drive = SustainedDrive(agent_id="ectopic", value=0.9, start_tick=0)
    a = Orchestrator([card], scenario([drive]), seed=3).run()
    b = Orchestrator([card], scenario([drive]), seed=3).run()
    assert a == b
