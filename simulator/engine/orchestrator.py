"""Tick orchestrator: one simulated day per step().

Emitter choice per agent per tick:
  - LLM path only when a client is provided AND the agent is HUB tier AND
    the tick is an epoch boundary {4, 15, 29} or scenario.injury_tick.
  - Everything else uses the deterministic rule fallback every tick.

Drug arms act as additive pressure on their targets' rule computation
(targets' own states are never written directly). All StateDeltas for a
tick are computed against the same pre-tick snapshot and applied
atomically.
"""

import argparse
import csv
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from simulator.engine.llm_agent import DeltaCache, OpenCodeClient, evaluate_llm_delta
from simulator.engine.rule_fallback import compute_influence, rule_next_state
from simulator.readouts import compute_readouts
from simulator.schemas import (
    AgentCard,
    Epoch,
    InfluencePacket,
    RunManifest,
    ScenarioConfig,
    StateDelta,
    TickAuditEntry,
    TickLog,
    WorldState,
    validate_states,
)

logger = logging.getLogger(__name__)

EPOCH_BOUNDARY_TICKS = frozenset({4, 15, 29})
ENGINE_VERSION = "0.1.0"


def resolve_label(cards: list[AgentCard], label_substr: str) -> AgentCard:
    needle = label_substr.lower()
    for card in sorted(cards, key=lambda c: c.id):
        if needle in card.label.lower():
            return card
    raise LookupError(f"no card label contains {label_substr!r}")


