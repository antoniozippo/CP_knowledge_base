import json

import pytest
from pydantic import ValidationError

from simulator.schemas import (
    AgentCard,
    AgentTier,
    DrugArm,
    DynamicsRule,
    Epoch,
    InfluenceEdge,
    InfluencePacket,
    Readout,
    RunManifest,
    ScenarioConfig,
    StateDelta,
    TickAuditEntry,
    TickLog,
    WorldState,
    epoch_for,
    validate_states,
)


def make_rule(**overrides):
    base = dict(
        rule_id="RULE-TNF_tnf-01",
        description="microglial TNF drives neuronal hyperexcitability",
        claim_refs=["EC-0001"],
        direction="up",
        magnitude_hint=0.4,
    )
    base.update(overrides)
    return DynamicsRule(**base)


def make_edge(**overrides):
    base = dict(source_id="CGRP_cgrp", relation="increases", sign=1)
    base.update(overrides)
    return InfluenceEdge(**base)


def make_card(**overrides):
    base = dict(
        id="TNF_tnf",
        label="TNF",
        entity_type="molecule",
        compartment="other",
        tier=AgentTier.MID,
        community=3,
        pathological_rules=[make_rule()],
        inbound_edges=[make_edge()],
        outbound_ids=["IL6_interleukin_6"],
    )
    base.update(overrides)
    return AgentCard(**base)


def make_delta(**overrides):
    base = dict(
        agent_id="TNF_tnf",
        tick=4,
        new_state=0.7,
        rationale="elevated by upstream glial activation",
        refs=["EC-0002"],
        emitter="llm",
    )
    base.update(overrides)
    return StateDelta(**base)


def make_arm(**overrides):
    base = dict(
        name="gabapentin",
        target_agent_ids=["CACNA_alpha2delta1"],
        start_tick=5,
        end_tick=20,
        effect_sign=-1,
        magnitude=0.6,
    )
    base.update(overrides)
    return DrugArm(**base)


def make_scenario(**overrides):
    base = dict(name="sni_cipn_cross_arm", injury_model="SNI", injury_tick=1)
    base.update(overrides)
    return ScenarioConfig(**base)


def make_world(**overrides):
    base = dict(
        tick=4,
        epoch=Epoch.SUBACUTE,
        states={"TNF_tnf": 0.7, "KCC2_kcc2": 0.2},
        readouts=Readout(pain_score=0.6, barrier_integrity=0.8, inflammation_index=0.5),
    )
    base.update(overrides)
    return WorldState(**base)


def make_ticklog(deltas=None, **overrides):
    if deltas is None:
        deltas = [make_delta(), make_delta(agent_id="KCC2_kcc2", new_state=0.3)]
    base = dict(
        tick=4,
        epoch=Epoch.SUBACUTE,
        deltas_applied=deltas,
        world_after=make_world(),
        audit=[
            TickAuditEntry(
                tick=4,
                agent_id="TNF_tnf",
                emitter="llm",
                prompt_sha256="a" * 64,
                response_sha256="b" * 64,
                cache_hit=False,
                latency_ms=123.4,
            ),
            TickAuditEntry(tick=4, agent_id="KCC2_kcc2", emitter="rules", cache_hit=True),
        ],
    )
    base.update(overrides)
    return TickLog(**base)


def assert_roundtrip(model):
    dump1 = model.model_dump()
    revived = type(model).model_validate(json.loads(json.dumps(dump1)))
    assert revived.model_dump() == dump1


class TestEpoch:
    @pytest.mark.parametrize(
        "tick,expected",
        [
            (0, Epoch.INITIATION),
            (3, Epoch.INITIATION),
            (4, Epoch.SUBACUTE),
            (14, Epoch.SUBACUTE),
            (15, Epoch.TRANSITION),
            (28, Epoch.TRANSITION),
            (29, Epoch.ESTABLISHED_CHRONIC),
            (180, Epoch.ESTABLISHED_CHRONIC),
        ],
    )
    def test_from_tick_boundaries(self, tick, expected):
        assert Epoch.from_tick(tick) is expected
        assert epoch_for(tick) is expected

    def test_negative_tick_rejected(self):
        with pytest.raises(ValueError):
            Epoch.from_tick(-1)


