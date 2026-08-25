"""Tests for simulator.build_cards (Task 2.2).

Covers deterministic card assembly (Part A), gated LLM hub enrichment
(Part B, always mocked here) and output artifacts (Part C) against a small
synthetic graph + claims + verdicts fixture written into tmp_path.
"""

import hashlib
import json

import pytest
import yaml

import simulator.build_cards as bc
from simulator.schemas import AgentCard, AgentTier


# ---------------------------------------------------------------------------
# fixture builders
# ---------------------------------------------------------------------------

def _node(node_id, label, entity_type="molecule", compartment="cns", tier="mid",
          community=1, file_type="document", source_file=None):
    return {
        "id": node_id,
        "label": label,
        "file_type": file_type,
        "entity_type": entity_type,
        "compartment": compartment,
        "tier": tier,
        "community": community,
        "norm_label": label.lower(),
        "source_file": source_file,
    }


@pytest.fixture
def fixture_dir(tmp_path):
    """Synthetic graph/claims/verdicts + dossier vault.

    Nodes:
      N1 Substance P        hub        molecule  baseline 0.5
      N2 NK1 Receptor       mid        receptor  baseline 0.5
      N3 Drug X             peripheral drug      baseline 0.0
      N4 Mechanical Hypersensitivity   symptom   baseline 0.05
      R1 rationale note     rationale file_type -> excluded
      I1 figure             image      file_type -> excluded
      N7 Orphan Cytokine    hub        molecule  only refuted rule -> gap reason
    """
    root = tmp_path
    nodes = [
        _node("N1_substance_p", "Substance P", tier="hub", source_file="SP.md"),
        _node("N2_nk1", "NK1 Receptor", entity_type="receptor", source_file="SP.md"),
        _node("N3_drug_x", "Drug X", entity_type="drug", compartment="blood",
              tier="peripheral", community=2, source_file="DX.md"),
        _node("N4_pain", "Mechanical Hypersensitivity", entity_type="symptom",
              compartment="behavior", tier="peripheral", community=2, source_file="S.md"),
        _node("R1_rationale", "rationale note", file_type="rationale",
              tier="peripheral", community=0),
        _node("I1_image", "figure 1", entity_type="structure", file_type="image",
              tier="peripheral", community=0),
        _node("N7_orphan", "Orphan Cytokine", tier="hub", community=3,
              source_file="ORPH.md"),
    ]
    links = [
        # N1 outbound rules (3)
        {"source": "N1_substance_p", "target": "N2_nk1", "relation": "increases",
         "sign": 1, "confidence": "EXTRACTED"},
        {"source": "N1_substance_p", "target": "N4_pain", "relation": "activates",
         "sign": 1, "confidence": "INFERRED"},
        {"source": "N1_substance_p", "target": "N3_drug_x", "relation": "modulates",
         "sign": -1, "confidence": "AMBIGUOUS"},
        # inbound edges for other cards
        {"source": "N3_drug_x", "target": "N1_substance_p", "relation": "inhibits",
         "sign": -1, "confidence": "EXTRACTED"},
        # all-refuted rule for N2
        {"source": "N2_nk1", "target": "N4_pain", "relation": "worsens",
         "sign": 1, "confidence": "EXTRACTED"},
        # all-refuted rule for hub N7 -> rule gap
        {"source": "N7_orphan", "target": "N4_pain", "relation": "potentiates",
         "sign": 1, "confidence": "EXTRACTED"},
        # neutral link without status: excluded everywhere
        {"source": "N3_drug_x", "target": "N2_nk1", "relation": "conceptually_related_to",
         "sign": 0, "confidence": "EXTRACTED"},
        # neutral link with REFUTED status targeting N2: kept flagged
        {"source": "N4_pain", "target": "N2_nk1", "relation": "associated_with",
         "sign": 0, "confidence": "EXTRACTED", "validation_status": "REFUTED"},
        # neutral link with MIXED status targeting N3: kept flagged
        {"source": "N4_pain", "target": "N3_drug_x", "relation": "correlates_with",
         "sign": 0, "confidence": "EXTRACTED", "validation_status": "MIXED"},
    ]
    claims = [
        {"id": "EC-0001", "kind": "edge", "subject": "Substance P",
         "predicate": "increases", "object": "NK1 Receptor"},
        {"id": "EC-0002", "kind": "edge", "subject": "Drug X",
         "predicate": "inhibits", "object": "Substance P"},
        {"id": "EC-0003", "kind": "edge", "subject": "NK1 Receptor",
         "predicate": "worsens", "object": "Mechanical Hypersensitivity"},
        {"id": "EC-0004", "kind": "edge", "subject": "Substance P",
         "predicate": "modulates", "object": "Drug X"},
        {"id": "EC-0005", "kind": "edge", "subject": "Orphan Cytokine",
         "predicate": "potentiates", "object": "Mechanical Hypersensitivity"},
        {"id": "QC-0001", "kind": "quantitative", "subject": "ignored",
         "predicate": "ignored", "object": "ignored", "source_note": "SP.md",
         "quote": "x"},
    ]
    verdicts = [
        {"claim_id": "EC-0001", "verdict": "CONFIRMED", "qualifier": None},
        {"claim_id": "EC-0002", "verdict": "CONFIRMED", "qualifier": None},
        {"claim_id": "EC-0003", "verdict": "REFUTED", "qualifier": None},
        {"claim_id": "EC-0004", "verdict": "MIXED",
         "qualifier": "re-scope cell types"},
        {"claim_id": "EC-0005", "verdict": "REFUTED", "qualifier": None},
        {"claim_id": "EC-9999", "verdict": "UNREVIEWED", "qualifier": None},
    ]
    vault = root / "vault"
    vault.mkdir()
    (vault / "SP.md").write_text("dossier text about substance p " * 300)
    (root / "graph.json").write_text(json.dumps({"nodes": nodes, "links": links}))
    (root / "claims.json").write_text(json.dumps(claims))
    (root / "verdicts.json").write_text(json.dumps(verdicts))
    return root


