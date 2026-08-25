"""Literature-grounded facts harness (Task 2.6).

Loads the curated assertion library `simulator/validation/facts.yaml`,
executes every referenced scenario exactly once through the deterministic
rule engine (runs are shared across facts via a registry), evaluates each
fact against the logs, writes `simulator/reports/facts_report.md`, and
exits non-zero unless every fact passes.

Fact kinds: stability_bound, ordering_pair, readout_threshold,
drug_effect, determinism. Crossing-time events reuse first_crossing from
the pilot acceptance module instead of duplicating it. All outputs are
deterministic for a given card set and facts file.
"""

import argparse
import json
import logging
import operator
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from simulator.engine.llm_agent import DeltaCache
from simulator.engine.orchestrator import Orchestrator, load_cards, load_scenario
from simulator.validation.pilot_acceptance import _first_crossing_series, first_crossing

logger = logging.getLogger(__name__)

FACTS_YAML = Path(__file__).resolve().parent / "facts.yaml"
DEFAULT_REPORT = Path("simulator/reports/facts_report.md")

KINDS = frozenset(
    {"readout_threshold", "ordering_pair", "drug_effect", "stability_bound", "determinism"}
)
READOUT_NAMES = ("pain_score", "inflammation_index", "barrier_integrity")
COMPARATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
RERUN_SUFFIX = "__rerun"
CACHE_WARM_SUFFIX = "__cache_warm"
CACHE_SECOND_SUFFIX = "__cache_second"


@dataclass
class FactResult:
    id: str
    claim: str
    source_ref: str
    kind: str
    expected: str
    observed: str
    passed: bool


class FakeLLMClient:
    """Deterministic stand-in LLM client used for cache-sanity checks."""

    def __init__(self):
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        return (
            '{"new_state": 0.85, "rationale": "fake client deterministic response", '
            '"refs": ["fake-ref"]}'
        )


def resolve_source_ref(repo_root: str | Path, ref: str) -> bool:
    """True when `ref` points at an existing repo artifact.

    Supported forms: 'theme_NN' or 'theme_NN#F.N.M' (sweep file + finding
    header), 'EC-####' (edge-claim id in analysis/claims/claims.json), or a
    repo-relative dossier path such as 'KCC2.md'.
    """
    ref = ref.strip()
    root = Path(repo_root)
    if ref.startswith("theme_"):
        theme_id, _, fragment = ref.partition("#")
        matches = sorted((root / "analysis" / "literature").glob(f"{theme_id}_*.md"))
        if not matches:
            return False
        if not fragment:
            return True
        pattern = re.compile(rf"^###\s+{re.escape(fragment)}:", re.MULTILINE)
        return any(pattern.search(p.read_text(errors="replace")) for p in matches)
    if re.fullmatch(r"EC-\d+", ref):
        try:
            claims = json.loads((root / "analysis" / "claims" / "claims.json").read_text())
        except (OSError, json.JSONDecodeError):
            return False
        return isinstance(claims, list) and any(
            isinstance(c, dict) and c.get("id") == ref for c in claims
        )
    return (root / ref).is_file()


def load_facts(path: str | Path = FACTS_YAML) -> list[dict]:
    """Parse and validate the facts YAML; raises ValueError on any defect."""
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict) or not isinstance(data.get("facts"), list) or not data["facts"]:
        raise ValueError(f"{path}: expected a top-level 'facts' list")
    facts = data["facts"]
    seen_ids: set[str] = set()
    for position, fact in enumerate(facts):
        where = f"{path} fact #{position}"
        if not isinstance(fact, dict):
            raise ValueError(f"{where}: not a mapping")
        for field in ("id", "claim", "source_ref", "kind", "params"):
            if not fact.get(field):
                raise ValueError(f"{where}: missing required field '{field}'")
        fid = fact["id"]
        where = f"{path} {fid}"
        if not re.fullmatch(r"F-\d{2}", str(fid)):
            raise ValueError(f"{where}: id must match F-NN")
        if fid in seen_ids:
            raise ValueError(f"{where}: duplicate id")
        seen_ids.add(fid)
        if fact["kind"] not in KINDS:
            raise ValueError(f"{where}: unknown kind '{fact['kind']}'")
        if not isinstance(fact["params"], dict):
            raise ValueError(f"{where}: params must be a mapping")
        _validate_params(fact["kind"], fact["params"], where)
    return facts


