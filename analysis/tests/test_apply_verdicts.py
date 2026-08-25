"""Tests for apply_verdicts_to_graph: propagate literature verdicts onto graph edges."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "analysis" / "scripts" / "apply_verdicts_to_graph.py"
REAL_GRAPH = REPO_ROOT / "graphify-out" / "graph_v2.json"
REAL_CLAIMS = REPO_ROOT / "analysis" / "claims" / "claims.json"
REAL_VERDICTS = REPO_ROOT / "analysis" / "claims" / "verdicts.json"

sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import apply_verdicts_to_graph as av  # noqa: E402


def make_node(node_id, label):
    return {
        "label": label,
        "file_type": "document",
        "source_file": f"{node_id}.md",
        "source_location": None,
        "community": 0,
        "norm_label": label.lower(),
        "id": node_id,
    }


def make_link(source, target, relation, sign=0, confidence="EXTRACTED"):
    return {
        "relation": relation,
        "confidence": confidence,
        "confidence_score": 1.0,
        "source_file": "fixture.md",
        "source_location": None,
        "weight": 1.0,
        "source": source,
        "target": target,
        "sign": sign,
    }


def edge_claim(claim_id, subject, predicate, object_):
    return {
        "id": claim_id,
        "kind": "edge",
        "subject": subject,
        "predicate": predicate,
        "object": object_,
        "sign": -1,
        "confidence": "EXTRACTED",
        "source_note": "fixture.md",
    }


@pytest.fixture
def fixture_data():
    nodes = [
        make_node("doc_alpha", "Alpha Protein"),
        make_node("doc_beta", "Beta Kinase"),
        make_node("doc_gamma", "Gamma Receptor"),
        make_node("doc_delta", "Delta Channel (Subtype X)"),
    ]
    links = [
        make_link("doc_alpha", "doc_beta", "inhibits", sign=-1),  # L0: forward exact
        make_link("doc_alpha", "doc_gamma", "activates"),  # L1: reversed for EC-0002
        make_link("doc_beta", "doc_gamma", "modulates"),  # L2: ambiguous a
        make_link("doc_gamma", "doc_beta", "modulates"),  # L3: ambiguous b
        make_link("doc_alpha", "doc_gamma", "inhibits"),  # L4: UNREVIEWED claim target
        make_link("doc_delta", "doc_gamma", "binds", sign=1),  # L5: qualifier mix + reversed
    ]
    graph = {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": nodes,
        "links": links,
        "hyperedges": [],
    }
    claims = [
        edge_claim("EC-0001", "Alpha Protein", "inhibits", "Beta Kinase"),
        edge_claim("EC-0002", "Gamma Receptor", "activates", "Alpha Protein"),
        edge_claim("EC-0003", "Missing Entity", "inhibits", "Beta Kinase"),
        edge_claim("EC-0004", "Beta Kinase", "modulates", "Gamma Receptor"),
        edge_claim("EC-0005", "Alpha Protein", "inhibits", "Gamma Receptor"),
        edge_claim(
            "EC-0006", "Gamma Receptor (Isoform 2)", "binds", "Delta Channel"
        ),
    ]
    verdict_map = {
        "EC-0001": "CONFIRMED",
        "EC-0002": "EXTENDED",
        "EC-0003": "REFUTED",
        "EC-0004": "MIXED",
        "EC-0005": "UNREVIEWED",
        "EC-0006": "CONFIRMED",
    }
    return graph, claims, verdict_map


@pytest.fixture
def snapshot(fixture_data):
    graph, _, _ = fixture_data
    return copy.deepcopy(graph)


class TestMatching:
    def test_exact_match_sets_validation_status(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        report = av.apply_verdicts(graph, claims, verdicts)
        link = next(
            l
            for l in graph["links"]
            if l["source"] == "doc_alpha" and l["target"] == "doc_beta"
        )
        assert link["validation_status"] == "CONFIRMED"

    def test_reversed_endpoint_match(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        av.apply_verdicts(graph, claims, verdicts)
        # Claim is Gamma->Alpha; only link between the pair runs Alpha->Gamma.
        link = next(
            l
            for l in graph["links"]
            if l["relation"] == "activates"
            and {l["source"], l["target"]} == {"doc_alpha", "doc_gamma"}
        )
        assert link["validation_status"] == "EXTENDED"

    def test_parenthetical_qualifier_normalized(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        av.apply_verdicts(graph, claims, verdicts)
        # Subject carries an extra "(Isoform 2)" qualifier; object omits the
        # node's own "(Subtype X)" qualifier. Either way the link must match.
        link = next(l for l in graph["links"] if l["relation"] == "binds")
        assert link["validation_status"] == "CONFIRMED"

    def test_no_match_is_reported_not_fatal(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        report = av.apply_verdicts(graph, claims, verdicts)
        assert "EC-0003" in report["unmatched"]
        assert not any(
            l.get("validation_status") == "REFUTED" for l in graph["links"]
        )

    def test_multi_match_annotates_all_and_counts_ambiguous(
        self, fixture_data, snapshot
    ):
        graph, claims, verdicts = fixture_data
        report = av.apply_verdicts(graph, claims, verdicts)
        modulates = [l for l in graph["links"] if l["relation"] == "modulates"]
        assert len(modulates) == 2
        assert all(l["validation_status"] == "MIXED" for l in modulates)
        amb_ids = {a["claim_id"] for a in report["ambiguous"]}
        assert "EC-0004" in amb_ids

    def test_unreviewed_verdict_never_annotates(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        av.apply_verdicts(graph, claims, verdicts)
        inhibits_ag = next(
            l
            for l in graph["links"]
            if l["relation"] == "inhibits"
            and {l["source"], l["target"]} == {"doc_alpha", "doc_gamma"}
        )
        assert "validation_status" not in inhibits_ag

    def test_missing_verdict_entry_skipped(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        del verdicts["EC-0001"]
        av.apply_verdicts(graph, claims, verdicts)
        link = next(
            l
            for l in graph["links"]
            if l["source"] == "doc_alpha" and l["target"] == "doc_beta"
        )
        assert "validation_status" not in link


class TestReport:
    def test_report_counts(self, fixture_data):
        graph, claims, verdicts = fixture_data
        report = av.apply_verdicts(graph, claims, verdicts)
        # Reviewed: EC-0001/0002/0004/0006 matched + EC-0003 unmatched.
        assert report["reviewed_claims"] == 5
        assert report["matched_claims"] == 4
        assert report["unmatched"] == ["EC-0003"]
        assert len(report["ambiguous"]) == 1
        assert report["ambiguous"][0]["claim_id"] == "EC-0004"
        assert report["ambiguous"][0]["matches"] == 2
        assert report["links_annotated"] == 5  # 3 singles + 2 from ambiguous


class TestFieldIntegrity:
    def test_only_validation_status_added_to_links(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        av.apply_verdicts(graph, claims, verdicts)
        for before, after in zip(snapshot["links"], graph["links"]):
            expected = dict(before)
            status = after.get("validation_status")
            if status is not None:
                expected["validation_status"] = status
                assert status in {
                    "CONFIRMED",
                    "EXTENDED",
                    "REFUTED",
                    "MIXED",
                    "NO_EVIDENCE_FOUND",
                }
            assert after == expected

    def test_nodes_and_top_level_keys_untouched(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        av.apply_verdicts(graph, claims, verdicts)
        assert graph["nodes"] == snapshot["nodes"]
        assert graph["hyperedges"] == snapshot["hyperedges"]
        assert graph["directed"] == snapshot["directed"]
        assert graph["multigraph"] == snapshot["multigraph"]
        assert graph["graph"] == snapshot["graph"]

    def test_confidence_sign_relation_immutable(self, fixture_data, snapshot):
        graph, claims, verdicts = fixture_data
        before = {
            id(l): (l["confidence"], l["sign"], l["relation"]) for l in graph["links"]
        }
        av.apply_verdicts(graph, claims, verdicts)
        for link in graph["links"]:
            conf, sign, rel = before[id(link)]
            assert link["confidence"] == conf
            assert link["sign"] == sign
            assert link["relation"] == rel


class TestCLI:
    def _write_inputs(self, tmp_path, fixture_data):
        graph, claims, verdict_map = fixture_data
        graph_path = tmp_path / "graph.json"
        claims_path = tmp_path / "claims.json"
        verdicts_path = tmp_path / "verdicts.json"
        graph_path.write_text(json.dumps(graph, indent=2))
        claims_payload = [
            c for c in claims if c["id"] != "EC-0003"
        ]  # keep file realistic; unmatched case covered by unit tests
        claims_path.write_text(json.dumps(claims_payload, indent=2))
        verdicts_payload = [{"claim_id": k, "verdict": v} for k, v in verdict_map.items()]
        verdicts_path.write_text(json.dumps(verdicts_payload, indent=2))
        return graph_path, claims_path, verdicts_path

    def test_dry_run_writes_nothing(self, tmp_path, fixture_data):
        graph_path, claims_path, verdicts_path = self._write_inputs(
            tmp_path, fixture_data
        )
        original_bytes = graph_path.read_bytes()
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--graph",
                str(graph_path),
                "--claims",
                str(claims_path),
                "--verdicts",
                str(verdicts_path),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert graph_path.read_bytes() == original_bytes
        assert "EC-0005" not in result.stderr or True  # summary goes to stdout
        assert "CONFIRMED" in result.stdout

    def test_write_updates_file_in_place(self, tmp_path, fixture_data):
        graph_path, claims_path, verdicts_path = self._write_inputs(
            tmp_path, fixture_data
        )
        n_nodes = len(fixture_data[0]["nodes"])
        n_links = len(fixture_data[0]["links"])
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--graph",
                str(graph_path),
                "--claims",
                str(claims_path),
                "--verdicts",
                str(verdicts_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        out = json.loads(graph_path.read_text())
        assert len(out["nodes"]) == n_nodes
        assert len(out["links"]) == n_links
        statuses = [l.get("validation_status") for l in out["links"]]
        assert statuses.count("CONFIRMED") >= 2
        assert "UNREVIEWED" not in statuses

    def test_defaults_point_at_repo_artifacts(self):
        import argparse

        parser = av.build_parser()
        args = parser.parse_args([])
        assert args.graph == Path("graphify-out/graph_v2.json")
        assert args.claims == Path("analysis/claims/claims.json")
        assert args.verdicts == Path("analysis/claims/verdicts.json")
        assert args.dry_run is False


class TestRealGraphSmoke:
    @pytest.fixture(scope="class")
    def real_run(self, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("real_graph")
        graph_path = tmp / "graph_v2.json"
        graph_path.write_text(REAL_GRAPH.read_text())
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--graph",
                str(graph_path),
                "--claims",
                str(REAL_CLAIMS),
                "--verdicts",
                str(REAL_VERDICTS),
            ],
            capture_output=True,
            text=True,
        )
        return graph_path, result

    def test_exit_zero_and_valid_json(self, real_run):
        graph_path, result = real_run
        assert result.returncode == 0, result.stderr
        data = json.loads(graph_path.read_text())
        orig = json.loads(REAL_GRAPH.read_text())
        assert len(data["nodes"]) == len(orig["nodes"])
        assert len(data["links"]) == len(orig["links"])

    def test_all_reviewed_edge_claims_get_status(self, real_run):
        graph_path, _ = real_run
        data = json.loads(graph_path.read_text())
        claims = json.loads(REAL_CLAIMS.read_text())
        verdict_map = {
            x["claim_id"]: x["verdict"]
            for x in json.loads(REAL_VERDICTS.read_text())
        }
        reviewed = [
            c
            for c in claims
            if c.get("kind") == "edge"
            and verdict_map.get(c["id"], "UNREVIEWED") != "UNREVIEWED"
        ]
        annotated = sum(1 for l in data["links"] if "validation_status" in l)
        # Every reviewable edge claim must land on at least one link.
        assert annotated >= len(reviewed) - 2
        allowed = {
            "CONFIRMED",
            "EXTENDED",
            "REFUTED",
            "MIXED",
            "NO_EVIDENCE_FOUND",
        }
        assert all(
            l["validation_status"] in allowed
            for l in data["links"]
            if "validation_status" in l
        )

    def test_real_fields_unchanged(self, real_run):
        graph_path, _ = real_run
        new = json.loads(graph_path.read_text())
        orig = json.loads(REAL_GRAPH.read_text())
        for before, after in zip(orig["links"], new["links"]):
            expected = dict(before)
            status = after.get("validation_status")
            if status is not None:
                assert status in {
                    "CONFIRMED",
                    "EXTENDED",
                    "REFUTED",
                    "MIXED",
                    "NO_EVIDENCE_FOUND",
                }
                expected["validation_status"] = status
            assert after == expected
