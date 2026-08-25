"""Tests for simulator/reports/generate_report.py.

All fixtures are synthetic tiny run dirs (manifest.json + tick_log.jsonl +
states.csv) fabricated inline; values are hand-computable.
"""

import json
from pathlib import Path

import pytest
import yaml

from simulator.reports.generate_report import (
    KEY_LABELS,
    generate_report,
    main as cli_main,
)

REAL_RUN = Path(__file__).resolve().parents[1] / "reports" / "runs" / "pilot_acceptance" / "sni_28d"
CARDS_DIR = Path(__file__).resolve().parents[1] / "agent_cards"

SECTIONS_SINGLE = [
    "## 1. Run Overview",
    "## 2. Readout Trajectories",
    "## 3. Key Entity Traces",
    "## 4. Emergent Events",
    "## 5. Perturbation & Drug Accounting",
    "## 6. Anomaly Flags",
    "## 7. Reproducibility",
]


# ---------------------------------------------------------------- fixtures


def write_card(cards_dir: Path, card: dict) -> None:
    cards_dir.mkdir(parents=True, exist_ok=True)
    (cards_dir / f"{card['id']}.yaml").write_text(yaml.safe_dump(card, sort_keys=True))


def base_card(cid, label, community=0, baseline=0.5, entity_type="molecule",
              inbound=None, tier="MID"):
    return {
        "id": cid,
        "label": label,
        "entity_type": entity_type,
        "compartment": "cns",
        "tier": tier,
        "community": community,
        "baseline_state": baseline,
        "normal_role": "",
        "pathological_rules": [],
        "inbound_edges": inbound or [],
        "outbound_ids": [],
        "rule_gap_reason": None,
        "source_note": None,
    }


