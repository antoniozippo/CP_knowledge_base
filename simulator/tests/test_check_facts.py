"""Tests for the literature-grounded facts harness (Task 2.6)."""

import json
from pathlib import Path

import pytest
import yaml

from simulator.schemas import Epoch, Readout, TickLog, WorldState
from simulator.validation.check_facts import (
    KINDS,
    evaluate_fact,
    load_facts,
    render_markdown,
    resolve_source_ref,
    run_checks,
)

CARDS_DIR = Path(__file__).resolve().parents[1] / "agent_cards"
SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"
FACTS_YAML = Path(__file__).resolve().parents[1] / "validation" / "facts.yaml"
REPO_ROOT = Path(__file__).resolve().parents[2]


def make_log(
    tick: int,
    states: dict[str, float],
    pain: float = 0.05,
    barrier: float = 1.0,
    inflammation: float = 0.5,
) -> TickLog:
    return TickLog(
        tick=tick,
        epoch=Epoch.from_tick(tick),
        deltas_applied=[],
        world_after=WorldState(
            tick=tick + 1,
            epoch=Epoch.from_tick(tick + 1),
            states=states,
            readouts=Readout(
                pain_score=pain,
                barrier_integrity=barrier,
                inflammation_index=inflammation,
            ),
        ),
    )


def series_logs(values, agent="a", **readout_kwargs) -> list[TickLog]:
    if isinstance(values, dict):
        ticks_states = [(tick, states) for tick, states in values.items()]
    else:
        ticks_states = [(tick, {agent: v}) for tick, v in enumerate(values)]
    return [make_log(tick, states, **readout_kwargs) for tick, states in ticks_states]


# ---------------------------------------------------------------------------
# source_ref resolver
# ---------------------------------------------------------------------------


class TestResolveSourceRef:
    @pytest.fixture()
    def fake_repo(self, tmp_path):
        lit = tmp_path / "analysis" / "literature"
        claims = tmp_path / "analysis" / "claims"
        lit.mkdir(parents=True)
        claims.mkdir(parents=True)
        (lit / "theme_01_spinal_disinhibition.md").write_text(
            "# Theme 1\n\n### F1.1: Some finding\n\ntext\n"
        )
        (claims / "claims.json").write_text(
            json.dumps([{"id": "EC-0001"}, {"id": "EC-0042"}])
        )
        (tmp_path / "RhoA-ROCK.md").write_text("# dossier\n")
        return tmp_path

    def test_theme_without_fragment(self, fake_repo):
        assert resolve_source_ref(fake_repo, "theme_01")

    def test_theme_with_existing_fragment(self, fake_repo):
        assert resolve_source_ref(fake_repo, "theme_01#F1.1")

    def test_theme_with_missing_fragment(self, fake_repo):
        assert not resolve_source_ref(fake_repo, "theme_01#F9.9")

    def test_unknown_theme(self, fake_repo):
        assert not resolve_source_ref(fake_repo, "theme_99")

    def test_ec_claim_present(self, fake_repo):
        assert resolve_source_ref(fake_repo, "EC-0042")

    def test_ec_claim_absent(self, fake_repo):
        assert not resolve_source_ref(fake_repo, "EC-9999")

    def test_dossier_path(self, fake_repo):
        assert resolve_source_ref(fake_repo, "RhoA-ROCK.md")

    def test_missing_dossier_path(self, fake_repo):
        assert not resolve_source_ref(fake_repo, "Nope.md")


# ---------------------------------------------------------------------------
# facts.yaml schema
# ---------------------------------------------------------------------------


class TestFactsYamlSchema:
    @pytest.fixture(scope="class")
    def facts(self):
        return load_facts(FACTS_YAML)

    def test_loads_nonempty(self, facts):
        assert len(facts) >= 16

    def test_ids_unique(self, facts):
        ids = [f["id"] for f in facts]
        assert len(ids) == len(set(ids))

    def test_kinds_valid_and_all_covered(self, facts):
        kinds = {f["kind"] for f in facts}
        assert kinds <= set(KINDS)
        assert kinds == set(KINDS)

    def test_required_fields(self, facts):
        for fact in facts:
            assert fact["id"]
            assert fact["claim"].strip()
            assert fact["source_ref"].strip()
            assert isinstance(fact["params"], dict) and fact["params"]

    def test_source_refs_resolve_against_real_repo(self, facts):
        bad = [
            f["source_ref"] for f in facts if not resolve_source_ref(REPO_ROOT, f["source_ref"])
        ]
        assert not bad, f"unresolved source_refs: {bad}"

    def test_raw_yaml_has_facts_key(self):
        data = yaml.safe_load(FACTS_YAML.read_text())
        assert isinstance(data.get("facts"), list)


