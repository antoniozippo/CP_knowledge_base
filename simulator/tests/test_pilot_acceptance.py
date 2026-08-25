"""Tests for the pilot acceptance harness."""

import json
from pathlib import Path

import pytest

from simulator.engine.orchestrator import load_cards, load_scenario
from simulator.schemas import Epoch, Readout, TickLog, WorldState
from simulator.validation.pilot_acceptance import (
    DEFAULT_DELTA,
    KCC2_ID,
    SCENARIO_FILES,
    _first_crossing_series,
    first_crossing,
    run_pilot,
)

CARDS_DIR = Path(__file__).resolve().parents[1] / "agent_cards"
SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def make_log(tick: int, states: dict[str, float], pain: float = 0.05) -> TickLog:
    return TickLog(
        tick=tick,
        epoch=Epoch.from_tick(tick),
        deltas_applied=[],
        world_after=WorldState(
            tick=tick + 1,
            epoch=Epoch.from_tick(tick + 1),
            states=states,
            readouts=Readout(
                pain_score=pain, barrier_integrity=1.0, inflammation_index=0.5
            ),
        ),
    )


def series_logs(values: list[float], agent: str = "a", baseline: float = 0.5) -> list[TickLog]:
    return [
        make_log(tick, {agent: v, "other": baseline})
        for tick, v in enumerate(values)
    ]


class TestFirstCrossingSynthetic:
    def test_never_cross_returns_none(self):
        logs = series_logs([0.5, 0.52, 0.55, 0.5])
        assert first_crossing(logs, "a", baseline=0.5) is None

    def test_immediate_cross(self):
        logs = series_logs([0.7, 0.7, 0.7])
        assert first_crossing(logs, "a", baseline=0.5) == 1

    def test_sustain_requirement_rejects_single_spike(self):
        logs = series_logs([0.7, 0.5, 0.5])
        assert first_crossing(logs, "a", baseline=0.5) is None

    def test_sustain_requirement_two_tick_streak(self):
        logs = series_logs([0.5, 0.7, 0.7, 0.5])
        assert first_crossing(logs, "a", baseline=0.5) == 2

    def test_streak_resets_after_interruption(self):
        logs = series_logs([0.7, 0.5, 0.7, 0.7])
        assert first_crossing(logs, "a", baseline=0.5) == 3

    def test_direction_down_uses_lower_threshold(self):
        logs = series_logs([0.5, 0.3, 0.3])
        assert first_crossing(logs, "a", direction="down", baseline=0.5) == 2

    def test_direction_down_never_on_rise(self):
        logs = series_logs([0.5, 0.7, 0.7])
        assert first_crossing(logs, "a", direction="down", baseline=0.5) is None

    def test_baseline_falls_back_to_first_logged_state(self):
        logs = series_logs([0.6, 0.6, 0.6])
        assert first_crossing(logs, "a") is None
        rising = series_logs([0.6, 0.7, 0.7])
        assert first_crossing(rising, "a", delta=0.05) == 2

    def test_empty_logs_return_none(self):
        assert first_crossing([], "a", baseline=0.5) is None

    def test_default_delta_value(self):
        assert DEFAULT_DELTA == 0.15

    def test_series_helper_matches_public_wrapper(self):
        values = [0.5, 0.66, 0.66, 0.66]
        logs = series_logs(values)
        assert (
            _first_crossing_series(values, 0.5, 0.15, 2, "up")
            == first_crossing(logs, "a", baseline=0.5) - 1
        )