def _validate_params(kind: str, params: dict, where: str) -> None:

    def _scenario(key: str) -> None:
        if not params.get(key):
            raise ValueError(f"{where}: params.{key} is required")

    if kind == "stability_bound":
        _scenario("scenario")
        targets = sum(bool(params.get(k)) for k in ("readout", "agent_id", "states_bounded"))
        if targets != 1:
            raise ValueError(
                f"{where}: stability_bound needs exactly one of "
                "readout | agent_id | states_bounded"
            )
        if params.get("readout") and params["readout"] not in READOUT_NAMES:
            raise ValueError(f"{where}: unknown readout '{params['readout']}'")
        if params.get("states_bounded"):
            return
        relative = bool(params.get("vs_scenario"))
        if not relative and params.get("comparator") not in COMPARATORS:
            raise ValueError(
                f"{where}: stability_bound needs vs_scenario or comparator"
            )
        if relative and not isinstance(params.get("min_gap"), (int, float)):
            raise ValueError(f"{where}: numeric min_gap is required")
        if not relative and not isinstance(params.get("value"), (int, float)):
            raise ValueError(f"{where}: numeric 'value' is required")
    elif kind == "ordering_pair":
        _scenario("scenario")
        for side in ("earlier", "later"):
            event = params.get(side)
            if not isinstance(event, dict):
                raise ValueError(f"{where}: params.{side} must be a mapping")
            has_agent = bool(event.get("agent"))
            has_readout = bool(event.get("readout"))
            if has_agent == has_readout:
                raise ValueError(f"{where}: params.{side} needs exactly one of agent|readout")
            if has_readout and event["readout"] not in READOUT_NAMES:
                raise ValueError(f"{where}: unknown readout '{event['readout']}'")
            if event.get("direction") not in ("up", "down"):
                raise ValueError(f"{where}: params.{side}.direction must be up|down")
    elif kind == "readout_threshold":
        _scenario("scenario")
        relative = bool(params.get("vs_scenario"))
        if not relative and params.get("comparator") not in COMPARATORS:
            raise ValueError(
                f"{where}: readout_threshold needs vs_scenario or comparator"
            )
        if params.get("readout") not in READOUT_NAMES:
            raise ValueError(f"{where}: params.readout is required and must be valid")
    elif kind == "drug_effect":
        _scenario("treatment")
        _scenario("control")
        if bool(params.get("readout")) == bool(params.get("agent_id")):
            raise ValueError(f"{where}: drug_effect needs exactly one of readout|agent_id")
        if params.get("readout") and params["readout"] not in READOUT_NAMES:
            raise ValueError(f"{where}: unknown readout '{params['readout']}'")
        if not isinstance(params.get("min_reduction"), (int, float)):
            raise ValueError(f"{where}: numeric min_reduction is required")
    elif kind == "determinism":
        _scenario("scenario")
        if params.get("check") not in ("byte_identical_rerun", "cached_second_run_zero_llm"):
            raise ValueError(f"{where}: unknown determinism check '{params.get('check')}'")


def _window(params: dict) -> tuple[float, float]:
    lo_hi = params.get("window")
    return (float("-inf"), float("inf")) if lo_hi is None else (float(lo_hi[0]), float(lo_hi[1]))


def _in_window(tick: int, lo: float, hi: float) -> bool:
    return lo <= tick <= hi


def _agg(values: list[float], agg: str) -> float:
    if not values:
        raise ValueError("empty window: no logged ticks matched")
    if agg == "max":
        return max(values)
    if agg == "min":
        return min(values)
    return sum(values) / len(values)


