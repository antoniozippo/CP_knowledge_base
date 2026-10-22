# crawler/tests/test_run.py - run.py wiring: inputs to extraction, full pipeline with stubbed IO

import json
import shutil
from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from crawler import run
from crawler.extractor import LLMExtractor
from crawler.fetcher import PaperContent
from crawler.search import PaperMeta

REPO = Path(__file__).resolve().parents[2]
PMID = "99999902"
LLM_OUTPUT = {
    "entities": [
        {"name": "KCC2", "entity_type": "channel", "compartment": "dorsal_horn"},
        {"name": "BDNF Val66Met Polymorphism", "entity_type": "concept"},
        {"name": "Zorblax-9", "entity_type": "molecule", "compartment": "DRG"},
    ],
    "relationships": [
        {
            "subject": "BDNF Val66Met Polymorphism",
            "predicate": "downregulates",
            "object": "KCC2",
            "sign": -1,
            "evidence_quote": "Val66Met carriers showed reduced KCC2.",
            "confidence": "HIGH",
        }
    ],
    "key_findings": [],
    "novel_terms": [],
}


def _meta(pmid=PMID, title="KCC2 in Val66Met carriers", abstract="meta abstract"):
    return PaperMeta(
        pmid=pmid, doi="10.1/x", title=title, authors=[], journal="J",
        publication_date="2026-01", mesh_terms=["Neuralgia"], abstract=abstract,
    )


def _content(pmid=PMID, abstract="KCC2 is reduced in BDNF Val66Met carriers.", sections=None):
    return PaperContent(
        pmid=pmid, pmcid=None, abstract_text=abstract, fulltext_xml=None,
        fulltext_sections=sections, is_fulltext=bool(sections),
    )


# --- build_extraction_inputs ------------------------------------------------

def test_inputs_carry_title_from_meta_and_abstract_as_content():
    inputs = run.build_extraction_inputs([_meta()], [_content()])
    assert inputs == [
        {
            "pmid": PMID,
            "title": "KCC2 in Val66Met carriers",
            "content": "KCC2 is reduced in BDNF Val66Met carriers.",
        }
    ]


def test_inputs_include_fulltext_sections_after_abstract():
    sections = {"Results": "KCC2 fell by 40%.", "Methods": "SNI surgery."}
    (item,) = run.build_extraction_inputs([_meta()], [_content(sections=sections)])
    assert item["content"].startswith("KCC2 is reduced")
    assert "KCC2 fell by 40%." in item["content"]
    assert "SNI surgery." in item["content"]


def test_inputs_fall_back_to_meta_abstract_when_fetch_returned_none():
    (item,) = run.build_extraction_inputs([_meta(abstract="from pubmed")], [_content(abstract="")])
    assert item["content"] == "from pubmed"


def test_inputs_skip_content_without_matching_meta():
    assert run.build_extraction_inputs([_meta(pmid="1")], [_content(pmid="2")]) == []


# --- full pipeline with stubbed search / fetch / LLM -------------------------

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "graphify-out").mkdir()
    shutil.copy(REPO / "graphify-out/graph_v2.json", tmp_path / "graphify-out/graph_v2.json")
    (tmp_path / "crawler/logs").mkdir(parents=True)
    themes = {"T01": {"name": "kcc2_test", "keywords": ["KCC2"], "mesh_terms": [], "entities": ["KCC2"]}}
    (tmp_path / "crawler/themes.yaml").write_text(yaml.safe_dump(themes))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("crawler.search.PROCESSED_PMIDS_PATH", tmp_path / "crawler/processed_pmids.json")
    monkeypatch.setattr("crawler.extractor.time.sleep", lambda s: None)
    return tmp_path, themes


@pytest.fixture
def llm_calls(monkeypatch):
    calls = []

    def fake_call(self, prompt):
        calls.append(prompt)
        return dict(LLM_OUTPUT)

    monkeypatch.setattr(LLMExtractor, "_call_llm", fake_call)
    return calls


def _args(**overrides):
    base = dict(
        themes_path="crawler/themes.yaml", since="2026-01-01", max_results=10, budget=50,
        llm_endpoint="http://stub", llm_model="stub", llm_max_tokens=256,
        min_mesh_freq=3, dry_run=False, no_commit=True,
    )
    base.update(overrides)
    return Namespace(**base)


def _stub_io(monkeypatch, metas, contents):
    monkeypatch.setattr(run, "search_theme", lambda cfg, since=None, max_results=0: metas)
    monkeypatch.setattr(run, "fetch_papers", lambda papers, cache_dir=None: contents)


def test_pipeline_writes_new_node_and_edge_and_marks_pmid_processed(workspace, llm_calls, monkeypatch):
    tmp, themes = workspace
    _stub_io(monkeypatch, [_meta()], [_content()])

    assert run.run_pipeline(_args(), themes=themes) == 0

    graph = json.loads((tmp / "graphify-out/graph_v2.json").read_text())
    assert [n["label"] for n in graph["nodes"] if n.get("contributor") == "auto_crawler"] == ["Zorblax-9"]
    (edge,) = [link for link in graph["links"] if link.get("origin") == "auto_crawled"]
    assert edge["source_pmid"] == PMID and edge["sign"] == -1
    assert json.loads((tmp / "crawler/processed_pmids.json").read_text()) == [PMID]