@pytest.fixture(scope="module")
def pilot_run(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("pilot")
    report = run_pilot(CARDS_DIR, out_dir, SCENARIOS_DIR)
    return report, out_dir


class TestRunPilotIntegration:
    def test_three_valid_ticklogs(self, pilot_run):
        report, out_dir = pilot_run
        for scenario_name in ("sni_28d", "sni_28d_clp257", "naive_28d"):
            log_file = out_dir / scenario_name / "tick_log.jsonl"
            assert log_file.exists()
            logs = [TickLog(**json.loads(line)) for line in log_file.read_text().splitlines()]
            assert len(logs) == 28
            assert [log.world_after.tick for log in logs] == list(range(1, 29))
            assert all(log.world_after.readouts is not None for log in logs)
            assert all(len(log.deltas_applied) > 0 for log in logs)

    def test_event_table_covers_key_entities(self, pilot_run):
        report, _ = pilot_run
        names = {row.name for row in report.events}
        assert {
            "microglia",
            "tnf_alpha",
            "bdnf",
            "mmp9",
            "kcc2_drop",
            "pnn_loss",
            "pv_dysfunction",
            "pain_readout",
        } <= names

    def test_ordering_booleans_computed(self, pilot_run):
        report, _ = pilot_run
        assert len(report.ordering) == 5
        assert all(step.ok in (True, False) for step in report.ordering)
        assert all(step.step for step in report.ordering)

    def test_drug_comparison_reported_not_assumed(self, pilot_run):
        report, _ = pilot_run
        assert isinstance(report.pain_mean_sni, float)
        assert isinstance(report.pain_mean_clp257, float)
        criteria = {c.name: c.passed for c in report.criteria}
        assert set(criteria) == {
            "drug_effect_pain_lower",
            "drug_effect_kcc2_higher",
            "naive_separation",
            "event_ordering",
        }

    def test_clp257_arm_differs_from_sni_in_kcc2_state(self, pilot_run):
        report, out_dir = pilot_run

        def kcc2_series(scenario_name):
            logs = [
                TickLog(**json.loads(line))
                for line in (out_dir / scenario_name / "tick_log.jsonl").read_text().splitlines()
            ]
            return [log.world_after.states[KCC2_ID] for log in logs]

        sni = kcc2_series("sni_28d")
        clp = kcc2_series("sni_28d_clp257")
        assert sni[:3] == clp[:3]
        assert clp[3:] != sni[3:]
        assert sum(clp[3:]) > sum(sni[3:])

    def test_all_means_within_unit_interval(self, pilot_run):
        report, _ = pilot_run
        for value in (
            report.pain_mean_sni,
            report.pain_mean_clp257,
            report.pain_mean_naive,
            report.kcc2_mean_sni_post3,
            report.kcc2_mean_clp257_post3,
        ):
            assert 0.0 <= value <= 1.0


class TestScenarioYamlsParse:
    @pytest.mark.parametrize("filename", sorted(SCENARIO_FILES.values()))
    def test_parses_into_scenario_config(self, filename):
        scenario = load_scenario(SCENARIOS_DIR / filename)
        assert scenario.horizon_days == 28

    def test_perturbation_ids_exist_in_card_set(self):
        cards = {c.id for c in load_cards(CARDS_DIR)}
        for arm, filename in SCENARIO_FILES.items():
            scenario = load_scenario(SCENARIOS_DIR / filename)
            for pert in scenario.initial_perturbations:
                assert pert.agent_id in cards, f"{arm}: unknown agent {pert.agent_id}"
            for drug_arm in scenario.drug_arms:
                for target in drug_arm.target_agent_ids:
                    assert target in cards, f"{arm}: unknown drug target {target}"

    def test_naive_has_no_perturbations_or_arms(self):
        scenario = load_scenario(SCENARIOS_DIR / SCENARIO_FILES["naive"])
        assert scenario.injury_model == "naive"
        assert scenario.injury_tick is None
        assert not scenario.initial_perturbations
        assert not scenario.drug_arms

    def test_clp257_arm_targets_canonical_kcc2(self):
        scenario = load_scenario(SCENARIOS_DIR / SCENARIO_FILES["clp257"])
        assert scenario.name == "sni_28d_clp257"
        assert len(scenario.drug_arms) == 1
        arm = scenario.drug_arms[0]
        assert arm.name == "clp257"
        assert arm.start_tick == 3
        assert arm.effect_sign == 1
        assert arm.magnitude == pytest.approx(0.6)
        assert arm.end_tick is None or arm.end_tick < scenario.horizon_days
