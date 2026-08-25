"""Tests for extract_claims: edge claim cards, quantitative mining, index."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_GRAPH = REPO_ROOT / "graphify-out" / "graph_v2.json"

sys.path.insert(0, str(REPO_ROOT / "analysis" / "scripts"))
import extract_claims as ec  # noqa: E402

REQUIRED_KEYS = [
    "id",
    "kind",
    "subject",
    "predicate",
    "object",
    "sign",
    "confidence",
    "source_note",
    "quote",
    "citation_status",
    "priority",
    "priority_flag",
    "theme_hint",
]

ALPHA_MD = """# Alpha Dossier

Neuropathic rats received gabapentin at 30 mg/kg body weight daily after sciatic nerve injury.

## Section

Microglial activation increased by 45% within the dorsal horn in this pain model.

Neuropathic rats received gabapentin at 30 mg/kg body weight daily after sciatic nerve injury.

No measurable content appears in this particular sentence at all.
"""

BETA_MD = """# Beta Dossier

Expression of the kinase rose 2.5-fold in injured DRG neurons compared with controls.

The antagonist showed an IC50 of 12 nM against the receptor in the binding assay.

Animals were perfused 24 h after treatment onset in this protocol.

Tissue was collected 72 h later and stored at minus eighty degrees.
"""

GAMMA_LONG_SENTENCE = (
    "Chronic constriction injury animals treated across 21 days showed "
    + "mechanical threshold recovery metrics " * 40
    + "with 10 mg/kg dosing."
)


def make_node(id_, label):
    return {"label": label, "id": id_, "source_file": f"{id_}.md"}


def make_link(source, target, relation, confidence="EXTRACTED", sign=0):
    return {
        "relation": relation,
        "confidence": confidence,
        "confidence_score": 1.0,
        "weight": 1.0,
        "source_file": f"{source}_dossier.md",
        "source_location": None,
        "source": source,
        "target": target,
        "sign": sign,
    }


@pytest.fixture
def fixture_graph():
    nodes = [
        make_node("a", "BDNF"),
        make_node("b", "KCC2 (SLC12A5 chloride cotransporter)"),
        make_node("k", "Kalirin-7 (GEF for Rac1/RhoG)"),
        make_node("rho", "RhoA GTPase"),
        make_node("nrcam", "NrCAM (Neuronal Cell Adhesion Molecule)"),
        make_node("ngr1", "NgR1 (Nogo-66 Receptor 1)"),
    ]
    links = [
        make_link("a", "b", "activates", "EXTRACTED", 1),
        make_link("rho", "k", "antagonizes_pathway", "INFERRED", -1),
        make_link("a", "k", "activates", "EXTRACTED", 1),
        make_link("nrcam", "ngr1", "potentially_interacts_via_cell_adhesion", "AMBIGUOUS", 1),
        make_link("b", "a", "references", "EXTRACTED", 0),
    ]
    return {
        "directed": True,
        "multigraph": True,
        "graph": {},
        "nodes": nodes,
        "links": links,
        "hyperedges": [],
    }


def make_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    (vault / "Alpha_dossier.md").write_text(ALPHA_MD, encoding="utf-8")
    (vault / "Beta_dossier.md").write_text(BETA_MD, encoding="utf-8")
    (vault / "Gamma_long.md").write_text(GAMMA_LONG_SENTENCE + "\n", encoding="utf-8")
    (vault / "README.md").write_text("Ignore me with 100 mg/kg content.\n", encoding="utf-8")
    nested = vault / "sub"
    nested.mkdir(exist_ok=True)
    (nested / "Nested.md").write_text("Nested 99 mg/kg dose in injury model.\n", encoding="utf-8")
    return vault


def graph_copy(graph):
    return json.loads(json.dumps(graph))


def _empty_graph():
    return {"nodes": [], "links": [], "hyperedges": []}


@pytest.fixture
def claims(fixture_graph, tmp_path):
    return ec.extract_all(graph_copy(fixture_graph), make_vault(tmp_path))


def by_kind(claims, kind):
    return [c for c in claims if c["kind"] == kind]


class TestEdgeClaims:
    def test_signed_extracted_edge_becomes_p0_claim(self, claims):
        match = [
            c for c in by_kind(claims, "edge")
            if c["predicate"] == "activates" and c["object"] == "KCC2 (SLC12A5 chloride cotransporter)"
        ]
        assert len(match) == 1
        claim = match[0]
        assert claim["id"].startswith("EC-")
        assert claim["priority"] == "P0"
        assert claim["sign"] == 1
        assert claim["confidence"] == "EXTRACTED"
        assert claim["subject"] == "BDNF"
        assert claim["quote"] is None
        assert claim["citation_status"] == "UNVERIFIED"
        assert claim["theme_hint"] is None
        assert claim["priority_flag"] is None
        assert claim["source_note"] == "a_dossier.md"

    def test_zero_sign_edges_excluded(self, claims):
        assert not [c for c in by_kind(claims, "edge") if c["predicate"] == "references"]

    def test_inferred_kalirin_edge_gets_p1_and_flag(self, claims):
        match = [c for c in by_kind(claims, "edge") if c["object"].startswith("Kalirin-7")
                 and c["confidence"] == "INFERRED"]
        assert len(match) == 1
        claim = match[0]
        assert claim["priority"] == "P1"
        assert claim["sign"] == -1
        assert claim["priority_flag"] == "kalirin_inferred"

    def test_extracted_kalirin_edge_has_no_flag(self, claims):
        match = [c for c in by_kind(claims, "edge") if c["object"].startswith("Kalirin-7")
                 and c["confidence"] == "EXTRACTED"]
        assert len(match) == 1
        assert match[0]["priority"] == "P0"
        assert match[0]["priority_flag"] is None

    def test_nrcam_ngr1_pair_flagged_ambiguous_p1(self, claims):
        match = [c for c in by_kind(claims, "edge") if c["predicate"] == "potentially_interacts_via_cell_adhesion"]
        assert len(match) == 1
        claim = match[0]
        assert claim["priority"] == "P1"
        assert claim["priority_flag"] == "nrcam_ngr1_ambiguous"


class TestQuantClaims:
    def test_concentration_sentence_claimed_with_tokens(self, claims):
        match = [c for c in by_kind(claims, "quantitative") if "mg/kg" in c["quote"]
                 and c["subject"] == "Alpha_dossier"]
        assert len(match) == 1
        claim = match[0]
        assert claim["id"].startswith("QC-")
        assert claim["predicate"] == "quantitative_statement"
        assert claim["priority"] == "P3"
        assert claim["sign"] == 0
        assert claim["confidence"] == "EXTRACTED"
        assert claim["citation_status"] == "UNVERIFIED"
        assert claim["theme_hint"] is None
        assert claim["value_tokens"] == ["30 mg/kg"]
        assert claim["source_note"] == "Alpha_dossier.md"

    def test_percent_sentence_claimed(self, claims):
        match = [c for c in by_kind(claims, "quantitative") if "%" in c["quote"]]
        assert len(match) == 1
        assert match[0]["value_tokens"] == ["45%"]

    def test_fold_and_ic50_sentences_claimed(self, claims):
        fold = [c for c in by_kind(claims, "quantitative") if "fold" in c["quote"]]
        ic50 = [c for c in by_kind(claims, "quantitative") if "IC50" in c["quote"]]
        assert len(fold) == 1 and fold[0]["value_tokens"] == ["2.5-fold"]
        assert len(ic50) == 1
        assert "IC50 of 12" in ic50[0]["value_tokens"]
        assert "12 nM" in ic50[0]["value_tokens"]

    def test_timepoint_requires_context_words(self, claims):
        with_context = [c for c in by_kind(claims, "quantitative") if "24 h" in c["quote"]]
        without_context = [c for c in by_kind(claims, "quantitative") if "72 h" in c["quote"]]
        assert len(with_context) == 1
        assert with_context[0]["value_tokens"] == ["24 h"]
        assert not without_context

    def test_duplicate_sentences_deduped_within_file(self, claims):
        mgkg = [c for c in by_kind(claims, "quantitative") if c["subject"] == "Alpha_dossier"
                and "mg/kg" in c["quote"]]
        assert len(mgkg) == 1

    def test_no_numbers_no_claim(self, claims):
        assert not [c for c in by_kind(claims, "quantitative") if "No measurable content" in c["quote"]]

    def test_object_trimmed_to_400_chars(self, claims):
        long_claims = [c for c in by_kind(claims, "quantitative") if c["subject"] == "Gamma_long"]
        assert len(long_claims) == 1
        claim = long_claims[0]
        assert len(claim["object"]) == 400
        assert claim["object"] == claim["quote"][:400]
        assert len(claim["quote"]) > 400

    def test_readme_and_subdirs_skipped(self, claims):
        subjects = {c["subject"] for c in by_kind(claims, "quantitative")}
        assert all(not s.lower().startswith("readme") for s in subjects)
        assert "Nested" not in subjects


class TestSchemaAndOrder:
    def test_all_claims_have_complete_schema(self, claims):
        for claim in claims:
            assert set(REQUIRED_KEYS) <= set(claim), claim["id"]
            assert claim["kind"] in {"edge", "quantitative"}
            assert claim["citation_status"] == "UNVERIFIED"
            assert claim["theme_hint"] is None
        quant = by_kind(claims, "quantitative")
        assert quant and all(isinstance(c["value_tokens"], list) and c["value_tokens"] for c in quant)

    def test_ids_sequential_per_prefix(self, claims):
        for prefix in ("EC", "QC"):
            ids = sorted(c["id"] for c in claims if c["id"].startswith(prefix))
            expected = [f"{prefix}-{i:04d}" for i in range(1, len(ids) + 1)]
            assert ids == expected

    def test_sorted_by_priority_then_id(self, claims):
        ranks = [ec.PRIORITY_RANK[c["priority"]] for c in claims]
        assert ranks == sorted(ranks)
        ids = [c["id"] for c in claims if c["priority"] == "P0"]
        assert ids == sorted(ids)

    def test_index_counts_match_fixture(self, claims):
        index = ec.summarize(claims)
        assert index["counts_by_priority"] == {"P0": 2, "P1": 2, "P2": 0, "P3": 6}
        assert index["counts_by_kind"] == {"edge": 4, "quantitative": 6}
        assert index["counts_by_confidence"] == {"EXTRACTED": 8, "INFERRED": 1, "AMBIGUOUS": 1}
        assert index["kalirin_inferred_count"] == 1
        assert index["nrcam_ngr1_flag_count"] == 1
        assert index["quantitative_statement_count"] == 6
        assert "warnings" not in index

    def test_cap_exceeded_noted_not_truncated(self, tmp_path):
        vault = tmp_path / "bulk_vault"
        vault.mkdir()
        lines = [
            f"Dose batch {i} mg/kg was administered in the neuropathic pain model."
            for i in range(ec.QUANT_WARN_THRESHOLD + 5)
        ]
        (vault / "Bulk.md").write_text("\n\n".join(lines), encoding="utf-8")
        claims = ec.extract_all(_empty_graph(), vault)
        quant = by_kind(claims, "quantitative")
        assert len(quant) == ec.QUANT_WARN_THRESHOLD + 5
        index = ec.summarize(claims)
        assert index["warnings"] and str(ec.QUANT_WARN_THRESHOLD) in index["warnings"][0]

    def test_ids_stable_across_runs(self, fixture_graph, tmp_path):
        first = ec.extract_all(graph_copy(fixture_graph), make_vault(tmp_path))
        second = ec.extract_all(graph_copy(fixture_graph), make_vault(tmp_path))
        assert first == second

    def test_input_graph_not_mutated(self, fixture_graph, tmp_path):
        snapshot = json.dumps(fixture_graph)
        ec.extract_all(fixture_graph, make_vault(tmp_path))
        assert json.dumps(fixture_graph) == snapshot


class TestTextMunging:
    def test_frontmatter_block_skipped(self, tmp_path):
        (tmp_path / "FM.md").write_text(
            "---\ntitle: X\nignore 10 mg/kg metadata\n---\n\nReal dose 5 mg/kg in pain model.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        assert [c["quote"] for c in claims] == ["Real dose 5 mg/kg in pain model."]

    def test_unclosed_frontmatter_yields_no_claims(self, tmp_path):
        (tmp_path / "Bad.md").write_text(
            "---\ntitle: X\nstray 10 mg/kg line never closed\n", encoding="utf-8"
        )
        assert ec.extract_all(_empty_graph(), tmp_path) == []

    def test_code_fence_content_skipped(self, tmp_path):
        (tmp_path / "Code.md").write_text(
            "```\nfenced 20 mg/kg pseudo-dose in model\n```\n\nProse dose 5 mg/kg in pain model.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        assert [c["value_tokens"] for c in claims] == [["5 mg/kg"]]

    def test_split_sentences_merges_across_abbreviations(self):
        assert len(ec.split_sentences("Allodynia fell as reported by Coull et al. (2003) in rodents.")) == 1
        assert len(ec.split_sentences("Some doses e.g. 50% shifts appeared. Next one stands alone.")) == 2

    @pytest.mark.parametrize("hyphen", ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014"])
    def test_unicode_hyphen_fold_and_timepoint_match(self, tmp_path, hyphen):
        (tmp_path / "Uni.md").write_text(
            f"Expression rose 2.5{hyphen}fold in injured DRG neurons.\n\n"
            f"Animals were perfused 24{hyphen}h after treatment onset.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        assert len(claims) == 2
        tokens = [token for claim in claims for token in claim["value_tokens"]]
        assert any(token.startswith("2.5") and token.endswith("fold") for token in tokens), tokens
        assert any(token.startswith("24") and token.endswith("h") for token in tokens), tokens

    def test_hardwrapped_paragraph_yields_full_sentence_quote(self, tmp_path):
        (tmp_path / "Wrap.md").write_text(
            "Rats received gabapentin daily for 7 days) significantly\n"
            "reduced mechanical allodynia in this injury model.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        assert len(claims) == 1
        assert claims[0]["quote"].endswith("allodynia in this injury model.")
        assert "7 days" in claims[0]["value_tokens"]

    def test_adjacent_bullets_without_blank_lines_stay_separate(self, tmp_path):
        (tmp_path / "Bullets.md").write_text(
            "*   **Etifoxine (Stresam)** :\n"
            "    *   Etifoxine (50 mg/kg, twice daily) post-nerve crush significantly alleviated hypersensitivity.\n"
            "    *   A second etifoxline arm used 25 mg/kg dosing in the monoarthritis model.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        quotes = [c["quote"] for c in claims]
        assert len(quotes) == 2
        assert quotes[0].startswith("Etifoxine (50 mg/kg")
        assert quotes[1].startswith("A second etifoxline arm")
        tokens = [token for c in claims for token in c["value_tokens"]]
        assert "50 mg/kg" in tokens and "25 mg/kg" in tokens

    def test_heading_and_blockquote_are_boundaries(self, tmp_path):
        (tmp_path / "Mixed.md").write_text(
            "### Dosing Summary\n"
            "- Loading dose was 10 mg/kg in the treated cohort.\n"
            "> Quote: maintenance used 5 mg/kg in the pain model.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        assert [c["value_tokens"] for c in claims] == [["10 mg/kg"], ["5 mg/kg"]]
        assert claims[0]["quote"].startswith("Dosing Summary") is False

    def test_dose_like_hyphen_line_is_not_a_bullet_boundary(self, tmp_path):
        (tmp_path / "Dose.md").write_text(
            "Escalation schedule\n-5 mM bolus was followed by 2 mg/kg maintenance infusions.\n",
            encoding="utf-8",
        )
        claims = ec.extract_all(_empty_graph(), tmp_path)
        assert len(claims) == 1
        assert claims[0]["quote"].startswith("Escalation schedule")

    def test_ip_abbreviation_merged(self):
        assert len(ec.split_sentences("AMG487 was given i.p. (3 mg/kg) daily in the CCI model.")) == 1

    def test_decode_error_reports_filename(self, tmp_path, capsys):
        (tmp_path / "Broken.md").write_bytes(b"\xff\xfe not utf8 with 10 mg/kg")
        (tmp_path / "Good.md").write_text("Dose 5 mg/kg in pain model.\n", encoding="utf-8")
        with pytest.raises(UnicodeDecodeError):
            ec.extract_all(_empty_graph(), tmp_path)
        assert "Broken.md" in capsys.readouterr().err


class TestCli:
    def test_writes_outputs_with_sha_and_timestamp(self, fixture_graph, tmp_path):
        graph_path = tmp_path / "graph_v2.json"
        graph_path.write_text(json.dumps(fixture_graph), encoding="utf-8")
        out_dir = tmp_path / "claims_out"
        rc = ec.main([
            "--graph", str(graph_path),
            "--output-dir", str(out_dir),
        ])
        assert rc == 0
        claims_out = json.loads((out_dir / "claims.json").read_text(encoding="utf-8"))
        index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        assert isinstance(claims_out, list) and claims_out
        assert hashlib.sha256(graph_path.read_bytes()).hexdigest() == index["input_sha256"]
        datetime.fromisoformat(index["generated_at"])

    def test_default_output_and_vault_dirs(self, fixture_graph, tmp_path, monkeypatch):
        graph_path = tmp_path / "graph_v2.json"
        graph_path.write_text(json.dumps({"nodes": [], "links": []}), encoding="utf-8")
        (tmp_path / "Solo.md").write_text("Dose 5 mg/kg in pain model.\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = ec.main(["--graph", str(graph_path)])
        assert rc == 0
        out_path = tmp_path / "analysis" / "claims" / "claims.json"
        claims_out = json.loads(out_path.read_text(encoding="utf-8"))
        assert any("5 mg/kg" in c["value_tokens"] for c in claims_out)


class TestRealInputsSmoke:
    @pytest.mark.skipif(not REAL_GRAPH.exists(), reason="real graph_v2.json not present")
    def test_full_run_on_real_inputs(self, tmp_path):
        out_dir = tmp_path / "claims"
        rc = ec.main([
            "--graph", str(REAL_GRAPH),
            "--vault-dir", str(REPO_ROOT),
            "--output-dir", str(out_dir),
        ])
        assert rc == 0
        claims_out = json.loads((out_dir / "claims.json").read_text(encoding="utf-8"))
        raw = json.loads(REAL_GRAPH.read_text(encoding="utf-8"))
        expected_edges = sum(1 for link in raw["links"] if link.get("sign", 0) != 0)
        edges = by_kind(claims_out, "edge")
        quants = by_kind(claims_out, "quantitative")
        assert len(edges) == expected_edges
        assert len(quants) > 50
        index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        total = sum(index["counts_by_priority"].values())
        assert total == len(claims_out)
        assert index["nrcam_ngr1_flag_count"] >= 1
        assert index["kalirin_inferred_count"] >= 1
        priorities = {c["priority"] for c in claims_out}
        assert priorities <= {"P0", "P1", "P3"}