# ---------------------------------------------------------------------------
# evaluators on synthetic logs
# ---------------------------------------------------------------------------


class TestStabilityBound:
    def _fact(self, params):
        return {
            "id": "T-1",
            "claim": "test",
            "source_ref": "x",
            "kind": "stability_bound",
            "params": params,
        }

    def test_readout_max_below_threshold_passes(self):
        runs = {"s": series_logs([0.05, 0.08, 0.12], pain=0.0)}
        ctx = {"runs": runs, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact({"scenario": "s", "readout": "pain_score", "comparator": "<", "value": 0.15}),
            ctx,
        )
        assert result.passed

    def test_readout_max_above_threshold_fails(self):
        runs = {"s": series_logs([0.2], pain=0.0)}
        ctx = {"runs": runs, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact({"scenario": "s", "readout": "inflammation_index", "comparator": "<", "value": 0.15}),
            ctx,
        )
        assert not result.passed

    def test_window_restricts_aggregation(self):
        logs = series_logs({t: {"a": 0.9} for t in range(1, 11)})
        ctx = {"runs": {"s": logs}, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact(
                {"scenario": "s", "agent_id": "a", "window": [8, 10], "agg": "max",
                 "comparator": "<", "value": 0.5}
            ),
            ctx,
        )
        assert not result.passed

    def test_agent_mean_over_window(self):
        logs = series_logs({t: {"a": 0.4} for t in range(20, 28)})
        ctx = {"runs": {"s": logs}, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact(
                {"scenario": "s", "agent_id": "a", "window": [20, 27], "agg": "mean",
                 "comparator": "<", "value": 0.5}
            ),
            ctx,
        )
        assert result.passed

    def test_states_bounded(self):
        logs = [make_log(t, {"a": 0.7}) for t in range(3)]
        ctx = {"runs": {"s": logs}, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact({"scenario": "s", "states_bounded": True}), ctx
        )
        assert result.passed

    def test_states_bounded_detects_violation(self):
        logs = [make_log(0, {"a": 0.5}), make_log(1, {"a": 0.5})]
        logs[1].world_after.states["a"] = 1.5
        ctx = {"runs": {"s": logs}, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact({"scenario": "s", "states_bounded": True}), ctx
        )
        assert not result.passed

    def test_relative_gap_against_other_scenario_passes(self):
        decayed = series_logs({t: {"tnf": 0.8} for t in range(21, 29)})
        sustained = series_logs({t: {"tnf": 0.97} for t in range(21, 29)})
        ctx = {"runs": {"dec": decayed, "sus": sustained}, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact(
                {"scenario": "dec", "vs_scenario": "sus", "agent_id": "tnf",
                 "window": [21, 28], "agg": "mean", "min_gap": 0.1}
            ),
            ctx,
        )
        assert result.passed

    def test_relative_gap_readout_insufficient_fails(self):
        decayed = series_logs({t: {"x": 0.5} for t in range(21, 29)}, pain=0.26)
        sustained = series_logs({t: {"x": 0.5} for t in range(21, 29)}, pain=0.29)
        ctx = {"runs": {"dec": decayed, "sus": sustained}, "cards_by_id": {}, "meta": {}}
        result = evaluate_fact(
            self._fact(
                {"scenario": "dec", "vs_scenario": "sus", "readout": "pain_score",
                 "window": [21, 28], "agg": "mean", "min_gap": 0.1}
            ),
            ctx,
        )
        assert not result.passed


