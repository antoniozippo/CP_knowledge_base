import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from simulator.engine.llm_agent import DeltaCache
from simulator.engine.orchestrator import Orchestrator, load_cards, load_scenario, resolve_label
from simulator.schemas import (
    AgentCard,
    AgentTier,
    DrugArm,
    Epoch,
    InfluenceEdge,
    DynamicsRule,
    Perturbation,
    RunManifest,
    ScenarioConfig,
)

CARDS_DIR = Path(__file__).resolve().parents[1] / "agent_cards"


def fixture_cards():
    tnf = AgentCard(
        id="tnf_hub",
        label="Tumor Necrosis Factor Alpha (TNF)",
        entity_type="molecule",
        compartment="systemic",
        tier=AgentTier.HUB,
        community=0,
        baseline_state=0.15,
        pathological_rules=[
            DynamicsRule(
                rule_id="RULE-tnf_hub-01",
                description="TNF drives microglial activation",
                claim_refs=["EC-0001"],
                direction="up",
            )
        ],
        outbound_ids=["microglia"],
    )
    microglia = AgentCard(
        id="microglia",
        label="Microglial Activation State",
        entity_type="process",
        compartment="cns",
        tier=AgentTier.MID,
        community=0,
        baseline_state=0.1,
        inbound_edges=[InfluenceEdge(source_id="tnf_hub", relation="drives", sign=1, weight=0.9)],
        outbound_ids=["hyperalgesia", "bscb"],
    )
    hyperalgesia = AgentCard(
        id="hyperalgesia",
        label="Mechanical Hyperalgesia",
        entity_type="symptom",
        compartment="periphery",
        tier=AgentTier.PERIPHERAL,
        community=0,
        baseline_state=0.05,
        inbound_edges=[
            InfluenceEdge(source_id="microglia", relation="drives", sign=1, weight=0.3),
            InfluenceEdge(source_id="inh_a", relation="gates", sign=-1, weight=1.0),
            InfluenceEdge(source_id="inh_b", relation="gates", sign=-1, weight=1.0),
        ],
        outbound_ids=[],
    )
    bscb = AgentCard(
        id="bscb",
        label="Blood-Spinal Cord Barrier",
        entity_type="structure",
        compartment="cns",
        tier=AgentTier.MID,
        community=0,
        baseline_state=0.1,
        inbound_edges=[InfluenceEdge(source_id="microglia", relation="disrupts", sign=1, weight=0.6)],
        outbound_ids=[],
    )
    inh_a = AgentCard(
        id="inh_a",
        label="Inhibitory Interneuron Gate A",
        entity_type="cell_type",
        compartment="cns",
        tier=AgentTier.MID,
        community=1,
        baseline_state=0.8,
        inbound_edges=[InfluenceEdge(source_id="inh_b", relation="recruits", sign=1, weight=0.9)],
        outbound_ids=["inh_b", "hyperalgesia"],
    )
    inh_b = AgentCard(
        id="inh_b",
        label="Inhibitory Interneuron Gate B",
        entity_type="cell_type",
        compartment="cns",
        tier=AgentTier.MID,
        community=1,
        baseline_state=0.8,
        inbound_edges=[InfluenceEdge(source_id="inh_a", relation="recruits", sign=1, weight=0.9)],
        outbound_ids=["inh_a", "hyperalgesia"],
    )
    return [tnf, microglia, hyperalgesia, bscb, inh_a, inh_b]


def naive_scenario(horizon=40):
    return ScenarioConfig(name="fixture_naive", horizon_days=horizon, injury_model="naive")


def sni_scenario(horizon=40, drug_arms=None):
    return ScenarioConfig(
        name="sni_like",
        horizon_days=horizon,
        injury_model="SNI",
        injury_tick=0,
        drug_arms=drug_arms or [],
        initial_perturbations=[Perturbation(agent_id="tnf_hub", value=0.9)],
        notes="fixture SNI proxy: boost TNF hub at t0",
    )


class ScriptedLLM:
    def __init__(self):
        self.prompts = []
        self.calls_by_tick = {}

    def complete(self, prompt):
        self.prompts.append(prompt)
        tick_line = [ln for ln in prompt.splitlines() if ln.startswith("tick:")]
        tick = int(tick_line[0].split(":", 1)[1].strip())
        self.calls_by_tick.setdefault(tick, []).append(prompt)
        return '{"new_state": 0.85, "rationale": "hub reasoning", "refs": ["RULE-tnf_hub-01"]}'