def load_fixture(fixture_dir):
    graph = json.loads((fixture_dir / "graph.json").read_text())
    claims = json.loads((fixture_dir / "claims.json").read_text())
    verdicts = json.loads((fixture_dir / "verdicts.json").read_text())
    return graph, claims, verdicts


def card_by_id(cards, card_id):
    return next(c for c in cards if c.id == card_id)


# ---------------------------------------------------------------------------
# Part A — deterministic assembly
# ---------------------------------------------------------------------------

def test_only_document_nodes_become_cards_with_mapped_fields(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, stats = bc.build_cards(graph, claims, verdicts)
    ids = {c.id for c in cards}
    assert ids == {"N1_substance_p", "N2_nk1", "N3_drug_x", "N4_pain", "N7_orphan"}
    n1 = card_by_id(cards, "N1_substance_p")
    assert n1.label == "Substance P"
    assert n1.entity_type == "molecule"
    assert n1.compartment == "cns"
    assert n1.tier is AgentTier.HUB
    assert n1.community == 1
    assert n1.source_note == "SP.md"


def test_baseline_state_from_entity_baseline_map(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    by_id = {c.id: c for c in cards}
    assert by_id["N3_drug_x"].baseline_state == 0.0
    assert by_id["N4_pain"].baseline_state == pytest.approx(0.05)
    assert by_id["N1_substance_p"].baseline_state == 0.5


def test_inbound_edge_weight_mapping_and_passthrough(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    by_id = {c.id: c for c in cards}

    n2_edges = {(e.source_id, e.relation): e for e in by_id["N2_nk1"].inbound_edges}
    inc = n2_edges[("N1_substance_p", "increases")]
    assert inc.sign == 1 and inc.weight == 0.9
    assert inc.validation_status is None and inc.neutral_ok is False

    n4_edges = {(e.source_id, e.relation): e for e in by_id["N4_pain"].inbound_edges}
    act = n4_edges[("N1_substance_p", "activates")]
    assert act.weight == 0.5  # INFERRED

    n3_edges = {(e.source_id, e.relation): e for e in by_id["N3_drug_x"].inbound_edges}
    mod = n3_edges[("N1_substance_p", "modulates")]
    assert mod.weight == 0.25  # AMBIGUOUS
    assert mod.sign == -1


def test_neutral_links_excluded_unless_refuted_or_mixed(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    by_id = {c.id: c for c in cards}

    # neutral without validation_status never appears anywhere
    all_relations = {e.relation for c in cards for e in c.inbound_edges}
    assert "conceptually_related_to" not in all_relations

    n2_neutral = [e for e in by_id["N2_nk1"].inbound_edges if e.sign == 0]
    assert len(n2_neutral) == 1
    assert n2_neutral[0].source_id == "N4_pain"
    assert n2_neutral[0].neutral_ok is True
    assert n2_neutral[0].validation_status == "REFUTED"

    n3_neutral = [e for e in by_id["N3_drug_x"].inbound_edges if e.sign == 0]
    assert len(n3_neutral) == 1
    assert n3_neutral[0].validation_status == "MIXED"
    assert n3_neutral[0].neutral_ok is True

    # no card received the plain-neutral link
    for card in cards:
        for edge in card.inbound_edges:
            assert not (edge.relation == "conceptually_related_to")


def test_outbound_ids_only_sign_nonzero_targets(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    by_id = {c.id: c for c in cards}
    assert by_id["N1_substance_p"].outbound_ids == [
        "N2_nk1", "N4_pain", "N3_drug_x"
    ]
    assert by_id["N4_pain"].outbound_ids == []


def test_rules_direction_description_and_zero_padded_ids(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    n1 = card_by_id(cards, "N1_substance_p")
    assert [r.rule_id for r in n1.pathological_rules] == [
        "RULE-N1_substance_p-01", "RULE-N1_substance_p-02", "RULE-N1_substance_p-03"
    ]
    first = n1.pathological_rules[0]
    assert first.direction == "up"
    assert first.description == "Substance P increases NK1 Receptor"
    third = n1.pathological_rules[2]
    assert third.direction == "down"
    assert third.description == "[MIXED:re-scope cell types] Substance P modulates Drug X"
    assert all(r.magnitude_hint is None for r in n1.pathological_rules)


def test_claim_refs_matched_via_label_matcher(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    n1 = card_by_id(cards, "N1_substance_p")
    refs_by_target = {
        r.description.split()[-1]: r.claim_refs for r in n1.pathological_rules
    }
    assert refs_by_target["Receptor"] == ["EC-0001"]
    assert refs_by_target["X"] == ["EC-0004"]
    # activates link has no matching claim
    act_rule = next(
        r for r in n1.pathological_rules if r.description.endswith("Hypersensitivity")
    )
    assert act_rule.claim_refs == []


def test_refuted_rule_dropped_and_counted(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, stats = bc.build_cards(graph, claims, verdicts)
    n2 = card_by_id(cards, "N2_nk1")
    assert n2.pathological_rules == []
    assert stats["dropped_refuted_rules"] == 2  # N2 worsens + N7 potentiates


def test_mixed_verdict_prefix_respects_cap(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, stats = bc.build_cards(graph, claims, verdicts)
    n1 = card_by_id(cards, "N1_substance_p")
    mixed_rule = next(
        r for r in n1.pathological_rules if r.rule_id == "RULE-N1_substance_p-03"
    )
    assert mixed_rule.description.startswith("[MIXED:re-scope cell types] ")
    assert mixed_rule.description.endswith("Substance P modulates Drug X")
    assert len(mixed_rule.description) <= 200
    assert stats["mixed_annotated"] == 1


def test_description_truncated_at_200_chars():
    long_label = "L" * 400
    text = bc.compose_description(long_label, "increases", "T")
    assert len(text) == 200


def test_hub_gap_reason_when_all_rules_refuted(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    n7 = card_by_id(cards, "N7_orphan")
    assert n7.pathological_rules == []
    assert n7.rule_gap_reason == "all candidate rules refuted or none found"


def test_template_normal_role_for_non_hub(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts)
    n4 = card_by_id(cards, "N4_pain")
    expected = (
        "Mechanical Hypersensitivity is a symptom located in behavior. "
        "Baseline activity level 0.05. It receives 3 regulatory influences "
        "and exerts 0."
    )
    assert n4.normal_role == expected


# ---------------------------------------------------------------------------
# Part B — hub enrichment (mocked; never a real subprocess call in tests)
# ---------------------------------------------------------------------------

def test_hub_placeholder_without_enrichment(fixture_dir):
    graph, claims, verdicts = load_fixture(fixture_dir)
    cards, _ = bc.build_cards(graph, claims, verdicts, hub_enrich=False)
    for card in cards:
        if card.tier is AgentTier.HUB:
            assert card.normal_role == "<LLM_ENRICH>"
        else:
            assert card.normal_role.startswith(card.label + " is a ")


def test_enrichment_mock_replaces_placeholder_for_hubs_only(fixture_dir, monkeypatch):
    graph, claims, verdicts = load_fixture(fixture_dir)
    calls = []

    def fake_enrich(card, dossier_text):
        calls.append((card.id, dossier_text))
        return f"healthy role of {card.id}"

    monkeypatch.setattr(bc, "enrich_hub_card", fake_enrich)
    cards, _ = bc.build_cards(
        graph, claims, verdicts, hub_enrich=True, vault_dir=fixture_dir / "vault"
    )
    by_id = {c.id: c for c in cards}
    assert by_id["N1_substance_p"].normal_role == "healthy role of N1_substance_p"
    assert by_id["N7_orphan"].normal_role == "healthy role of N7_orphan"
    assert by_id["N2_nk1"].normal_role.startswith("NK1 Receptor is a ")
    assert sorted(cid for cid, _ in calls) == ["N1_substance_p", "N7_orphan"]
    # dossier excerpt passed through from the vault file
    (_, dossier_text), = [c for c in calls if c[0] == "N1_substance_p"]
    assert dossier_text.startswith("dossier text about substance p")


def test_enrichment_empty_result_falls_back_to_template(fixture_dir, monkeypatch):
    graph, claims, verdicts = load_fixture(fixture_dir)

    def fake_enrich(card, dossier_text):
        return ""

    monkeypatch.setattr(bc, "enrich_hub_card", fake_enrich)
    cards, _ = bc.build_cards(
        graph, claims, verdicts, hub_enrich=True, vault_dir=fixture_dir / "vault"
    )
    n1 = card_by_id(cards, "N1_substance_p")
    assert n1.normal_role != ""
    assert "<LLM_ENRICH>" not in n1.normal_role


def test_enrich_hub_card_subprocess_contract(monkeypatch):
    recorded = {}

    class ProcDone:
        stdout = "  enriched text  \n"

    def fake_run(cmd, capture_output, text, timeout, check):
        recorded["cmd"] = cmd
        recorded["timeout"] = timeout
        raise RuntimeError("no real subprocess allowed")

    monkeypatch.setenv("OPENCODE_BIN", "fake-opencode-bin")
    monkeypatch.setattr(bc.subprocess, "run", fake_run)
    card = AgentCard(
        id="H1", label="Hub One", entity_type="molecule", compartment="cns",
        tier=AgentTier.HUB, community=1, normal_role="<LLM_ENRICH>",
        rule_gap_reason="none found",
    )
    result = bc.enrich_hub_card(card, "dossier excerpt")
    assert result == ""
    assert recorded["cmd"][0] == "fake-opencode-bin"
    assert recorded["cmd"][1:4] == ["run", "--format", "text"]
    assert "Hub One" in recorded["cmd"][4]
    assert recorded["timeout"] == bc.ENRICH_TIMEOUT_S == 120


def test_enrich_hub_card_success_returns_stripped_stdout(monkeypatch):
    class ProcDone:
        stdout = "  healthy hub physiology text\n"

    captured = {}

    def fake_run(cmd, capture_output, text, timeout, check):
        captured["prompt"] = cmd[-1]
        return ProcDone()

    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(bc.subprocess, "run", fake_run)
    card = AgentCard(
        id="H1", label="Hub One", entity_type="molecule", compartment="cns",
        tier=AgentTier.HUB, community=1, normal_role="<LLM_ENRICH>",
        rule_gap_reason="none found",
    )
    result = bc.enrich_hub_card(card, "dossier body")
    assert result == "healthy hub physiology text"
    assert "dossier body" in captured["prompt"]
    assert "plain text" in captured["prompt"].lower()


# ---------------------------------------------------------------------------
# Part C — outputs
# ---------------------------------------------------------------------------

def generate(fixture_dir, out, report, **kwargs):
    graph, claims, verdicts = load_fixture(fixture_dir)
    manifest, cards = bc.generate_outputs(
        graph, claims, verdicts,
        output_dir=out, report_path=report,
        vault_dir=fixture_dir / "vault",
        input_graph_path=fixture_dir / "graph.json",
        **kwargs,
    )
    return manifest, cards


def test_yaml_round_trip_validates_into_agent_card(fixture_dir, tmp_path):
    out = tmp_path / "cards"
    report = tmp_path / "hubs.md"
    manifest, cards = generate(fixture_dir, out, report)
    written = sorted(p for p in out.glob("*.yaml") if p.name != "_manifest.yaml")
    assert len(written) == 5
    loaded = []
    for path in written:
        data = yaml.safe_load(path.read_text())
        loaded.append(AgentCard(**data))  # must validate
    assert {c.id for c in loaded} == {c.id for c in cards}


def test_manifest_contents_and_hash_stability(fixture_dir, tmp_path):
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    man_a, _ = generate(fixture_dir, out_a, tmp_path / "ra.md")
    man_b, _ = generate(fixture_dir, out_b, tmp_path / "rb.md")

    assert man_a["input_graph_sha256"] == hashlib.sha256(
        (fixture_dir / "graph.json").read_bytes()
    ).hexdigest()
    assert man_a["counts_by_tier"] == {"HUB": 2, "MID": 1, "PERIPHERAL": 2}
    assert man_a["counts_by_entity_type"] == {
        "molecule": 2, "receptor": 1, "drug": 1, "symptom": 1
    }
    assert man_a["dropped_refuted_rules"] == 2
    assert man_a["mixed_annotated"] == 1
    assert len(man_a["cards"]) == 5
    per_card_files = [entry["file"] for entry in man_a["cards"]]
    assert all((out_a / f).exists() for f in per_card_files)

    # determinism across runs: identical card shas and set hash
    assert man_a["card_set_hash"] == man_b["card_set_hash"]
    sha_a = sorted(e["sha256"] for e in man_a["cards"])
    sha_b = sorted(e["sha256"] for e in man_b["cards"])
    assert sha_a == sha_b

    # card_set_hash is sha256 over the sorted per-card sha256 strings
    digest = hashlib.sha256("\n".join(sha_a).encode()).hexdigest()
    assert man_a["card_set_hash"] == digest

    # per-card sha256 matches actual file content
    entry = next(e for e in man_a["cards"] if e["id"] == "N1_substance_p")
    content = (out_a / entry["file"]).read_bytes()
    assert entry["sha256"] == hashlib.sha256(content).hexdigest()


def test_safe_filenames_and_manifest_fields(fixture_dir, tmp_path):
    out = tmp_path / "cards"
    manifest, _ = generate(fixture_dir, out, tmp_path / "hubs.md")
    files = {p.name for p in out.glob("*.yaml")}
    assert "_manifest.yaml" in files
    assert "N1_substance_p.yaml" in files
    assert manifest["generated_at_utc"].endswith("Z")
    assert set(manifest.keys()) >= {
        "generated_at_utc", "input_graph_sha256", "counts_by_tier",
        "counts_by_entity_type", "cards", "card_set_hash",
        "dropped_refuted_rules", "mixed_annotated",
    }


def test_only_hubs_writes_subset(fixture_dir, tmp_path):
    out = tmp_path / "cards"
    manifest, cards = generate(
        fixture_dir, out, tmp_path / "hubs.md", only_hubs=True
    )
    assert {c.id for c in cards} == {"N1_substance_p", "N7_orphan"}
    files = {p.name for p in out.glob("*.yaml")}
    assert files == {"_manifest.yaml", "N1_substance_p.yaml", "N7_orphan.yaml"}
    assert manifest["counts_by_tier"] == {"HUB": 2}
    assert manifest["counts_by_entity_type"] == {"molecule": 2}
    assert len(manifest["cards"]) == 2
    assert manifest["dropped_refuted_rules"] == 1  # only N7's refuted rule


def test_report_digest_lists_hub_rules_refs_and_roles(fixture_dir, tmp_path):
    report = tmp_path / "card_review_hubs.md"
    _, _ = generate(fixture_dir, out=tmp_path / "cards", report=report)
    text = report.read_text()
    assert "# Hub agent card review digest" in text
    for hub_id in ("N1_substance_p", "N7_orphan"):
        assert hub_id in text
    assert "EC-0001 (CONFIRMED)" in text
    # N7's only candidate rule was dropped as fully refuted; digest shows it
    assert "EC-0005 (REFUTED)" in text
    assert "[MIXED" in text
    assert "<LLM_ENRICH>" in text
    assert "all candidate rules refuted or none found" in text


def test_case_insensitive_id_collision_gets_distinct_files(fixture_dir, tmp_path):
    """Ids differing only by case must not collide on case-insensitive
    filesystems (real graph has rbfox1_Rbfox1/rbfox1_rbfox1)."""
    # pure assignment: colliding safe names get a deterministic id-derived suffix
    names = bc.assign_card_filenames(["rbfox1_Rbfox1", "rbfox1_rbfox1"])
    assigned = [names[i] for i in ("rbfox1_Rbfox1", "rbfox1_rbfox1")]
    assert len(set(assigned)) == 2
    assert len({f.lower() for f in assigned}) == 2
    # non-colliding ids keep the plain sanitized name
    plain = bc.assign_card_filenames(["N3_drug_x", "N4_pain"])
    assert plain == {"N3_drug_x": "N3_drug_x.yaml", "N4_pain": "N4_pain.yaml"}
    # deterministic across invocations
    again = bc.assign_card_filenames(["rbfox1_rbfox1", "rbfox1_Rbfox1"])
    assert again == names

    # end-to-end: manifest lists distinct, case-fold-distinct files whose
    # recorded shas match what write_cards serialized for each card
    graph, claims, verdicts = load_fixture(fixture_dir)
    graph["nodes"].append(
        _node("n1_SUBSTANCE_P", "Substance P Alias", entity_type="molecule",
              tier="mid", community=4)
    )
    cards, _ = bc.build_cards(graph, claims, verdicts)
    entries = bc.write_cards(cards, tmp_path / "cards")
    files = [e["file"] for e in entries]
    assert len(files) == len(set(files))
    assert len({f.lower() for f in files}) == len(files)


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def test_main_end_to_end_writes_artifacts(fixture_dir, tmp_path, capsys):
    rc = bc.main([
        "--graph", str(fixture_dir / "graph.json"),
        "--claims", str(fixture_dir / "claims.json"),
        "--verdicts", str(fixture_dir / "verdicts.json"),
        "--vault-dir", str(fixture_dir / "vault"),
        "--output-dir", str(tmp_path / "cli_cards"),
        "--report", str(tmp_path / "cli_hubs.md"),
    ])
    assert rc == 0
    out = tmp_path / "cli_cards"
    assert (out / "_manifest.yaml").exists()
    assert (out / "N3_drug_x.yaml").exists()
    assert (tmp_path / "cli_hubs.md").exists()
    summary = capsys.readouterr().out
    assert "cards" in summary


def test_tests_never_invoke_real_opencode(monkeypatch):
    """Guard: any accidental real subprocess call inside build_cards fails."""
    def forbidden(*args, **kwargs):
        raise AssertionError("tests must not spawn real opencode processes")

    monkeypatch.setattr(bc.subprocess, "run", forbidden)
    monkeypatch.setattr(bc.subprocess, "Popen", forbidden, raising=False)


def test_inferred_closure_confidence_maps_to_half_weight():
    """Dynamic-closure edges (confidence INFERRED_CLOSURE) get weight 0.5."""
    assert bc.CONFIDENCE_WEIGHTS["INFERRED_CLOSURE"] == 0.5
    assert bc.weight_for("INFERRED_CLOSURE") == 0.5
    link = {
        "source": "s",
        "relation": "causes",
        "sign": 1,
        "confidence": "INFERRED_CLOSURE",
        "validation_status": None,
        "weight": None,
    }
    edge = bc.build_influence_edge(link)
    assert edge.weight == 0.5