class TestOrderingPair:
    def _fact(self, earlier, later, tolerance=1):
        return {
            "id": "T-2",
            "claim": "test",
            "source_ref": "x",
            "kind": "ordering_pair",
            "params": {
                "scenario": "s",
                "earlier": earlier,
                "later": later,
                "tolerance": tolerance,
                "delta": 0.15,
                "sustain": 2,
            },
        }

    def _ctx(self, values_a, values_b, baseline_a=0.5, baseline_b=0.5):
        cards = {
            "a": type("C", (), {"id": "a", "baseline_state": baseline_a}),
            "b": type("C", (), {"id": "b", "baseline_state": baseline_b}),
        }
        logs = []
        for t in range(len(values_a)):
            logs.append(make_log(t, {"a": values_a[t], "b": values_b[t]}))
        return {"runs": {"s": logs}, "cards_by_id": cards, "meta": {}}

    def test_earlier_before_later_passes(self):
        ctx = self._ctx([0.7] * 5, [0.5, 0.5, 0.7, 0.7, 0.7])
        result = evaluate_fact(
            self._fact({"agent": "a", "direction": "up"}, {"agent": "b", "direction": "up"}), ctx
        )
        assert result.passed

    def test_later_before_earlier_fails(self):
        ctx = self._ctx([0.5, 0.5, 0.7, 0.7, 0.7], [0.7] * 5)
        result = evaluate_fact(
            self._fact({"agent": "a", "direction": "up"}, {"agent": "b", "direction": "up"}), ctx
        )
        assert not result.passed

    def test_tie_within_tolerance_passes(self):
        ctx = self._ctx([0.7] * 5, [0.7] * 5)
        result = evaluate_fact(
            self._fact({"agent": "a", "direction": "up"}, {"agent": "b", "direction": "up"}), ctx
        )
        assert result.passed

    def test_down_crossing_uses_lower_threshold(self):
        ctx = self._ctx([0.5, 0.3, 0.3, 0.3, 0.3], [0.5, 0.5, 0.5, 0.3, 0.3])
        result = evaluate_fact(
            self._fact({"agent": "a", "direction": "down"}, {"agent": "b", "direction": "down"}),
            ctx,
        )
        assert result.passed

    def test_never_crossing_fails(self):
        ctx = self._ctx([0.5] * 5, [0.7] * 5)
        result = evaluate_fact(
            self._fact({"agent": "a", "direction": "up"}, {"agent": "b", "direction": "up"}), ctx
        )
        assert not result.passed

    def test_readout_event_with_baseline_from_scenario(self):
        ref_logs = [make_log(t, {"x": 0.5}, pain=0.05 + t * 0.001) for t in range(28)]
        target_logs = [
            make_log(
                t,
                {"a": 0.5 if t < 2 else 0.7, "b": 0.5},
                pain=0.05 if t < 3 else 0.25,
            )
            for t in range(28)
        ]
        ctx = {
            "runs": {"s": target_logs, "ref": ref_logs},
            "cards_by_id": {},
            "meta": {},
        }
        fact = self._fact(
            {"agent": "a", "direction": "up"},
            {"readout": "pain_score", "direction": "up", "baseline_from": {"scenario": "ref"}},
        )
        result = evaluate_fact(fact, ctx)
        assert result.passed


class TestReadoutThreshold:
    def _logs(self, pain=0.05, barrier=1.0, inflammation=0.5):
        return [make_log(t, {"x": 0.5}, pain=pain, barrier=barrier, inflammation=inflammation)
                for t in range(28)]

    def _eval(self, params, runs):
        fact = {
            "id": "T-3",
            "claim": "test",
            "source_ref": "x",
            "kind": "readout_threshold",
            "params": params,
        }
        return evaluate_fact(fact, {"runs": runs, "cards_by_id": {}, "meta": {}})

    def test_absolute_threshold_pass(self):
        runs = {"sni": self._logs(pain=0.3)}
        result = self._eval(
            {"scenario": "sni", "readout": "pain_score", "window": [14, 28],
             "comparator": ">", "value": 0.1},
            runs,
        )
        assert result.passed

    def test_relative_gap_higher_pass(self):
        runs = {"sni": self._logs(inflammation=0.6), "naive": self._logs(inflammation=0.5)}
        result = self._eval(
            {"scenario": "sni", "vs_scenario": "naive", "readout": "inflammation_index",
             "window": [7, 21], "min_gap": 0.05},
            runs,
        )
        assert result.passed

    def test_relative_gap_wrong_direction_fail(self):
        runs = {"naive": self._logs(barrier=0.44), "sni": self._logs(barrier=1.0)}
        result = self._eval(
            {"scenario": "naive", "vs_scenario": "sni", "readout": "barrier_integrity",
             "window": [10, 28], "min_gap": 0.03},
            runs,
        )
        assert not result.passed

    def test_relative_gap_lower_in_treatment_pass(self):
        runs = {"naive": self._logs(barrier=1.0), "sni": self._logs(barrier=0.44)}
        result = self._eval(
            {"scenario": "naive", "vs_scenario": "sni", "readout": "barrier_integrity",
             "window": [10, 28], "min_gap": 0.03},
            runs,
        )
        assert result.passed