def states_at(logs, tick, agent_id):
    return logs[tick].world_after.states[agent_id]


def test_perturbation_model_and_scenario_extension():
    p = Perturbation(agent_id="x", value=0.9)
    assert p.value == 0.9
    with pytest.raises(ValidationError):
        Perturbation(agent_id="x", value=1.5)
    sc = ScenarioConfig(
        name="sni2",
        injury_model="SNI",
        injury_tick=1,
        initial_perturbations=[{"agent_id": "y", "value": 0.3}],
    )
    assert sc.initial_perturbations[0].value == 0.3


def test_resolve_label_deterministic_lowest_sorted_id():
    cards = fixture_cards()
    assert resolve_label(cards, "necrosis").id == "tnf_hub"
    assert resolve_label(cards, "barrier").id == "bscb"
    both = [
        AgentCard(
            id="b_second",
            label="Something TNF related",
            entity_type="molecule",
            compartment="other",
            tier=AgentTier.MID,
            community=0,
        ),
        AgentCard(
            id="a_first",
            label="Another TNF thing",
            entity_type="molecule",
            compartment="other",
            tier=AgentTier.MID,
            community=0,
        ),
    ]
    assert resolve_label(both, "tnf").id == "a_first"
    with pytest.raises(LookupError):
        resolve_label(cards, "nonexistent-xyz")


def test_non_naive_without_seeds_raises_not_implemented():
    scenario = ScenarioConfig(name="sni3", injury_model="SNI", injury_tick=0)
    with pytest.raises(NotImplementedError):
        Orchestrator(fixture_cards(), scenario)


def test_naive_with_seeds_rejected():
    scenario = ScenarioConfig(
        name="naive_bad",
        injury_model="naive",
        initial_perturbations=[Perturbation(agent_id="tnf_hub", value=0.9)],
    )
    with pytest.raises(ValueError):
        Orchestrator(fixture_cards(), scenario)


def test_a_naive_guardrail_states_bounded_and_pain_below_threshold():
    cards = fixture_cards()
    orch = Orchestrator(cards, naive_scenario(40))
    logs = orch.run()
    assert len(logs) == 40
    baselines = {c.id: c.baseline_state for c in cards}
    for log in logs:
        assert log.world_after.states == baselines
        for state in log.world_after.states.values():
            assert 0.0 <= state <= 1.0
        assert log.world_after.readouts.pain_score < 0.2


def test_b_sni_boost_moves_downstream_neighbors_sign_correctly():
    naive_logs = Orchestrator(fixture_cards(), naive_scenario(40)).run()
    sni_logs = Orchestrator(fixture_cards(), sni_scenario(40)).run()
    for t in range(1, 6):
        assert states_at(sni_logs, t, "microglia") > states_at(naive_logs, t, "microglia")
    assert states_at(sni_logs, 5, "microglia") > states_at(naive_logs, 5, "microglia")
    pain_sni = sni_logs[4].world_after.readouts.pain_score
    pain_naive = naive_logs[4].world_after.readouts.pain_score
    assert pain_sni > pain_naive
    barrier_sni = sni_logs[4].world_after.readouts.barrier_integrity
    barrier_naive = naive_logs[4].world_after.readouts.barrier_integrity
    assert barrier_sni < barrier_naive


def test_c_drug_arm_partially_reverses_sni_effect():
    drug = DrugArm(
        name="anti_tnf_proxy",
        target_agent_ids=["microglia"],
        start_tick=0,
        end_tick=None,
        effect_sign=-1,
        magnitude=0.5,
    )
    drugged = Orchestrator(fixture_cards(), sni_scenario(40, [drug])).run()
    undrugged = Orchestrator(fixture_cards(), sni_scenario(40)).run()
    assert states_at(drugged, 5, "microglia") < states_at(undrugged, 5, "microglia")
    assert drugged[4].world_after.readouts.pain_score < undrugged[4].world_after.readouts.pain_score


