import re
from collections import Counter
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RULE_ID_PATTERN = r"^RULE-[A-Za-z0-9_]+-[0-9]{2}$"
SCENARIO_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Epoch(str, Enum):
    INITIATION = "INITIATION"
    SUBACUTE = "SUBACUTE"
    TRANSITION = "TRANSITION"
    ESTABLISHED_CHRONIC = "ESTABLISHED_CHRONIC"

    @classmethod
    def from_tick(cls, tick: int) -> "Epoch":
        if tick < 0:
            raise ValueError(f"tick must be >= 0, got {tick}")
        if tick <= 3:
            return cls.INITIATION
        if tick <= 14:
            return cls.SUBACUTE
        if tick <= 28:
            return cls.TRANSITION
        return cls.ESTABLISHED_CHRONIC


class AgentTier(str, Enum):
    HUB = "HUB"
    MID = "MID"
    PERIPHERAL = "PERIPHERAL"


class DynamicsRule(_StrictModel):
    rule_id: str = Field(pattern=RULE_ID_PATTERN)
    description: str
    claim_refs: list[str] = Field(default_factory=list)
    direction: Literal["up", "down", "set"]
    magnitude_hint: float | None = Field(default=None, ge=0.0, le=1.0)


class InfluenceEdge(_StrictModel):
    source_id: str
    relation: str
    sign: int = Field(ge=-1, le=1)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    validation_status: str | None = None
    neutral_ok: bool = False


class AgentCard(_StrictModel):
    id: str
    label: str
    entity_type: str
    compartment: str
    tier: AgentTier
    community: int
    baseline_state: float = Field(default=0.5, ge=0.0, le=1.0)
    normal_role: str = Field(default="", max_length=2000)
    pathological_rules: list[DynamicsRule] = Field(default_factory=list)
    inbound_edges: list[InfluenceEdge] = Field(default_factory=list)
    outbound_ids: list[str] = Field(default_factory=list)
    rule_gap_reason: str | None = None
    source_note: str | None = None

    @model_validator(mode="after")
    def _check_hub_rules_and_neutral_edges(self) -> "AgentCard":
        if (
            self.tier is AgentTier.HUB
            and not self.pathological_rules
            and not self.rule_gap_reason
        ):
            raise ValueError(
                f"hub agent '{self.id}' requires at least one pathological_rule "
                "or an explicit rule_gap_reason"
            )
        for edge in self.inbound_edges:
            if edge.sign == 0 and not edge.neutral_ok:
                raise ValueError(
                    f"inbound edge from '{edge.source_id}' has sign 0; "
                    "set neutral_ok=True to accept it explicitly"
                )
        return self


class InfluencePacket(_StrictModel):
    source_id: str
    sign: int = Field(ge=-1, le=1)
    weight: float = Field(ge=0.0, le=1.0)
    sender_state: float = Field(ge=0.0, le=1.0)
    sender_baseline: float = Field(default=0.5, ge=0.0, le=1.0)
    tick: int = Field(ge=0)


class StateDelta(_StrictModel):
    agent_id: str
    tick: int = Field(ge=0)
    new_state: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(max_length=500)
    refs: list[str] = Field(min_length=1)
    emitter: Literal["llm", "rules"]


class Readout(_StrictModel):
    pain_score: float = Field(ge=0.0, le=1.0)
    barrier_integrity: float = Field(ge=0.0, le=1.0)
    inflammation_index: float = Field(ge=0.0, le=1.0)


class WorldState(_StrictModel):
    tick: int
    epoch: Epoch
    states: dict[str, float]
    readouts: Readout | None = None

    @field_validator("states")
    @classmethod
    def _states_in_unit_range(cls, v: dict[str, float]) -> dict[str, float]:
        offenders = validate_state_values(v)
        if offenders:
            raise ValueError(f"agent states outside [0,1]: {', '.join(offenders)}")
        return v


class Perturbation(_StrictModel):
    agent_id: str
    value: float = Field(ge=0.0, le=1.0)