def test_prompt_contains_paper_title_and_text(workspace, llm_calls, monkeypatch):
    _, themes = workspace
    _stub_io(monkeypatch, [_meta()], [_content()])
    run.run_pipeline(_args(), themes=themes)
    assert len(llm_calls) == 1
    assert "KCC2 in Val66Met carriers" in llm_calls[0]
    assert "KCC2 is reduced in BDNF Val66Met carriers." in llm_calls[0]


def test_paper_without_theme_entity_is_not_sent_to_llm(workspace, llm_calls, monkeypatch):
    _, themes = workspace
    _stub_io(monkeypatch, [_meta()], [_content(abstract="Nothing relevant here.")])
    run.run_pipeline(_args(), themes=themes)
    assert llm_calls == []


def test_dry_run_never_calls_llm_or_changes_graph(workspace, llm_calls, monkeypatch):
    tmp, themes = workspace
    before = (tmp / "graphify-out/graph_v2.json").read_text()
    _stub_io(monkeypatch, [_meta()], [_content()])
    assert run.run_pipeline(_args(dry_run=True), themes=themes) == 0
    assert llm_calls == []
    assert (tmp / "graphify-out/graph_v2.json").read_text() == before


def test_pipeline_records_contradiction_of_confirmed_edge_for_human_review(workspace, llm_calls, monkeypatch):
    from crawler.matcher import EntityMatcher

    tmp, themes = workspace
    graph_path = tmp / "graphify-out/graph_v2.json"
    matcher = EntityMatcher(graph_path=str(graph_path))
    val66 = matcher.match_entity("BDNF Val66Met Polymorphism").matched_node_id
    kcc2 = matcher.match_entity("KCC2").matched_node_id
    graph = json.loads(graph_path.read_text())
    seeded = {"source": val66, "target": kcc2, "relation": "upregulates", "sign": 1,
              "confidence_score": 0.8, "validation_status": "CONFIRMED"}
    graph["links"].append(seeded)
    graph_path.write_text(json.dumps(graph))
    _stub_io(monkeypatch, [_meta()], [_content()])  # LLM says Val66Met downregulates KCC2 (sign -1)

    assert run.run_pipeline(_args(), themes=themes) == 0

    saved = json.loads(graph_path.read_text())
    assert [link for link in saved["links"] if link.get("origin") == "auto_crawled"] == []
    assert saved["links"][-1] == seeded
    conflicts = yaml.safe_load((tmp / "crawler/conflicts.yaml").read_text())["conflicts"]
    assert [(c["new_pmid"], c["recommendation"], c["resolved"]) for c in conflicts] == [(PMID, "HUMAN_REVIEW", False)]
    run_log = json.loads(next((tmp / "crawler/logs").glob("run_*.json")).read_text())
    assert run_log["conflicts"]["human_review"] == 1


# --- robustness: run-wide budget, PMID bookkeeping, test gate -----------------

THEMES_TWO = {
    "T01": {"name": "a", "keywords": ["x"], "mesh_terms": [], "entities": ["KCC2"]},
    "T02": {"name": "b", "keywords": ["y"], "mesh_terms": [], "entities": ["BDNF"]},
}


def test_llm_budget_is_shared_across_themes(workspace, llm_calls, monkeypatch):
    _, _ = workspace
    metas = [_meta(pmid="1", title="t1"), _meta(pmid="2", title="t2")]
    contents = [_content(pmid="1", abstract="KCC2 paper."), _content(pmid="2", abstract="BDNF paper.")]
    _stub_io(monkeypatch, metas, contents)

    run.run_pipeline(_args(budget=1), themes=THEMES_TWO)

    assert len(llm_calls) == 1


def test_budget_is_not_spent_twice_on_a_paper_matching_two_themes(workspace, llm_calls, monkeypatch):
    _, _ = workspace
    _stub_io(monkeypatch, [_meta(pmid="1")], [_content(pmid="1", abstract="KCC2 and BDNF paper.")])

    run.run_pipeline(_args(budget=5), themes=THEMES_TWO)

    assert len(llm_calls) == 1


def test_pmid_is_not_marked_processed_when_the_graph_save_fails(workspace, llm_calls, monkeypatch):
    tmp, themes = workspace
    _stub_io(monkeypatch, [_meta()], [_content()])

    def boom(self):
        raise OSError("disk full")

    monkeypatch.setattr("crawler.run.GraphUpdater.save", boom)
    with pytest.raises(OSError):
        run.run_pipeline(_args(), themes=themes)

    assert not (tmp / "crawler/processed_pmids.json").exists()


def test_test_gate_covers_crawler_analysis_and_simulator_suites(monkeypatch):
    seen = {}

    class Done:
        returncode, stdout, stderr = 0, "", ""

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return Done()

    monkeypatch.setattr(run.subprocess, "run", fake_run)
    ok, _ = run.run_test_gate()

    assert ok is True
    for suite in ("crawler/tests", "analysis/tests", "simulator/tests"):
        assert suite in seen["cmd"]


def test_failing_gate_aborts_before_any_git_command(workspace, llm_calls, monkeypatch):
    _, themes = workspace
    _stub_io(monkeypatch, [_meta()], [_content()])
    git_calls = []
    monkeypatch.setattr(run, "run_test_gate", lambda: (False, "1 failed"))
    monkeypatch.setattr(run.subprocess, "run", lambda cmd, **kw: git_calls.append(cmd))

    assert run.run_pipeline(_args(no_commit=False), themes=themes) == 1
    assert git_calls == []