class TestDrugEffect:
    def _logs(self, value):
        return [make_log(t, {"rock": value, "mg": value}) for t in range(28)]

    def _eval(self, params, runs):
        fact = {
            "id": "T-4",
            "claim": "test",
            "source_ref": "x",
            "kind": "drug_effect",
            "params": params,
        }
        return evaluate_fact(fact, {"runs": runs, "cards_by_id": {}, "meta": {}})

    def test_readout_reduction_pass(self):
        runs = {"ctrl": self._logs(0.0), "trt": self._logs(0.0)}
        for i, log in enumerate(runs["ctrl"]):
            log.world_after.readouts.pain_score = 0.3
        for i, log in enumerate(runs["trt"]):
            log.world_after.readouts.pain_score = 0.2
        result = self._eval(
            {"treatment": "trt", "control": "ctrl", "readout": "pain_score",
             "window": [14, 28], "min_reduction": 0.03},
            runs,
        )
        assert result.passed

    def test_agent_state_reduction_pass(self):
        runs = {"ctrl": self._logs(0.8), "trt": self._logs(0.4)}
        result = self._eval(
            {"treatment": "trt", "control": "ctrl", "agent_id": "rock",
             "window": [14, 28], "min_reduction": 0.2},
            runs,
        )
        assert result.passed

    def test_insufficient_reduction_fails(self):
        runs = {"ctrl": self._logs(0.45), "trt": self._logs(0.42)}
        result = self._eval(
            {"treatment": "trt", "control": "ctrl", "agent_id": "rock",
             "window": [14, 28], "min_reduction": 0.2},
            runs,
        )
        assert not result.passed


class TestDeterminism:
    def _fact(self, check, scenario="sni"):
        return {
            "id": "T-5",
            "claim": "test",
            "source_ref": "x",
            "kind": "determinism",
            "params": {"check": check, "scenario": scenario},
        }

    def _logs(self, jitter=None):
        logs = [make_log(t, {"h": 0.5}) for t in range(28)]
        return logs

    def test_byte_identical_rerun_passes(self):
        a, b = self._logs(), self._logs()
        ctx = {"runs": {"sni": a, "sni__rerun": b}, "cards_by_id": {}, "meta": {}}
        assert evaluate_fact(self._fact("byte_identical_rerun"), ctx).passed

    def test_byte_identical_rerun_detects_divergence(self):
        a = self._logs()
        b = self._logs()
        b[5].world_after.states["h"] = 0.9
        ctx = {"runs": {"sni": a, "sni__rerun": b}, "cards_by_id": {}, "meta": {}}
        assert not evaluate_fact(self._fact("byte_identical_rerun"), ctx).passed

    def test_cached_second_run_zero_llm_calls(self):
        ctx = {
            "runs": {},
            "cards_by_id": {},
            "meta": {"cache_warm_calls": 5, "cache_second_run_calls": 0},
        }
        assert evaluate_fact(self._fact("cached_second_run_zero_llm"), ctx).passed

    def test_cached_second_run_with_llm_calls_fails(self):
        ctx = {
            "runs": {},
            "cards_by_id": {},
            "meta": {"cache_warm_calls": 5, "cache_second_run_calls": 3},
        }
        assert not evaluate_fact(self._fact("cached_second_run_zero_llm"), ctx).passed

    def test_cached_check_vacuous_without_warm_run_fails(self):
        ctx = {
            "runs": {},
            "cards_by_id": {},
            "meta": {"cache_warm_calls": 0, "cache_second_run_calls": 0},
        }
        assert not evaluate_fact(self._fact("cached_second_run_zero_llm"), ctx).passed


class TestEvaluateFactValidation:
    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError):
            evaluate_fact(
                {"id": "X", "claim": "c", "source_ref": "s", "kind": "bogus", "params": {}},
                {"runs": {}, "cards_by_id": {}, "meta": {}},
            )

    def test_stability_bound_requires_target(self):
        with pytest.raises(ValueError):
            evaluate_fact(
                {"id": "X", "claim": "c", "source_ref": "s",
                 "kind": "stability_bound", "params": {"scenario": "s"}},
                {"runs": {}, "cards_by_id": {}, "meta": {}},
            )


# ---------------------------------------------------------------------------
# integration on the real card set
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def checked(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("facts")
    results = run_checks(CARDS_DIR, out_dir=out_dir, scenarios_dir=SCENARIOS_DIR)
    return results, out_dir


class TestRunChecksIntegration:
    def test_all_facts_pass(self, checked):
        results, _ = checked
        failures = [r for r in results if not r.passed]
        assert not failures, "\n".join(
            f"{r.id}: expected {r.expected}, observed {r.observed}" for r in failures
        )

    def test_report_written_and_deterministic(self, checked):
        results, out_dir = checked
        report = render_markdown(results)
        path = out_dir / "facts_report.md"
        assert path.exists()
        assert path.read_text() == report
        assert report.count("| PASS |") == len(results)
        assert "| FAIL |" not in report

    def test_covers_all_kinds(self, checked):
        results, _ = checked
        kinds = {r.kind for r in results}
        assert kinds == set(KINDS)