def _card_content_sha(card: AgentCard) -> str:
    canonical = json.dumps(card.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Orchestrator:
    def __init__(
        self,
        cards: list[AgentCard],
        scenario: ScenarioConfig,
        llm_client=None,
        seed: int = 0,
        cache: DeltaCache | None = None,
    ):
        self.cards_by_id: dict[str, AgentCard] = {c.id: c for c in sorted(cards, key=lambda c: c.id)}
        self.scenario = scenario
        self.llm_client = llm_client
        self.seed = seed
        self.cache = cache if cache is not None else DeltaCache()
        self._validate_edge_endpoints()
        if scenario.injury_model != "naive" and not scenario.initial_perturbations:
            raise NotImplementedError(
                f"scenario '{scenario.name}' ({scenario.injury_model}) declares no "
                "initial_perturbations; non-naive scenarios must seed injury explicitly "
                "(see resolve_label)"
            )
        if scenario.injury_model == "naive" and scenario.initial_perturbations:
            raise ValueError("naive scenarios must not declare initial_perturbations")
        states = {cid: card.baseline_state for cid, card in self.cards_by_id.items()}
        for pert in scenario.initial_perturbations:
            if pert.agent_id not in states:
                raise ValueError(f"perturbation targets unknown agent '{pert.agent_id}'")
            states[pert.agent_id] = pert.value
        readout = compute_readouts(states, self.cards_by_id)
        self.world = WorldState(tick=0, epoch=Epoch.from_tick(0), states=states, readouts=readout)
        self.manifest = RunManifest(
            scenario=scenario,
            started_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            seed=seed,
            engine_version=ENGINE_VERSION,
            card_set_hash=self._card_set_hash(),
        )

    def _validate_edge_endpoints(self) -> None:
        missing = sorted(
            {
                edge.source_id
                for card in self.cards_by_id.values()
                for edge in card.inbound_edges
                if edge.source_id not in self.cards_by_id
            }
        )
        if missing:
            logger.warning(
                "%d inbound-edge sources absent from card set (edges skipped): %s",
                len(missing),
                ", ".join(missing),
            )

    def _card_set_hash(self) -> str:
        joined = "\n".join(
            f"{cid}:{_card_content_sha(card)}" for cid, card in sorted(self.cards_by_id.items())
        )
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def _llm_eligible_ticks(self) -> frozenset[int]:
        ticks = set(EPOCH_BOUNDARY_TICKS)
        if self.scenario.injury_tick is not None:
            ticks.add(self.scenario.injury_tick)
        return frozenset(ticks)

    def _build_packets(self, agent_id: str, tick: int) -> list[InfluencePacket]:
        packets = []
        for edge in self.cards_by_id[agent_id].inbound_edges:
            sender = self.cards_by_id.get(edge.source_id)
            if sender is None:
                continue
            packets.append(
                InfluencePacket(
                    source_id=edge.source_id,
                    sign=edge.sign,
                    weight=edge.weight,
                    sender_state=self.world.states[edge.source_id],
                    sender_baseline=sender.baseline_state,
                    tick=tick,
                )
            )
        return packets

    def _drug_pressures(self, tick: int) -> dict[str, float]:
        pressures: dict[str, float] = {}
        for arm in self.scenario.drug_arms:
            active = arm.start_tick <= tick and (arm.end_tick is None or tick < arm.end_tick)
            if not active:
                continue
            pressure = arm.effect_sign * arm.magnitude
            for target in arm.target_agent_ids:
                pressures[target] = pressures.get(target, 0.0) + pressure
        return pressures

    def _rule_delta(self, agent_id: str, tick: int, packets, drug_pressure: float):
        card = self.cards_by_id[agent_id]
        current = self.world.states[agent_id]
        new_state = rule_next_state(card, current, packets, drug_pressure)
        refs = (
            [r.rule_id for r in card.pathological_rules]
            or [p.source_id for p in packets]
            or [card.id]
        )
        rationale = (
            f"rules: I={compute_influence(packets):+.4f} drug={drug_pressure:+.4f} "
            f"epoch={Epoch.from_tick(tick).value}"
        )
        return StateDelta(
            agent_id=agent_id,
            tick=tick,
            new_state=new_state,
            rationale=rationale[:500],
            refs=refs,
            emitter="rules",
        )

    def step(self) -> TickLog:
        tick = self.world.tick
        pressures = self._drug_pressures(tick)
        llm_ticks = self._llm_eligible_ticks()
        deltas = []
        audit = []
        for agent_id in sorted(self.cards_by_id):
            card = self.cards_by_id[agent_id]
            packets = self._build_packets(agent_id, tick)
            drug_pressure = pressures.get(agent_id, 0.0)
            use_llm = (
                self.llm_client is not None
                and card.tier.value == "HUB"
                and tick in llm_ticks
            )
            if use_llm:
                attempt = evaluate_llm_delta(
                    card,
                    packets,
                    self.world.states[agent_id],
                    Epoch.from_tick(tick),
                    tick,
                    self.llm_client,
                    cache=self.cache,
                )
                audit.append(
                    TickAuditEntry(
                        tick=tick,
                        agent_id=agent_id,
                        emitter="llm" if attempt.delta is not None else "rules",
                        prompt_sha256=attempt.prompt_sha256 if attempt.delta is not None else None,
                        response_sha256=attempt.response_sha256
                        if attempt.delta is not None
                        else None,
                        cache_hit=attempt.cache_hit,
                        latency_ms=attempt.latency_ms if not attempt.cache_hit else None,
                    )
                )
                if attempt.delta is not None:
                    deltas.append(attempt.delta)
                    continue
            deltas.append(self._rule_delta(agent_id, tick, packets, drug_pressure))
            if not use_llm:
                audit.append(TickAuditEntry(tick=tick, agent_id=agent_id, emitter="rules", cache_hit=False))
        new_states = dict(self.world.states)
        for delta in deltas:
            new_states[delta.agent_id] = delta.new_state
        next_tick = tick + 1
        world_after = WorldState(
            tick=next_tick,
            epoch=Epoch.from_tick(next_tick),
            states=new_states,
        )
        validate_states(world_after)
        world_after = world_after.model_copy(
            update={"readouts": compute_readouts(new_states, self.cards_by_id)}
        )
        log = TickLog(tick=tick, epoch=Epoch.from_tick(tick), deltas_applied=deltas, world_after=world_after, audit=audit)
        self.world = world_after
        return log

    def run(self) -> list[TickLog]:
        return [self.step() for _ in range(self.scenario.horizon_days)]

    def save_run(self, logs: list[TickLog], out_dir: str | Path | None = None) -> Path:
        out_path = Path(out_dir) if out_dir is not None else Path(".")
        out_path.mkdir(parents=True, exist_ok=True)
        manifest_payload = {
            "manifest": self.manifest.model_dump(mode="json"),
            "scenario_echo": self.scenario.model_dump(mode="json"),
        }
        (out_path / "manifest.json").write_text(
            json.dumps(manifest_payload, sort_keys=True, indent=2) + "\n"
        )
        with (out_path / "tick_log.jsonl").open("w") as fh:
            for log in logs:
                fh.write(
                    json.dumps(log.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
        rows = []
        for log in logs:
            for agent_id in sorted(log.world_after.states):
                rows.append((log.world_after.tick, agent_id, log.world_after.states[agent_id]))
        with (out_path / "states.csv").open("w", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["tick", "agent_id", "state"])
            writer.writerows(rows)
        return out_path


def load_scenario(path: str | Path) -> ScenarioConfig:
    data = yaml.safe_load(Path(path).read_text())
    return ScenarioConfig(**data)


def load_cards(cards_dir: str | Path) -> list[AgentCard]:
    directory = Path(cards_dir)
    cards = []
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        cards.append(AgentCard(**yaml.safe_load(path.read_text())))
    return cards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the CP simulator engine")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cards", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--llm-bin", default=None, help="enable LLM hub path via this CLI binary")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    scenario = load_scenario(args.scenario)
    cards = load_cards(args.cards)
    client = OpenCodeClient(bin_path=args.llm_bin) if args.llm_bin else None
    orch = Orchestrator(cards=cards, scenario=scenario, llm_client=client, seed=args.seed)
    logs = orch.run()
    out_dir = orch.save_run(logs, args.out)
    final = logs[-1].world_after
    print(
        f"run complete: ticks={len(logs)} final_tick={final.tick} "
        f"pain={final.readouts.pain_score:.4f} "
        f"inflammation={final.readouts.inflammation_index:.4f} "
        f"barrier_integrity={final.readouts.barrier_integrity:.4f} -> {out_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