class TestDynamicsRule:
    @pytest.mark.parametrize(
        "rule_id",
        ["RULE-TNF_tnf-01", "RULE-agent_1-07", "RULE-KCC2_kcc2-42"],
    )
    def test_valid_rule_ids(self, rule_id):
        rule = make_rule(rule_id=rule_id)
        assert rule.magnitude_hint == 0.4

    @pytest.mark.parametrize(
        "rule_id",
        ["RULE-TNF-1", "rule-tnf-01", "RULE-TNF_tnf-001", "FOO-TNF_tnf-01", "RULE-TNF_tnf-"],
    )
    def test_invalid_rule_ids_rejected(self, rule_id):
        with pytest.raises(ValidationError):
            make_rule(rule_id=rule_id)

    def test_direction_literal_enforced(self):
        with pytest.raises(ValidationError):
            make_rule(direction="sideways")

    def test_magnitude_hint_bounds_and_default(self):
        with pytest.raises(ValidationError):
            make_rule(magnitude_hint=1.2)
        assert make_rule(magnitude_hint=None).magnitude_hint is None

    def test_empty_claim_refs_allowed(self):
        assert make_rule(claim_refs=[]).claim_refs == []


class TestInfluenceEdge:
    @pytest.mark.parametrize("sign", [-1, 0, 1])
    def test_sign_domain(self, sign):
        assert make_edge(sign=sign).sign == sign

    @pytest.mark.parametrize("sign", [-2, 2])
    def test_sign_out_of_domain_rejected(self, sign):
        with pytest.raises(ValidationError):
            make_edge(sign=sign)

    def test_weight_defaults_to_one(self):
        edge = InfluenceEdge(source_id="a", relation="increases", sign=-1)
        assert edge.weight == 1.0


class TestInfluencePacket:
    def test_valid_packet(self):
        packet = InfluencePacket(source_id="CGRP_cgrp", sign=1, weight=0.8, sender_state=0.9, tick=10)
        assert packet.sender_state == 0.9

    def test_sender_state_bounded(self):
        with pytest.raises(ValidationError):
            InfluencePacket(source_id="x", sign=1, weight=1.0, sender_state=1.5, tick=0)


class TestStateDelta:
    def test_valid_delta(self):
        delta = make_delta()
        assert delta.new_state == 0.7
        assert delta.emitter == "llm"

    @pytest.mark.parametrize("new_state", [-0.01, 1.01])
    def test_new_state_range_enforced(self, new_state):
        with pytest.raises(ValidationError):
            make_delta(new_state=new_state)

    @pytest.mark.parametrize("new_state", [0.0, 1.0])
    def test_new_state_boundaries_accepted(self, new_state):
        assert make_delta(new_state=new_state).new_state == new_state

    def test_refs_min_length(self):
        with pytest.raises(ValidationError):
            make_delta(refs=[])

    def test_emitter_literal(self):
        with pytest.raises(ValidationError):
            make_delta(emitter="oracle")

    def test_negative_tick_rejected(self):
        with pytest.raises(ValidationError):
            make_delta(tick=-1)

    def test_rationale_max_length(self):
        with pytest.raises(ValidationError):
            make_delta(rationale="x" * 501)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            make_delta(unspecified_field=1)


class TestReadout:
    def test_valid_readout(self):
        readout = Readout(pain_score=0.0, barrier_integrity=1.0, inflammation_index=0.5)
        assert readout.pain_score == 0.0

    def test_pain_score_bounded(self):
        with pytest.raises(ValidationError):
            Readout(pain_score=1.5, barrier_integrity=0.5, inflammation_index=0.5)


class TestWorldState:
    def test_valid_world(self):
        world = make_world()
        assert world.epoch is Epoch.SUBACUTE

    def test_out_of_range_state_rejected_on_construction(self):
        with pytest.raises(ValidationError):
            make_world(states={"ok": 0.5, "bad": 1.5})

    def test_validate_states_ok(self):
        assert validate_states(make_world()) is None

    def test_validate_states_lists_offending_ids(self):
        world = make_world()
        world.states["bad_agent"] = 1.5
        world.states["worse_agent"] = -0.2
        with pytest.raises(ValueError) as excinfo:
            validate_states(world)
        message = str(excinfo.value)
        assert "bad_agent" in message
        assert "worse_agent" in message