def test_d_llm_called_only_on_hub_boundary_and_injury_ticks_then_cached():
    cache = DeltaCache()
    llm = ScriptedLLM()
    logs = Orchestrator(fixture_cards(), sni_scenario(32), llm_client=llm, cache=cache).run()
    assert set(llm.calls_by_tick) == {0, 4, 15, 29}
    assert all(len(v) == 1 for v in llm.calls_by_tick.values())
    audit_by_tick = {}
    for log in logs:
        for entry in log.audit:
            audit_by_tick.setdefault(entry.tick, []).append(entry)
    for boundary in (0, 4, 15, 29):
        entries = audit_by_tick[boundary]
        llm_entries = [e for e in entries if e.emitter == "llm"]
        rule_entries = [e for e in entries if e.emitter == "rules"]
        assert len(llm_entries) == 1 and len(rule_entries) == 5
        assert all(e.prompt_sha256 and e.response_sha256 for e in llm_entries)
        assert all(e.latency_ms is not None for e in llm_entries)
    for other in (1, 2, 16, 30):
        assert all(e.emitter == "rules" for e in audit_by_tick[other])
        assert all(e.prompt_sha256 is None and e.latency_ms is None for e in audit_by_tick[other])
    second_client = ScriptedLLM()
    Orchestrator(fixture_cards(), sni_scenario(32), llm_client=second_client, cache=cache).run()
    assert second_client.prompts == []


def test_e_save_run_round_trip(tmp_path):
    orch = Orchestrator(fixture_cards(), naive_scenario(3))
    logs = orch.run()
    out_dir = tmp_path / "run1"
    orch.save_run(logs, out_dir)
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "tick_log.jsonl").exists()
    assert (out_dir / "states.csv").exists()
    manifest_data = json.loads((out_dir / "manifest.json").read_text())
    manifest = RunManifest.model_validate(manifest_data["manifest"])
    assert manifest.scenario.name == "fixture_naive"
    lines = (out_dir / "tick_log.jsonl").read_text().splitlines()
    assert len(lines) == 3
    parsed = json.loads(lines[0])
    assert parsed["tick"] == 0
    csv_lines = (out_dir / "states.csv").read_text().splitlines()
    assert csv_lines[0] == "tick,agent_id,state"
    assert len(csv_lines) == 1 + 3 * len(fixture_cards())


def test_f_determinism_byte_identical_tick_logs(tmp_path):
    orch_a = Orchestrator(fixture_cards(), naive_scenario(12), seed=7)
    logs_a = orch_a.run()
    orch_b = Orchestrator(fixture_cards(), naive_scenario(12), seed=7)
    logs_b = orch_b.run()
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    orch_a.save_run(logs_a, dir_a)
    orch_b.save_run(logs_b, dir_b)
    assert (dir_a / "tick_log.jsonl").read_bytes() == (dir_b / "tick_log.jsonl").read_bytes()


def test_yaml_loaders_round_trip(tmp_path):
    scenario_yaml = tmp_path / "sc.yaml"
    scenario_yaml.write_text(
        yaml.safe_dump(
            {
                "name": "loader_check",
                "horizon_days": 10,
                "injury_model": "CCI",
                "injury_tick": 2,
                "initial_perturbations": [{"agent_id": "tnf_hub", "value": 0.9}],
            }
        )
    )
    scenario = load_scenario(scenario_yaml)
    assert scenario.injury_model == "CCI"
    assert scenario.initial_perturbations[0].agent_id == "tnf_hub"
    cards = load_cards(CARDS_DIR)
    assert len(cards) == 254
    by_id = {c.id: c for c in cards}
    assert by_id["TNF_TNF_alpha"].tier == AgentTier.MID


def test_g_real_card_set_smoke_run_bounds():
    cards = load_cards(CARDS_DIR)
    scenario = ScenarioConfig(name="real_smoke", horizon_days=3, injury_model="naive")
    logs = Orchestrator(cards, scenario).run()
    assert len(logs) == 3
    final = logs[-1]
    assert final.tick == 2
    assert final.world_after.tick == 3
    assert len(final.deltas_applied) == 254
    assert len(final.audit) == 254
    for state in final.world_after.states.values():
        assert 0.0 <= state <= 1.0
    readout = final.world_after.readouts
    assert 0.0 <= readout.pain_score <= 1.0
    assert 0.0 <= readout.barrier_integrity <= 1.0