class SustainedDrive(_StrictModel):
    """Tonic scenario-level excitation for one agent.

    While start_tick <= tick < end_tick (end_tick None = through the whole
    horizon) the engine adds (value - baseline_agent) * DRIVE_GAIN as a
    constant positive deviation contribution to the agent's inbound
    excitation, modeling tonic drivers such as ectopic firing or sustained
    glial activation.
    """

    agent_id: str
    value: float = Field(ge=0.0, le=1.0)
    start_tick: int = Field(ge=0)
    end_tick: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _window_ordering(self) -> "SustainedDrive":
        if self.end_tick is not None and self.end_tick <= self.start_tick:
            raise ValueError(
                f"sustained drive on '{self.agent_id}' has inverted window: "
                f"end_tick {self.end_tick} <= start_tick {self.start_tick}"
            )
        return self


class DrugArm(_StrictModel):
    name: str
    target_agent_ids: list[str]
    start_tick: int = Field(ge=0)
    end_tick: int | None = Field(default=None, ge=0)
    effect_sign: int
    magnitude: float = Field(ge=0.0, le=1.0)

    @field_validator("effect_sign")
    @classmethod
    def _effect_sign_domain(cls, v: int) -> int:
        if v not in (-1, 1):
            raise ValueError("effect_sign must be -1 or 1")
        return v

    @model_validator(mode="after")
    def _window_ordering(self) -> "DrugArm":
        if self.end_tick is not None and self.end_tick <= self.start_tick:
            raise ValueError(
                f"drug arm '{self.name}' has inverted window: "
                f"end_tick {self.end_tick} <= start_tick {self.start_tick}"
            )
        return self


class ScenarioConfig(_StrictModel):
    name: str = Field(pattern=SCENARIO_NAME_PATTERN)
    horizon_days: int = Field(default=180, ge=1, le=180)
    injury_model: Literal["naive", "SNI", "CCI", "SNL", "CIPN", "other"]
    injury_tick: int | None = Field(default=None, ge=0)
    drug_arms: list[DrugArm] = Field(default_factory=list)
    sustained_drives: list[SustainedDrive] = Field(default_factory=list)
    initial_perturbations: list[Perturbation] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _check_injury_and_arms(self) -> "ScenarioConfig":
        if self.injury_model == "naive":
            if self.injury_tick is not None:
                raise ValueError("injury_tick must be None when injury_model is 'naive'")
        elif self.injury_tick is None:
            raise ValueError(
                f"injury_tick is required when injury_model is '{self.injury_model}'"
            )
        for arm in self.drug_arms:
            if arm.start_tick >= self.horizon_days:
                raise ValueError(
                    f"drug arm '{arm.name}' starts at tick {arm.start_tick}, "
                    f"beyond horizon {self.horizon_days}"
                )
            if arm.end_tick is not None and arm.end_tick >= self.horizon_days:
                raise ValueError(
                    f"drug arm '{arm.name}' ends at tick {arm.end_tick}, "
                    f"beyond horizon {self.horizon_days}"
                )
        for drive in self.sustained_drives:
            if drive.start_tick >= self.horizon_days:
                raise ValueError(
                    f"sustained drive on '{drive.agent_id}' starts at tick "
                    f"{drive.start_tick}, beyond horizon {self.horizon_days}"
                )
        return self


class TickAuditEntry(_StrictModel):
    tick: int = Field(ge=0)
    agent_id: str
    emitter: Literal["llm", "rules"]
    prompt_sha256: str | None = None
    response_sha256: str | None = None
    cache_hit: bool
    latency_ms: float | None = None


class TickLog(_StrictModel):
    tick: int
    epoch: Epoch
    deltas_applied: list[StateDelta]
    world_after: WorldState
    audit: list[TickAuditEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_delta_agents(self) -> "TickLog":
        counts = Counter(delta.agent_id for delta in self.deltas_applied)
        duplicates = sorted(agent_id for agent_id, n in counts.items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate agent_id in deltas_applied: {', '.join(duplicates)}")
        return self


class RunManifest(_StrictModel):
    scenario: ScenarioConfig
    started_at_utc: str
    seed: int
    engine_version: str = Field(default="0.1.0", pattern=SEMVER_PATTERN)
    card_set_hash: str


def epoch_for(tick: int) -> Epoch:
    return Epoch.from_tick(tick)


def validate_state_values(states: dict[str, float]) -> list[str]:
    return sorted(a for a, s in states.items() if not (0.0 <= s <= 1.0))


def validate_states(world: WorldState) -> None:
    offenders = validate_state_values(world.states)
    if offenders:
        raise ValueError(f"agent states outside [0,1]: {', '.join(offenders)}")
