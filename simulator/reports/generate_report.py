"""Experiment report generator for the CP simulator.

Reads a saved run directory (manifest.json + tick_log.jsonl + states.csv as
written by simulator.engine.orchestrator.Orchestrator.save_run) and renders a
deterministic markdown report with matplotlib trajectory plots.

CLI:
    python3 -m simulator.reports.generate_report --run <run_dir> \
        [--compare <run_dir2>] --out <report.md> [--plots-dir <dir>] \
        [--cards <agent_cards_dir>]

Determinism: all text output uses fixed %.4f float formatting and sorted
iteration; rules-only engine runs are byte-identical across reruns. The
generation timestamp and the embedded PNG plot are excluded from any
determinism claim (PNG bytes are not reproducible).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

KEY_LABELS = [
    "microglia",
    "TNF",
    "BDNF",
    "MMP-9",
    "KCC2",
    "perineuronal",
    "parvalbumin",
    "allodynia",
]
READOUT_FIELDS = ("pain_score", "inflammation_index", "barrier_integrity")
PIN_THRESHOLD = 0.20
STATE_EPS = 1e-9
OSC_WINDOW_TICKS = 10
OSC_MIN_FLIPS = 4
TOP_EVENTS = 10
DEFAULT_CARDS_DIR = "simulator/agent_cards"
SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def _fmt_signed(v: float) -> str:
    return f"{v:+.4f}"


# --------------------------------------------------------------- run loading


@dataclass
class RunData:
    path: Path
    manifest: dict = field(default_factory=dict)
    scenario: dict = field(default_factory=dict)
    readouts_by_tick: dict[int, dict[str, float]] = field(default_factory=dict)
    states_by_tick: dict[int, dict[str, float]] = field(default_factory=dict)

    @property
    def ticks(self) -> list[int]:
        return sorted(self.states_by_tick)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_run(run_dir: str | Path) -> RunData:
    path = Path(run_dir)
    payload = json.loads((path / "manifest.json").read_text())
    manifest = payload.get("manifest", {})
    scenario = payload.get("scenario_echo", manifest.get("scenario", {}))
    readouts: dict[int, dict[str, float]] = {}
    for line in (path / "tick_log.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        world_after = entry.get("world_after", {})
        tick = world_after.get("tick", entry.get("tick", 0) + 1)
        ro = world_after.get("readouts")
        if ro is not None:
            readouts[tick] = ro
    states: dict[int, dict[str, float]] = {}
    with (path / "states.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            tick = int(row["tick"])
            states.setdefault(tick, {})[row["agent_id"]] = float(row["state"])
    return RunData(
        path=path,
        manifest=manifest,
        scenario=scenario,
        readouts_by_tick=readouts,
        states_by_tick=states,
    )


# ------------------------------------------------------------ text primitives


def sparkline(values: list[float]) -> str:
    out = []
    for v in values:
        v = min(1.0, max(0.0, v))
        idx = int(round(v * (len(SPARK_CHARS) - 1)))
        out.append(SPARK_CHARS[idx])
    return "".join(out)


def ascii_bar(value: float) -> str:
    n = int(round(min(1.0, max(0.0, value)) * 10))
    return "[" + "#" * n + "." * (10 - n) + "]"


def _window_str(start_tick: int, end_tick: int | None, horizon: int) -> str:
    return f"[{start_tick}, {end_tick})" if end_tick is not None else f"[{start_tick}, {horizon})"


def _active(tick: int, start_tick: int, end_tick: int | None) -> bool:
    return start_tick <= tick and (end_tick is None or tick < end_tick)


# ------------------------------------------------------------------ analysis


def resolve_key_cards(cards_by_id: dict[str, object]) -> list[tuple[str, object | None]]:
    """First-match each KEY_LABELS substring against card labels (id-sorted)."""
    ordered_ids = sorted(cards_by_id)
    resolved = []
    for needle in KEY_LABELS:
        hit = None
        for cid in ordered_ids:
            if needle.lower() in cards_by_id[cid].label.lower():
                hit = cards_by_id[cid]
                break
        resolved.append((needle, hit))
    return resolved


def sampled_ticks(ticks: list[int], horizon: int) -> list[int]:
    """Every max(1, horizon//12)-th tick, final tick always included."""
    if not ticks:
        return []
    step = max(1, horizon // 12)
    first = ticks[0]
    picked = [t for t in range(first + step - 1, ticks[-1] + 1, step)]
    if ticks[-1] not in picked:
        picked.append(ticks[-1])
    return picked


def emergent_events(
    run: RunData,
    cards_by_id: dict[str, object],
    top_n: int = TOP_EVENTS,
) -> list[dict]:
    ticks = run.ticks
    if not ticks:
        return []
    prev: dict[str, float] = {}
    perturbed = {
        p.get("agent_id"): float(p.get("value", 0.0))
        for p in run.scenario.get("initial_perturbations", [])
    }
    for agent_id in sorted(run.states_by_tick[ticks[0]]):
        card = cards_by_id.get(agent_id)
        if agent_id in perturbed:
            prev[agent_id] = perturbed[agent_id]
        elif card is not None:
            prev[agent_id] = float(getattr(card, "baseline_state"))
        else:
            prev[agent_id] = run.states_by_tick[ticks[0]][agent_id]
    events = []
    for tick in ticks:
        for agent_id in sorted(run.states_by_tick[tick]):
            state = run.states_by_tick[tick][agent_id]
            delta = state - prev.get(agent_id, state)
            prev[agent_id] = state
            if abs(delta) <= STATE_EPS:
                continue
            events.append(
                {"tick": tick, "agent_id": agent_id, "delta": delta}
            )
    events.sort(key=lambda e: (-abs(e["delta"]), e["tick"], e["agent_id"]))
    return events[:top_n]


def cross_community_agents(cards_by_id: dict[str, object]) -> set[str]:
    cross = set()
    for cid in sorted(cards_by_id):
        card = cards_by_id[cid]
        own = card.community
        for edge in card.inbound_edges:
            sender = cards_by_id.get(edge.source_id)
            if sender is not None and sender.community != own:
                cross.add(cid)
                break
    return cross


def _observed_window(start_tick: int, end_tick: int | None) -> tuple[int, int | None]:
    """Map a scenario pressure window to observed post-ticks.

    The engine applies drug/drive pressure during step t (pre-tick t); the
    resulting state is recorded as post-tick t+1 in states.csv, so the
    observable effect window is [start+1, end+1).
    """
    return (start_tick + 1, None if end_tick is None else end_tick + 1)


def window_effect(
    states_by_agent: dict[str, dict[int, float]],
    ticks: list[int],
    start_tick: int,
    end_tick: int | None,
) -> dict[str, tuple[float | None, float | None]]:
    """Mean state during window vs outside, per agent (None when no ticks)."""
    out: dict[str, tuple[float | None, float | None]] = {}
    for agent_id in sorted(states_by_agent):
        series = states_by_agent[agent_id]
        inside = [series[t] for t in ticks if t in series and _active(t, start_tick, end_tick)]
        outside = [series[t] for t in ticks if t in series and not _active(t, start_tick, end_tick)]
        mean_in = sum(inside) / len(inside) if inside else None
        mean_out = sum(outside) / len(outside) if outside else None
        out[agent_id] = (mean_in, mean_out)
    return out


def detect_anomalies(run: RunData, cards_by_id: dict[str, object]) -> list[str]:
    flags: list[str] = []
    ticks = run.ticks
    total = len(ticks)
    if total:
        for agent_id in sorted(run.states_by_tick[ticks[0]]):
            series = [run.states_by_tick[t].get(agent_id) for t in ticks]
            series = [s for s in series if s is not None]
            if not series:
                continue
            pinned_low = sum(1 for s in series if abs(s) <= STATE_EPS)
            pinned_high = sum(1 for s in series if abs(s - 1.0) <= STATE_EPS)
            card = cards_by_id.get(agent_id)
            who = getattr(card, "label", agent_id) if card is not None else agent_id
            for level, count in ((0.0, pinned_low), (1.0, pinned_high)):
                frac = count / total
                if frac > PIN_THRESHOLD:
                    flags.append(
                        f"- PINNED: {who} ({agent_id}) at {_fmt(level)} "
                        f"for {frac * 100:.2f}% of ticks (> {PIN_THRESHOLD:.0%})"
                    )
        for agent_id in sorted(run.states_by_tick[ticks[0]]):
            deltas = []
            prev = None
            for tick in ticks:
                cur = run.states_by_tick[tick].get(agent_id)
                if cur is None:
                    continue
                if prev is not None:
                    deltas.append((tick, cur - prev))
                prev = cur
            flips = []
            last_sign = 0
            for tick, d in deltas:
                sign = 0 if abs(d) <= STATE_EPS else (1 if d > 0 else -1)
                if sign == 0:
                    continue
                if last_sign != 0 and sign != last_sign:
                    flips.append(tick)
                last_sign = sign
            for i in range(len(flips) - OSC_MIN_FLIPS + 1):
                if flips[i + OSC_MIN_FLIPS - 1] - flips[i] <= OSC_WINDOW_TICKS:
                    card = cards_by_id.get(agent_id)
                    who = getattr(card, "label", agent_id) if card is not None else agent_id
                    flags.append(
                        f"- OSCILLATION: {who} ({agent_id}) has >= "
                        f"{OSC_MIN_FLIPS} state sign-flips within "
                        f"{OSC_WINDOW_TICKS} ticks"
                    )
                    break
    out_of_range = []
    for tick in sorted(run.readouts_by_tick):
        for name in READOUT_FIELDS:
            v = run.readouts_by_tick[tick].get(name)
            if v is None:
                continue
            if not (math.isfinite(v) and 0.0 <= v <= 1.0):
                out_of_range.append(f"- READOUT RANGE: {name}={_fmt(v)} outside [0,1] at tick {tick}")
    flags.extend(sorted(out_of_range))
    return flags


# -------------------------------------------------------------------- plots


def write_readout_plot(run: RunData, png_path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ticks = sorted(set(run.readouts_by_tick) & set(run.states_by_tick))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = {"pain_score": "#d62728", "inflammation_index": "#ff7f0e", "barrier_integrity": "#1f77b4"}
    for name in READOUT_FIELDS:
        ys = [run.readouts_by_tick[t].get(name, float("nan")) for t in ticks]
        ax.plot(ticks, ys, label=name, color=colors[name], linewidth=1.5)
    ax.set_xlabel("day (post-tick)")
    ax.set_ylabel("readout value")
    ax.set_title(f"Readout trajectories — {run.scenario.get('name', run.path.name)}")
    ax.set_xlim(min(ticks), max(ticks))
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=120)
    plt.close(fig)
    return png_path


# ------------------------------------------------------------------ rendering


def _section_overview(run: RunData, generated_at: str) -> str:
    sc = run.scenario
    lines = [
        "## 1. Run Overview",
        "",
        f"- run_dir: {run.path}",
        f"- scenario: {sc.get('name', '?')}",
        f"- injury_model: {sc.get('injury_model', '?')}",
        f"- injury_tick: {sc.get('injury_tick') if sc.get('injury_tick') is not None else 'n/a'}",
        f"- horizon_days: {sc.get('horizon_days', '?')}",
        f"- seed: {run.manifest.get('seed', '?')}",
        f"- engine_version: {run.manifest.get('engine_version', '?')}",
        f"- started_at_utc: {run.manifest.get('started_at_utc', 'n/a')}",
        f"- generated_at: {generated_at}",
    ]
    made = run.manifest.get("llm_calls_made")
    deferred = run.manifest.get("llm_calls_deferred")
    if made is not None:
        lines.append(f"- llm_calls_made: {made}")
    if deferred is not None:
        lines.append(f"- llm_calls_deferred: {deferred}")
    notes = sc.get("notes")
    if notes:
        lines.append(f"- notes: {' '.join(str(notes).split())}")
    return "\n".join(lines)


def _section_trajectories(run: RunData, embed_rel: str | None) -> str:
    horizon = int(run.scenario.get("horizon_days", 0))
    ticks = sorted(set(run.readouts_by_tick))
    lines = [
        "## 2. Readout Trajectories",
        "",
    ]
    if embed_rel:
        lines += [f"![readout trajectories]({embed_rel})", ""]
    lines += [
        "| day | pain_score | inflammation_index | barrier_integrity |",
        "|---|---|---|---|",
    ]
    for tick in sampled_ticks(ticks, horizon):
        ro = run.readouts_by_tick[tick]
        lines.append(
            f"| {tick} | " + " | ".join(_fmt(ro.get(n, float('nan'))) for n in READOUT_FIELDS) + " |"
        )
    return "\n".join(lines)


def _section_traces(run: RunData, cards_by_id: dict, resolved: list) -> str:
    ticks = run.ticks
    lines = ["## 3. Key Entity Traces", ""]
    if not ticks:
        lines.append("(no ticks)")
        return "\n".join(lines)
    shown = 0
    for needle, card in resolved:
        if card is None:
            continue
        series = [run.states_by_tick[t].get(card.id) for t in ticks]
        series_known = [s for s in series if s is not None]
        if not series_known:
            continue
        final = series_known[-1]
        baseline = float(card.baseline_state)
        lines.append(f"### {card.id} — {card.label} (key: {needle})")
        lines.append("")
        lines.append(f"state {sparkline(series_known)}")
        lines.append(
            f"final {_fmt(final)} vs baseline {_fmt(baseline)} -> delta {_fmt_signed(final - baseline)}"
        )
        lines.append("")
        shown += 1
    if not shown:
        lines.append("(none resolved)")
    return "\n".join(lines)


def _section_events(run: RunData, cards_by_id: dict) -> str:
    lines = [
        "## 4. Emergent Events",
        "",
        "Top single-tick state changes (pre-tick 0 reconstructed from card baselines"
        " and scenario initial_perturbations):",
        "",
        "| rank | day | agent | label | delta | direction | propagation |",
        "|---|---|---|---|---|---|---|",
    ]
    cross = cross_community_agents(cards_by_id)
    events = emergent_events(run, cards_by_id)
    if not events:
        lines.append("| n/a | n/a | n/a | (no changes) | n/a | n/a | |")
    for rank, ev in enumerate(events, start=1):
        card = cards_by_id.get(ev["agent_id"])
        label = getattr(card, "label", ev["agent_id"]) if card is not None else ev["agent_id"]
        direction = "up" if ev["delta"] > 0 else "down"
        note = "cross-community" if ev["agent_id"] in cross else ""
        lines.append(
            f"| {rank} | {ev['tick']} | {ev['agent_id']} | {label} | "
            f"{_fmt_signed(ev['delta'])} | {direction} | {note} |"
        )
    return "\n".join(lines)


def _effect_line(agent_id: str, stats: tuple[float | None, float | None], indent: str = "") -> str:
    mean_in, mean_out = stats
    in_s = _fmt(mean_in) if mean_in is not None else "n/a"
    out_s = _fmt(mean_out) if mean_out is not None else "n/a"
    if mean_in is not None and mean_out is not None:
        delta = f" (delta {_fmt_signed(mean_in - mean_out)})"
    else:
        delta = ""
    return f"{indent}- observed effect @ {agent_id}: mean-in {in_s} vs mean-out {out_s}{delta}"


def _section_accounting(run: RunData) -> str:
    horizon = int(run.scenario.get("horizon_days", 0))
    ticks = run.ticks
    states_by_agent: dict[str, dict[int, float]] = {}
    for tick in ticks:
        for agent_id, state in run.states_by_tick[tick].items():
            states_by_agent.setdefault(agent_id, {})[tick] = state
    lines = ["## 5. Perturbation & Drug Accounting", ""]
    perts = run.scenario.get("initial_perturbations", [])
    lines.append(f"### initial_perturbations ({len(perts)})")
    lines.append("")
    for p in sorted(perts, key=lambda p: p.get("agent_id", "")):
        lines.append(f"- {p.get('agent_id')} -> value {_fmt(float(p.get('value', 0.0)))}")
    if not perts:
        lines.append("- none")
    drives = run.scenario.get("sustained_drives", [])
    lines += ["", f"### sustained_drives ({len(drives)})"]
    for d in sorted(drives, key=lambda d: d.get("agent_id", "")):
        agent_id = d.get("agent_id")
        start = int(d.get("start_tick", 0))
        end = d.get("end_tick")
        lines.append(
            f"- {agent_id}: value {_fmt(float(d.get('value', 0.0)))}, "
            f"window {_window_str(start, end, horizon)}"
        )
        if ticks:
            stats = window_effect(
                {agent_id: states_by_agent.get(agent_id, {})},
                ticks,
                *_observed_window(start, end),
            )
            lines.append(_effect_line(agent_id, stats[agent_id]))
    if not drives:
        lines.append("- none")
    arms = run.scenario.get("drug_arms", [])
    lines += ["", f"### drug_arms ({len(arms)})"]
    for arm in sorted(arms, key=lambda a: a.get("name", "")):
        start = int(arm.get("start_tick", 0))
        end = arm.get("end_tick")
        sign = int(arm.get("effect_sign", 0))
        lines.append(
            f"- {arm.get('name')}: effect_sign {sign:+d}, magnitude "
            f"{_fmt(float(arm.get('magnitude', 0.0)))}, window "
            f"{_window_str(start, end, horizon)}"
        )
        targets = sorted(dict.fromkeys(arm.get("target_agent_ids", [])))
        if ticks and targets:
            obs_start, obs_end = _observed_window(start, end)
            stats = window_effect(
                {t: states_by_agent.get(t, {}) for t in targets}, ticks, obs_start, obs_end
            )
            for target in targets:
                lines.append(_effect_line(target, stats[target]))
    if not arms:
        lines.append("- none")
    return "\n".join(lines)


def _section_anomalies(run: RunData, cards_by_id: dict, resolved: list) -> str:
    flags = detect_anomalies(run, cards_by_id)
    unresolved = [needle for needle, card in resolved if card is None]
    lines = ["## 6. Anomaly Flags", ""]
    lines.append("Rule-based flags:")
    lines.append("")
    if flags:
        lines.extend(flags)
    else:
        lines.append("none detected")
    lines += ["", "Unresolved key-label warnings:"]
    if unresolved:
        lines.extend(
            f"- UNRESOLVED LABEL: '{needle}' matched no card" for needle in unresolved
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _section_repro(
    run: RunData,
    compare_run: RunData | None,
    command_echo: str,
) -> str:
    lines = ["## 7. Reproducibility", ""]
    for fname in ("manifest.json", "tick_log.jsonl", "states.csv"):
        f = run.path / fname
        tag = " (A)" if compare_run is not None else ""
        lines.append(f"- {fname} sha256{tag}: {_sha256(f)}")
    if compare_run is not None:
        for fname in ("manifest.json", "tick_log.jsonl", "states.csv"):
            f = compare_run.path / fname
            lines.append(f"- {fname} sha256 (B): {_sha256(f)}")
    card_hash = run.manifest.get("card_set_hash")
    if card_hash:
        lines.append(f"- card_set_hash: {card_hash} (cards manifest hash)")
    lines.append(
        "- determinism: rules-only engine runs are byte-reproducible "
        "(identical manifest.json / tick_log.jsonl / states.csv); the generation "
        "timestamp above and the embedded PNG plot are excluded from determinism "
        "claims (PNG bytes are not guaranteed reproducible)."
    )
    if command_echo:
        lines.append(f"- command: {command_echo}")
    return "\n".join(lines)


def _section_compare(run_a: RunData, run_b: RunData) -> str:
    name_a = run_a.scenario.get("name", run_a.path.name)
    name_b = run_b.scenario.get("name", run_b.path.name)
    common = sorted(set(run_a.readouts_by_tick) & set(run_b.readouts_by_tick))
    lines = [
        f"## 8. Comparison A vs B ({name_a} vs {name_b})",
        "",
        f"Common window: ticks {common[0]}..{common[-1]} ({len(common)} ticks)",
        "",
        "| readout | " f"{name_a} (A) | bar | {name_b} (B) | bar | delta (B-A) |",
        "|---|---|---|---|---|---|",
    ]
    for name in READOUT_FIELDS:
        mean_a = sum(run_a.readouts_by_tick[t][name] for t in common) / len(common)
        mean_b = sum(run_b.readouts_by_tick[t][name] for t in common) / len(common)
        lines.append(
            f"| {name} | {_fmt(mean_a)} | {ascii_bar(mean_a)} | "
            f"{_fmt(mean_b)} | {ascii_bar(mean_b)} | {_fmt_signed(mean_b - mean_a)} |"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------- entry


def generate_report(
    run_dir: str | Path,
    out_path: str | Path,
    cards_dir: str | Path | None = None,
    compare_dir: str | Path | None = None,
    plots_dir: str | Path | None = None,
    command_echo: str = "",
) -> str:
    from simulator.engine.orchestrator import load_cards

    run = load_run(run_dir)
    compare_run = load_run(compare_dir) if compare_dir is not None else None
    if cards_dir is None:
        cards_dir = DEFAULT_CARDS_DIR
    cards_by_id = {c.id: c for c in load_cards(cards_dir)}
    resolved = resolve_key_cards(cards_by_id)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    plots_root = Path(plots_dir) if plots_dir is not None else out.parent / "plots"
    png_path = plots_root / f"{run.path.name}_readouts.png"
    write_readout_plot(run, png_path)
    embed_rel = os.path.relpath(png_path, out.parent).replace(os.sep, "/")

    generated_at = _utc_now()
    sections = [
        "# CP Simulator Experiment Report",
        "",
        _section_overview(run, generated_at),
        _section_trajectories(run, embed_rel),
        _section_traces(run, cards_by_id, resolved),
        _section_events(run, cards_by_id),
        _section_accounting(run),
        _section_anomalies(run, cards_by_id, resolved),
        _section_repro(run, compare_run, command_echo),
    ]
    if compare_run is not None:
        sections.append(_section_compare(run, compare_run))
    text = "\n\n".join(sections) + "\n"
    out.write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate experiment report from a run directory")
    parser.add_argument("--run", required=True, help="run directory (save_run output)")
    parser.add_argument("--compare", default=None, help="second run directory for A-vs-B comparison")
    parser.add_argument("--out", required=True, help="output markdown report path")
    parser.add_argument("--plots-dir", default=None, help="directory for PNG figures (default: <out dir>/plots)")
    parser.add_argument("--cards", default=DEFAULT_CARDS_DIR, help="agent cards directory")
    args = parser.parse_args(argv)
    echo = "python3 -m simulator.reports.generate_report " + " ".join(argv if argv is not None else sys.argv[1:])
    generate_report(
        run_dir=args.run,
        out_path=args.out,
        cards_dir=args.cards,
        compare_dir=args.compare,
        plots_dir=args.plots_dir,
        command_echo=echo.strip(),
    )
    print(f"report written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