def _series(logs: list, key_fn) -> list[tuple[int, float]]:
    return [(log.world_after.tick, key_fn(log)) for log in logs]


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def eval_stability_bound(fact: dict, ctx: dict) -> tuple[str, str, bool]:
    p = fact["params"]
    logs = ctx["runs"][p["scenario"]]
    if p.get("states_bounded"):
        offenders = sorted(
            (log.world_after.tick, agent_id)
            for log in logs
            for agent_id, state in log.world_after.states.items()
            if not 0.0 <= state <= 1.0
        )
        observed = (
            "all states in [0,1] at every tick" if not offenders else
            f"violations at {offenders[:5]}{'...' if len(offenders) > 5 else ''}"
        )
        return "[0,1] everywhere", observed, not offenders
    lo, hi = _window(p)
    if p.get("readout"):
        extractor = lambda log: getattr(log.world_after.readouts, p["readout"])  # noqa: E731
        subject = p["readout"]
    else:
        extractor = lambda log: log.world_after.states[p["agent_id"]]  # noqa: E731
        subject = f"state[{p['agent_id']}]"
    series = _series(logs, extractor)
    values = [v for tick, v in series if _in_window(tick, lo, hi)]
    agg = p.get("agg", "max")
    observed_value = _agg(values, agg)
    window_str = f"[{p['window'][0]},{p['window'][1]}]" if p.get("window") else "[all ticks]"
    if p.get("vs_scenario"):
        ref_series = _series(ctx["runs"][p["vs_scenario"]], extractor)
        ref_values = [v for tick, v in ref_series if _in_window(tick, lo, hi)]
        reference_value = _agg(ref_values, agg)
        gap = float(p["min_gap"])
        observed_gap = reference_value - observed_value
        expected = (
            f"{agg} {subject} {p['scenario']} is below {p['vs_scenario']} by "
            f">= {_fmt(gap)} over {window_str}"
        )
        observed = (
            f"gap={_fmt(observed_gap)} "
            f"({_fmt(reference_value)} -> {_fmt(observed_value)})"
        )
        return expected, observed, observed_gap >= gap
    comparator = COMPARATORS[p["comparator"]]
    threshold = float(p["value"])
    expected = (
        f"{agg} {subject} over {window_str} {p['comparator']} {_fmt(threshold)}"
    )
    return expected, f"{subject}={_fmt(observed_value)}", comparator(observed_value, threshold)


def _crossing_tick(event: dict, runs: dict, scenario: str, cards_by_id: dict, defaults: dict) -> int | None:
    delta = float(event.get("delta", defaults.get("delta", 0.15)))
    sustain = int(event.get("sustain", defaults.get("sustain", 2)))
    direction = event["direction"]
    scenario_logs = runs[scenario]
    if event.get("agent"):
        agent_id = event["agent"]
        card = cards_by_id.get(agent_id)
        baseline = event.get("baseline", card.baseline_state if card else None)
        return first_crossing(
            scenario_logs, agent_id, delta=delta, sustain=sustain,
            direction=direction, baseline=baseline,
        )
    readout_name = event["readout"]

    def readout_series(logs: list) -> list[tuple[int, float]]:
        return _series(
            logs, lambda log: getattr(log.world_after.readouts, readout_name)
        )

    series = readout_series(scenario_logs)
    if "baseline_from" in event:
        ref_values = [v for _, v in readout_series(runs[event["baseline_from"]["scenario"]])]
        baseline = _agg(ref_values, event["baseline_from"].get("agg", "mean"))
    else:
        baseline = float(event["baseline"])
    index = _first_crossing_series([v for _, v in series], baseline, delta, sustain, direction)
    return None if index is None else series[index][0]


def eval_ordering_pair(fact: dict, ctx: dict) -> tuple[str, str, bool]:
    p = fact["params"]
    scenario = p["scenario"]
    tolerance = int(p.get("tolerance", 1))
    earlier = _crossing_tick(p["earlier"], ctx["runs"], scenario, ctx["cards_by_id"], p)
    later = _crossing_tick(p["later"], ctx["runs"], scenario, ctx["cards_by_id"], p)

    def fmt_side(side: dict, tick: int | None) -> str:
        name = side.get("agent") or f"readout:{side['readout']}"
        return f"{name}@{'t=' + str(tick) if tick is not None else 'never'}"

    expected = (
        f"{fmt_side(p['earlier'], None).split('@')[0]} crosses before/equal "
        f"{fmt_side(p['later'], None).split('@')[0]} (+/-{tolerance} tick)"
    )
    observed = f"{fmt_side(p['earlier'], earlier)} vs {fmt_side(p['later'], later)}"
    passed = earlier is not None and later is not None and earlier <= later + tolerance
    return expected, observed, passed