class TestAgentCard:
    def test_baseline_state_default(self):
        card = AgentCard(
            id="x",
            label="X",
            entity_type="molecule",
            compartment="other",
            tier=AgentTier.PERIPHERAL,
            community=1,
            pathological_rules=[],
            inbound_edges=[],
            outbound_ids=[],
        )
        assert card.baseline_state == 0.5

    def test_baseline_state_bounded(self):
        with pytest.raises(ValidationError):
            make_card(baseline_state=1.2)

    def test_hub_requires_rule_or_gap_reason(self):
        with pytest.raises(ValidationError):
            make_card(tier=AgentTier.HUB, pathological_rules=[], rule_gap_reason=None)

    def test_hub_with_gap_reason_accepted(self):
        card = make_card(tier=AgentTier.HUB, pathological_rules=[], rule_gap_reason="no disease rules in source corpus")
        assert card.pathological_rules == []

    def test_hub_with_rule_accepted(self):
        make_card(tier=AgentTier.HUB)

    def test_peripheral_without_rules_accepted(self):
        card = make_card(tier=AgentTier.PERIPHERAL, pathological_rules=[], rule_gap_reason=None)
        assert card.rule_gap_reason is None

    def test_neutral_inbound_edge_requires_flag(self):
        with pytest.raises(ValidationError):
            make_card(inbound_edges=[make_edge(sign=0)])

    def test_neutral_inbound_edge_with_flag_accepted(self):
        card = make_card(inbound_edges=[make_edge(sign=0, neutral_ok=True)])
        assert card.inbound_edges[0].neutral_ok is True

    def test_signed_inbound_edge_always_accepted(self):
        make_card(inbound_edges=[make_edge(sign=-1), make_edge(sign=1)])

    def test_normal_role_max_length(self):
        with pytest.raises(ValidationError):
            make_card(normal_role="x" * 2001)


class TestDrugArm:
    def test_effect_sign_domain(self):
        with pytest.raises(ValidationError):
            make_arm(effect_sign=0)
        assert make_arm(effect_sign=1).effect_sign == 1

    def test_magnitude_bounded(self):
        with pytest.raises(ValidationError):
            make_arm(magnitude=1.5)


class TestScenarioConfig:
    def test_snake_case_name_enforced(self):
        for bad_name in ["SNI Chronic", "SNI", "sni-chronic"]:
            with pytest.raises(ValidationError):
                make_scenario(name=bad_name)
        assert make_scenario(name="sni_chronic_v1").name == "sni_chronic_v1"

    def test_horizon_default_and_bounds(self):
        assert make_scenario().horizon_days == 180
        with pytest.raises(ValidationError):
            make_scenario(horizon_days=0)
        with pytest.raises(ValidationError):
            make_scenario(horizon_days=181)

    def test_naive_requires_no_injury_tick(self):
        scenario = ScenarioConfig(name="naive_baseline", injury_model="naive")
        assert scenario.injury_tick is None

    def test_naive_with_injury_tick_rejected(self):
        with pytest.raises(ValidationError):
            make_scenario(injury_model="naive", injury_tick=5)

    def test_non_naive_requires_injury_tick(self):
        with pytest.raises(ValidationError):
            make_scenario(injury_tick=None)

    def test_non_naive_with_injury_tick_accepted(self):
        assert make_scenario(injury_model="CIPN", injury_tick=0).injury_tick == 0

    def test_drug_arms_default_empty(self):
        assert make_scenario().drug_arms == []

    def test_arm_start_beyond_horizon_rejected(self):
        with pytest.raises(ValidationError):
            make_scenario(drug_arms=[make_arm(start_tick=180)])

    def test_arm_end_beyond_horizon_rejected(self):
        with pytest.raises(ValidationError):
            make_scenario(drug_arms=[make_arm(start_tick=170, end_tick=181)])

    def test_arm_within_horizon_accepted(self):
        scenario = make_scenario(drug_arms=[make_arm(start_tick=179, end_tick=None)])
        assert scenario.drug_arms[0].start_tick == 179


class TestTickLog:
    def test_duplicate_agent_deltas_rejected(self):
        duplicates = [make_delta(), make_delta(new_state=0.9)]
        with pytest.raises(ValidationError):
            make_ticklog(deltas=duplicates)

    def test_valid_ticklog(self):
        log = make_ticklog()
        assert len(log.audit) == 2
        assert log.world_after.tick == log.tick


class TestRunManifest:
    def test_engine_version_default(self):
        manifest = RunManifest(
            scenario=make_scenario(),
            started_at_utc="2026-08-25T00:00:00Z",
            seed=42,
            card_set_hash="abc123",
        )
        assert manifest.engine_version == "0.1.0"

    def test_bad_engine_version_rejected(self):
        with pytest.raises(ValidationError):
            RunManifest(
                scenario=make_scenario(),
                started_at_utc="2026-08-25T00:00:00Z",
                seed=42,
                engine_version="v1",
                card_set_hash="abc123",
            )


class TestJsonRoundTrip:
    def test_agent_card_roundtrip(self):
        assert_roundtrip(make_card())

    def test_scenario_config_roundtrip(self):
        assert_roundtrip(make_scenario(drug_arms=[make_arm()], notes="first pass"))

    def test_tick_log_roundtrip(self):
        assert_roundtrip(make_ticklog())