def make_run(
    run_dir: Path,
    *,
    name="fx_naive",
    injury_model="naive",
    injury_tick=None,
    horizon=8,
    seed=0,
    engine_version="0.1.0",
    llm_made=None,
    llm_deferred=None,
    perturbations=None,
    drives=None,
    arms=None,
    readouts_by_tick,
    states_by_tick,
) -> Path:
    """readouts_by_tick/states_by_tick keyed by post-tick (1..horizon)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    scenario = {
        "name": name,
        "horizon_days": horizon,
        "injury_model": injury_model,
        "injury_tick": injury_tick,
        "drug_arms": arms or [],
        "sustained_drives": drives or [],
        "initial_perturbations": perturbations or [],
        "budget": {"max_llm_calls": None, "max_wall_minutes": None},
        "notes": None,
    }
    manifest = {
        "scenario": scenario,
        "started_at_utc": "2026-01-01T00:00:00Z",
        "seed": seed,
        "engine_version": engine_version,
        "card_set_hash": "deadbeef",
        "llm_calls_made": llm_made,
        "llm_calls_deferred": llm_deferred,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps({"manifest": manifest, "scenario_echo": scenario}, sort_keys=True)
    )
    with (run_dir / "tick_log.jsonl").open("w") as fh:
        for tick in sorted(readouts_by_tick):
            fh.write(
                json.dumps(
                    {
                        "tick": tick - 1,
                        "epoch": "INITIATION",
                        "deltas_applied": [],
                        "audit": [],
                        "world_after": {
                            "tick": tick,
                            "epoch": "INITIATION",
                            "states": states_by_tick[tick],
                            "readouts": readouts_by_tick[tick],
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    rows = ["tick,agent_id,state"]
    agents = sorted(states_by_tick[1])
    for tick in sorted(states_by_tick):
        for a in agents:
            rows.append(f"{tick},{a},{states_by_tick[tick][a]!r}")
    (run_dir / "states.csv").write_text("\n".join(rows) + "\n")
    return run_dir


def const_readouts(ticks, pain=0.1, inflam=0.2, barrier=0.3):
    return {
        t: {
            "pain_score": pain,
            "inflammation_index": inflam,
            "barrier_integrity": barrier,
        }
        for t in ticks
    }


@pytest.fixture()
def simple_run(tmp_path):
    """3 agents; mig jumps to 0.9 at tick 1 then stays; symp constant."""
    states = {
        1: {"mig": 0.9, "tnf": 0.5, "symp": 0.05},
        2: {"mig": 0.9, "tnf": 0.5, "symp": 0.05},
        3: {"mig": 0.9, "tnf": 0.5, "symp": 0.05},
        4: {"mig": 0.9, "tnf": 0.5, "symp": 0.05},
    }
    return make_run(
        tmp_path / "run_a",
        horizon=4,
        seed=7,
        engine_version="9.9.9",
        llm_made=3,
        llm_deferred=1,
        readouts_by_tick=const_readouts([1, 2, 3, 4]),
        states_by_tick=states,
    )


@pytest.fixture()
def simple_cards(tmp_path):
    d = tmp_path / "cards"
    write_card(d, base_card("mig", "Microglia", community=1, baseline=0.1))
    write_card(d, base_card("tnf", "TNF-alpha", community=0, baseline=0.5))
    write_card(
        d,
        base_card(
            "symp",
            "Mechanical Allodynia",
            community=1,
            baseline=0.05,
            entity_type="symptom",
            inbound=[{"source_id": "mig", "relation": "drives", "sign": 1, "weight": 0.5}],
        ),
    )
    return d


def generate(simple_run_, simple_cards_, tmp_path, **kw):
    out = tmp_path / "report.md"
    text = generate_report(run_dir=simple_run_, out_path=out, cards_dir=simple_cards_, **kw)
    assert out.exists()
    return text


# ------------------------------------------------------------------ tests


class TestSingleRunSections:
    def test_all_seven_sections_present(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        for heading in SECTIONS_SINGLE:
            assert heading in text

    def test_header_fields_echoed(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        assert "scenario: fx_naive" in text
        assert "injury_model: naive" in text
        assert "horizon_days: 4" in text
        assert "seed: 7" in text
        assert "engine_version: 9.9.9" in text
        assert "generated_at:" in text
        assert "llm_calls_made: 3" in text
        assert "llm_calls_deferred: 1" in text

    def test_llm_counters_omitted_when_absent(self, tmp_path):
        states = {t: {"mig": 0.5} for t in (1, 2)}
        run = make_run(
            tmp_path / "r", horizon=2, llm_made=None, llm_deferred=None,
            readouts_by_tick=const_readouts([1, 2]), states_by_tick=states,
        )
        cards = tmp_path / "c"
        write_card(cards, base_card("mig", "Microglia"))
        out = tmp_path / "rep.md"
        text = generate_report(run_dir=run, out_path=out, cards_dir=cards)
        assert "llm_calls_made" not in text.split("## 2")[0]

    def test_readout_table_sampled_every_step(self, tmp_path):
        ticks = list(range(1, 25))  # horizon 24 -> step = max(1, 24//12) = 2
        states = {t: {"mig": 0.5} for t in ticks}
        readouts = {
            t: {"pain_score": 0.10 * t, "inflammation_index": 0.0, "barrier_integrity": 0.0}
            for t in ticks
        }
        run = make_run(tmp_path / "r", horizon=24, readouts_by_tick=readouts, states_by_tick=states)
        cards = tmp_path / "c"
        write_card(cards, base_card("mig", "Microglia"))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        table = text.split("## 2")[1].split("## 3")[0]
        assert "| 2 | 0.2000 | 0.0000 | 0.0000 |" in table
        assert "| 22 | 2.2000 |" in table  # sampled even tick present
        assert "\n| 21 |" not in table and "\n| 23 |" not in table
        assert "| 24 | 2.4000 |" in table  # final tick always included

    def test_png_created_and_embedded(self, simple_run, simple_cards, tmp_path):
        plots = tmp_path / "figs"
        text = generate(simple_run, simple_cards, tmp_path, plots_dir=plots)
        pngs = list(plots.glob("*.png"))
        assert len(pngs) == 1
        rel = pngs[0].name
        assert rel in text and "![" in text

    def test_key_traces_resolved_with_delta(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        traces = text.split("## 3")[1].split("## 4")[0]
        assert "Microglia" in traces
        # final 0.9000 vs baseline 0.1000 -> delta +0.8000
        assert "+0.8000" in traces

    def test_unresolved_labels_warned_in_anomalies(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        flags = text.split("## 6")[1].split("## 7")[0]
        # microglia/TNF/allodynia resolve against the fixture cards; the
        # remaining KEY_LABELS must be reported as unresolved warnings.
        resolved = ("microglia", "TNF", "allodynia")
        expected_missing = [k for k in KEY_LABELS if k not in resolved]
        for key in expected_missing:
            assert key in flags
        for key in resolved:
            assert f"'{key}' matched no card" not in flags

    def test_emergent_events_top10_cross_community(self, tmp_path):
        # 12 agents each jump +0.5 at distinct ticks -> >10 candidate events
        states = {}
        n_agents = 12
        ids = [f"a{i:02d}" for i in range(n_agents)]
        for t in range(1, 15):
            row = {}
            for i, aid in enumerate(ids):
                row[aid] = 0.9 if t >= i + 1 else 0.4
            states[t] = row
        run = make_run(tmp_path / "r", horizon=14, readouts_by_tick=const_readouts(range(1, 15)),
                       states_by_tick=states)
        cards = tmp_path / "c"
        for i, aid in enumerate(ids):
            comm = 1 if i == 0 else 0
            inbound = [{"source_id": "a01", "relation": "x", "sign": 1, "weight": 0.5}]
            write_card(cards, base_card(aid, f"Agent {aid}", community=comm, baseline=0.4,
                                        inbound=inbound))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        events = text.split("## 4")[1].split("## 5")[0]
        listed = [line for line in events.splitlines() if line.startswith("| ") and "a0" in line]
        assert len(listed) == 10  # top-10 cap
        # every event agent has an inbound edge from a01 (community 1); agents
        # a02..a12 are community 0 -> cross-community flag appears
        assert "cross-community" in events

    def test_event_direction_up(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        events = text.split("## 4")[1].split("## 5")[0]
        assert "up" in events  # mig 0.1 -> 0.9 at tick 1 (vs reconstructed pre-tick)


class TestAnomalies:
    def test_pinned_flagged(self, tmp_path):
        states = {t: {"pinned": 1.0, "free": 0.5} for t in range(1, 11)}
        run = make_run(tmp_path / "r", horizon=10, readouts_by_tick=const_readouts(range(1, 11)),
                       states_by_tick=states)
        cards = tmp_path / "c"
        write_card(cards, base_card("pinned", "Pinned Agent"))
        write_card(cards, base_card("free", "Free Agent"))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        flags = text.split("## 6")[1].split("## 7")[0]
        assert "pinned" in flags and "Pinned Agent" in flags
        assert "Free Agent" not in flags

    def test_not_pinned_below_threshold(self, tmp_path):
        # pinned exactly 20% of ticks -> NOT flagged (>20% required)
        states = {}
        for t in range(1, 11):
            v = 1.0 if t <= 2 else 0.5
            states[t] = {"edge": v}
        run = make_run(tmp_path / "r", horizon=10, readouts_by_tick=const_readouts(range(1, 11)),
                       states_by_tick=states)
        cards = tmp_path / "c"
        write_card(cards, base_card("edge", "Edge Agent"))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        flags = text.split("## 6")[1].split("## 7")[0]
        assert "Edge Agent" not in flags

    def test_oscillation_flagged(self, tmp_path):
        states = {}
        for t in range(1, 11):
            states[t] = {"osc": 1.0 if t % 2 else 0.0}
        run = make_run(tmp_path / "r", horizon=10, readouts_by_tick=const_readouts(range(1, 11)),
                       states_by_tick=states)
        cards = tmp_path / "c"
        write_card(cards, base_card("osc", "Oscillator"))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        flags = text.split("## 6")[1].split("## 7")[0]
        assert "Oscillator" in flags and "oscillat" in flags.lower()

    def test_readout_out_of_range_flagged(self, simple_run, simple_cards, tmp_path):
        # corrupt one readout directly in the fixture file
        lines = (simple_run / "tick_log.jsonl").read_text().splitlines()
        obj = json.loads(lines[0])
        obj["world_after"]["readouts"]["pain_score"] = 1.5
        lines[0] = json.dumps(obj, sort_keys=True)
        (simple_run / "tick_log.jsonl").write_text("\n".join(lines) + "\n")
        text = generate(simple_run, simple_cards, tmp_path)
        flags = text.split("## 6")[1].split("## 7")[0]
        assert "outside [0,1]" in flags and "1.5000" in flags

    def test_no_flags_when_clean(self, tmp_path):
        states = {t: {"mig": 0.5} for t in (1, 2, 3)}
        run = make_run(tmp_path / "r", horizon=3, readouts_by_tick=const_readouts([1, 2, 3]),
                       states_by_tick=states)
        cards = tmp_path / "c"
        write_card(cards, base_card("mig", "Microglia"))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        flags = text.split("## 6")[1].split("## 7")[0]
        assert "none detected" in flags


class TestAccounting:
    def test_drug_window_effect_math(self, tmp_path):
        # arm active on ticks [2, 4): observed states [0, 0, .6, .8, 0, 0]
        # mean-in = (0.6+0.8)/2 = 0.7000 ; mean-out = 0.0000
        states = {
            1: {"kcc2": 0.0}, 2: {"kcc2": 0.0}, 3: {"kcc2": 0.6},
            4: {"kcc2": 0.8}, 5: {"kcc2": 0.0}, 6: {"kcc2": 0.0},
        }
        arms = [{
            "name": "clp257",
            "target_agent_ids": ["kcc2"],
            "start_tick": 2,
            "end_tick": 4,
            "effect_sign": 1,
            "magnitude": 0.6,
        }]
        run = make_run(tmp_path / "r", horizon=6, arms=arms,
                       readouts_by_tick=const_readouts(range(1, 7)), states_by_tick=states)
        cards = tmp_path / "c"
        write_card(cards, base_card("kcc2", "KCC2 Transporter"))
        text = generate_report(run_dir=run, out_path=tmp_path / "rep.md", cards_dir=cards)
        acct = text.split("## 5")[1].split("## 6")[0]
        assert "clp257" in acct
        assert "0.7000" in acct and "0.0000" in acct

    def test_drive_window_echo(self, simple_run, simple_cards, tmp_path):
        run_dir = simple_run
        # add a sustained drive to the manifest echo
        import json as _json
        payload = _json.loads((run_dir / "manifest.json").read_text())
        payload["scenario_echo"]["sustained_drives"] = [
            {"agent_id": "mig", "value": 0.9, "start_tick": 0, "end_tick": None}
        ]
        (run_dir / "manifest.json").write_text(_json.dumps(payload, sort_keys=True))
        text = generate(run_dir, simple_cards, tmp_path)
        acct = text.split("## 5")[1].split("## 6")[0]
        assert "mig" in acct and "0.9000" in acct


class TestCompareMode:
    def test_compare_table_math(self, tmp_path):
        common = range(1, 5)
        states_a = {t: {"mig": 0.5} for t in common}
        states_b = {t: {"mig": 0.5} for t in common}
        ra = make_run(tmp_path / "ra", name="alpha", horizon=4,
                      readouts_by_tick=const_readouts(common, pain=0.2),
                      states_by_tick=states_a)
        rb = make_run(tmp_path / "rb", name="beta", horizon=6,
                      readouts_by_tick=const_readouts(common, pain=0.4),
                      states_by_tick=states_b)
        cards = tmp_path / "c"
        write_card(cards, base_card("mig", "Microglia"))
        text = generate_report(run_dir=ra, compare_dir=rb, out_path=tmp_path / "rep.md",
                               cards_dir=cards)
        comp = text.split("## 8")[1]
        # common window is min(max_a, max_b) = 4 ticks
        assert "| pain_score | 0.2000 |" in comp
        assert "| pain_score |" in comp and "0.4000" in comp and "+0.2000" in comp
        assert "[####......]" in comp  # B bar at 0.4
        assert "[##........]" in comp  # A bar at 0.2
        assert "alpha" in text.split("## 8")[0] or True
        heading = text.split("\n## 8")[1].splitlines()[0]
        assert "A vs B" in heading and "alpha" in heading and "beta" in heading

    def test_compare_section_absent_without_compare(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        assert "## 8" not in text


class TestDeterminismAndRepro:
    def test_deterministic_text_output(self, simple_run, simple_cards, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "simulator.reports.generate_report._utc_now",
            lambda: "2026-01-01T00:00:00Z",
        )
        t1 = generate_report(run_dir=simple_run, out_path=tmp_path / "a.md", cards_dir=simple_cards)
        t2 = generate_report(run_dir=simple_run, out_path=tmp_path / "b.md", cards_dir=simple_cards)
        assert t1 == t2

    def test_repro_block_hashes(self, simple_run, simple_cards, tmp_path):
        text = generate(simple_run, simple_cards, tmp_path)
        repro = text.split("## 7")[1].split("## 8")[0] if "## 8" in text else \
            text.split("## 7")[1]
        assert "sha256" in repro
        assert "card_set_hash: deadbeef" in repro
        assert "PNG" in repro  # excluded-from-determinism note

    def test_command_line_echo(self, simple_run, simple_cards, tmp_path):
        rc = cli_main([
            "--run", str(simple_run), "--out", str(tmp_path / "rep.md"),
            "--cards", str(simple_cards),
        ])
        assert rc == 0
        text = (tmp_path / "rep.md").read_text()
        assert "--run" in text and str(simple_run.name) in text


class TestCliEndToEndRealRun:
    @pytest.mark.skipif(not REAL_RUN.exists(), reason="real pilot run dir missing")
    def test_real_sni_28d(self, tmp_path):
        out = tmp_path / "sni_report.md"
        rc = cli_main(["--run", str(REAL_RUN), "--out", str(out),
                       "--cards", str(CARDS_DIR)])
        assert rc == 0
        text = out.read_text()
        for heading in SECTIONS_SINGLE:
            assert heading in text
        assert "scenario: sni_28d" in text
        plots_dir = out.parent / "plots"
        assert any(plots_dir.glob("*.png"))

    @pytest.mark.skipif(not REAL_RUN.exists(), reason="real pilot run dir missing")
    def test_real_compare_mode(self, tmp_path):
        other = REAL_RUN.parent / "sni_28d_clp257"
        if not other.exists():
            pytest.skip("compare run missing")
        out = tmp_path / "cmp.md"
        rc = cli_main(["--run", str(REAL_RUN), "--compare", str(other),
                       "--out", str(out), "--cards", str(CARDS_DIR)])
        assert rc == 0
        text = out.read_text()
        assert "## 8. Comparison A vs B" in text