def eval_readout_threshold(fact: dict, ctx: dict) -> tuple[str, str, bool]:
    p = fact["params"]

    def mean_of(scenario: str) -> float:
        lo, hi = _window(p)
        values = [
            v for tick, v in _series(
                ctx["runs"][scenario],
                lambda log: getattr(log.world_after.readouts, p["readout"]),
            )
            if _in_window(tick, lo, hi)
        ]
        return _agg(values, p.get("agg", "mean"))

    window_str = (
        f"[{p['window'][0]},{p['window'][1]}]" if p.get("window") else "[all ticks]"
    )
    if p.get("vs_scenario"):
        treatment_mean, control_mean = mean_of(p["scenario"]), mean_of(p["vs_scenario"])
        gap = float(p["min_gap"])
        observed_gap = treatment_mean - control_mean
        expected = (
            f"mean {p['readout']} {p['scenario']} - {p['vs_scenario']} over {window_str} "
            f">= {_fmt(gap)}"
        )
        observed = f"gap={_fmt(observed_gap)} ({_fmt(treatment_mean)} vs {_fmt(control_mean)})"
        return expected, observed, observed_gap >= gap
    lo, hi = _window(p)
    values = [
        v for tick, v in _series(
            ctx["runs"][p["scenario"]],
            lambda log: getattr(log.world_after.readouts, p["readout"]),
        )
        if _in_window(tick, lo, hi)
    ]
    observed_value = _agg(values, p.get("agg", "mean"))
    comparator = COMPARATORS[p["comparator"]]
    threshold = float(p["value"])
    expected = (
        f"mean {p['readout']} over {window_str} {p['comparator']} {_fmt(threshold)}"
    )
    return expected, f"observed={_fmt(observed_value)}", comparator(observed_value, threshold)


def eval_drug_effect(fact: dict, ctx: dict) -> tuple[str, str, bool]:
    p = fact["params"]
    lo, hi = _window(p)

    def mean_over(scenario: str) -> float:
        if p.get("readout"):
            extractor = lambda log: getattr(log.world_after.readouts, p["readout"])  # noqa: E731
            target = f"readout {p['readout']}"
        else:
            extractor = lambda log: log.world_after.states[p["agent_id"]]  # noqa: E731
            target = f"state[{p['agent_id']}]"
        values = [
            v for tick, v in _series(ctx["runs"][scenario], extractor)
            if _in_window(tick, lo, hi)
        ]
        return _agg(values, "mean"), target

    control_mean, target = mean_over(p["control"])
    treatment_mean, _ = mean_over(p["treatment"])
    reduction = control_mean - treatment_mean
    min_reduction = float(p["min_reduction"])
    window_str = (
        f"[{p['window'][0]},{p['window'][1]}]" if p.get("window") else "[all ticks]"
    )
    expected = f"mean {target} reduction >= {_fmt(min_reduction)} over {window_str}"
    observed = (
        f"{p['control']}-{p['treatment']}={_fmt(reduction)} "
        f"({_fmt(control_mean)} -> {_fmt(treatment_mean)})"
    )
    return expected, observed, reduction >= min_reduction


def eval_determinism(fact: dict, ctx: dict) -> tuple[str, str, bool]:
    p = fact["params"]
    scenario = p["scenario"]
    runs = ctx["runs"]
    if p["check"] == "byte_identical_rerun":
        rerun_key = scenario + RERUN_SUFFIX
        left = serialize_run(runs[scenario])
        right = serialize_run(runs[rerun_key])
        passed = left == right
        return (
            f"tick_log bytes identical across reruns of {scenario}",
            "identical" if passed else "diverged",
            passed,
        )
    second_calls = int(ctx["meta"].get("cache_second_run_calls", -1))
    warm_calls = int(ctx["meta"].get("cache_warm_calls", -1))
    passed = second_calls == 0 and warm_calls > 0
    return (
        "cached second run makes 0 LLM calls",
        f"warm={warm_calls}, second={second_calls}",
        passed,
    )


_EVALUATORS = {
    "stability_bound": eval_stability_bound,
    "ordering_pair": eval_ordering_pair,
    "readout_threshold": eval_readout_threshold,
    "drug_effect": eval_drug_effect,
    "determinism": eval_determinism,
}


def evaluate_fact(fact: dict, ctx: dict) -> FactResult:
    kind = fact["kind"]
    if kind not in _EVALUATORS:
        raise ValueError(f"unknown fact kind '{kind}'")
    _validate_params(kind, fact.get("params") or {}, f"fact {fact.get('id', '?')}")
    expected, observed, passed = _EVALUATORS[kind](fact, ctx)
    return FactResult(
        id=fact["id"],
        claim=fact["claim"].strip(),
        source_ref=fact["source_ref"],
        kind=kind,
        expected=expected,
        observed=observed,
        passed=bool(passed),
    )


def serialize_run(logs: list) -> bytes:
    """Byte-canonical serialization matching save_run's tick_log.jsonl."""
    return "".join(
        json.dumps(log.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
        for log in logs
    ).encode("utf-8")


def _required_scenarios(facts: list[dict]) -> set[str]:
    names: set[str] = set()

    def scan(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("scenario", "vs_scenario", "treatment", "control") and isinstance(value, str):
                    names.add(value)
                elif key == "baseline_from" and isinstance(value, dict):
                    scan(value)
                else:
                    scan(value)
        elif isinstance(node, list):
            for item in node:
                scan(item)

    for fact in facts:
        scan(fact["params"])
    return names


def run_checks(
    cards_dir: str | Path,
    scenarios_dir: str | Path | None = None,
    out_dir: str | Path | None = None,
    facts_path: str | Path = FACTS_YAML,
) -> list[FactResult]:
    """Run every needed scenario once, evaluate all facts, optionally write report."""
    scenarios_dir = (
        Path(scenarios_dir)
        if scenarios_dir is not None
        else Path(__file__).resolve().parents[1] / "scenarios"
    )
    cards = load_cards(cards_dir)
    cards_by_id = {c.id: c for c in cards}
    facts = load_facts(facts_path)

    scenario_files = {}
    for path in sorted(scenarios_dir.glob("*.yaml")):
        config = load_scenario(path)
        scenario_files[config.name] = path
    runs: dict[str, list] = {}

    def run_once(name: str) -> list:
        if name not in scenario_files:
            raise LookupError(f"no scenario named '{name}' under {scenarios_dir}")
        orch = Orchestrator(cards=cards, scenario=load_scenario(scenario_files[name]),
                            llm_client=None, seed=0)
        logs = orch.run()
        runs[name] = logs
        if out_dir is not None:
            orch.save_run(logs, Path(out_dir) / name)
        return logs

    for name in sorted(_required_scenarios(facts)):
        run_once(name)

    meta: dict = {}
    for fact in facts:
        params = fact["params"]
        if fact["kind"] == "determinism":
            scenario = params["scenario"]
            if params["check"] == "byte_identical_rerun" and scenario + RERUN_SUFFIX not in runs:
                run_once(scenario)
                runs[scenario + RERUN_SUFFIX] = run_once(scenario)
            elif params["check"] == "cached_second_run_zero_llm":
                warm_key, second_key = scenario + CACHE_WARM_SUFFIX, scenario + CACHE_SECOND_SUFFIX
                if warm_key not in runs:
                    cache = DeltaCache()
                    warm_client = FakeLLMClient()
                    orch = Orchestrator(
                        cards=cards,
                        scenario=load_scenario(scenario_files[scenario]),
                        llm_client=warm_client,
                        seed=0,
                        cache=cache,
                    )
                    runs[warm_key] = orch.run()
                    if warm_client.calls == 0:
                        raise RuntimeError(
                            f"cache-warm run for '{scenario}' made no LLM calls; "
                            "check is vacuous"
                        )
                    second_client = FakeLLMClient()
                    orch2 = Orchestrator(
                        cards=cards,
                        scenario=load_scenario(scenario_files[scenario]),
                        llm_client=second_client,
                        seed=0,
                        cache=cache,
                    )
                    runs[second_key] = orch2.run()
                    meta["cache_warm_calls"] = warm_client.calls
                    meta["cache_second_run_calls"] = second_client.calls

    results = [evaluate_fact(fact, {"runs": runs, "cards_by_id": cards_by_id, "meta": meta})
               for fact in facts]
    if out_dir is not None:
        report_path = Path(out_dir) / "facts_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_markdown(results))
    return results


def render_markdown(results: list[FactResult]) -> str:
    lines = [
        "# Facts Report — literature-grounded simulation checks",
        "",
        "| id | claim | source_ref | expected | observed | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        claim = r.claim.replace("|", "/").replace("\n", " ")
        expected = r.expected.replace("|", "/")
        observed = r.observed.replace("|", "/")
        lines.append(
            f"| {r.id} | {claim} | {r.source_ref} | {expected} | {observed} "
            f"| {'PASS' if r.passed else 'FAIL'} |"
        )
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    lines += [
        "",
        f"Overall: {'PASS' if passed == total else 'FAIL'} ({passed}/{total} facts)",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the facts validation harness")
    parser.add_argument("--cards", default="simulator/agent_cards")
    parser.add_argument("--scenarios-dir", default="simulator/scenarios")
    parser.add_argument("--facts", default=str(FACTS_YAML))
    parser.add_argument("--out-dir", default=None, help="optional per-run output directory")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    results = run_checks(args.cards, args.scenarios_dir, args.out_dir, args.facts)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(results))
    passed = sum(1 for r in results if r.passed)
    print(
        f"facts harness: {'PASS' if passed == len(results) else 'FAIL'} "
        f"({passed}/{len(results)} facts) -> {report_path}"
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
