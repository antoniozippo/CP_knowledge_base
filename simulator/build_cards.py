#!/usr/bin/env python3
"""Build per-agent YAML cards from the literature knowledge graph (Task 2.2).

Part A  deterministic assembly: one AgentCard per document-type node, with
        inbound influence edges (confidence-derived weights), outbound ids,
        pathological rules derived from outbound signed links and matched
        edge claims. Rules whose claim refs are all REFUTED are dropped;
        MIXED evidence keeps the rule with a "[MIXED:<qualifier>]" prefix.
Part B  LLM enrichment for HUB tier only, gated behind --hub-enrich and
        delegated to enrich_hub_card() which shells out to the `opencode`
        CLI; every failure degrades to template text.
Part C  outputs: simulator/agent_cards/<safe_id>.yaml, _manifest.yaml with
        deterministic hashes, and a hub review digest markdown report.

Claim matching replicates the label normalizer of
analysis/scripts/apply_verdicts_to_graph.py (label_tokens /
build_label_index / resolve_label_ids).
"""

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from simulator.schemas import AgentCard, AgentTier, DynamicsRule, InfluenceEdge

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_CLAIMS = Path("analysis/claims/claims.json")
DEFAULT_VERDICTS = Path("analysis/claims/verdicts.json")
DEFAULT_OUTPUT_DIR = Path("simulator/agent_cards")
DEFAULT_REPORT = Path("simulator/reports/card_review_hubs.md")

CONFIDENCE_WEIGHTS = {
    "EXTRACTED": 0.9,
    "INFERRED": 0.5,
    "INFERRED_CLOSURE": 0.5,
    "AMBIGUOUS": 0.25,
}
ENTITY_BASELINE = {"drug": 0.0, "symptom": 0.05}
DEFAULT_BASELINE = 0.5
TIER_BY_NAME = {
    "hub": AgentTier.HUB,
    "mid": AgentTier.MID,
    "peripheral": AgentTier.PERIPHERAL,
}
NEUTRAL_KEEP_STATUSES = {"REFUTED", "MIXED"}
DESCRIPTION_MAX_CHARS = 200
NORMAL_ROLE_MAX_CHARS = 2000
DOSSIER_EXCERPT_CHARS = 3000
ENRICH_TIMEOUT_S = 120
HUB_PLACEHOLDER = "<LLM_ENRICH>"
RULE_GAP_TEXT = "all candidate rules refuted or none found"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# label matcher (replicated from analysis/scripts/apply_verdicts_to_graph.py)
# ---------------------------------------------------------------------------

PAREN_RE = re.compile(r"\([^)]*\)")
NON_WORD_RE = re.compile(r"[^\w\s]+")
WHITESPACE_RE = re.compile(r"\s+")


def label_tokens(label):
    """Lowercase paren-free word tokens for a label (norm_label style)."""
    text = PAREN_RE.sub(" ", str(label).lower())
    text = NON_WORD_RE.sub(" ", text)
    return [tok for tok in WHITESPACE_RE.split(text) if tok]


def build_label_index(nodes):
    """Map ' '.join(tokens) -> set of node ids for exact-token lookup."""
    index = defaultdict(set)
    for node in nodes:
        tokens = label_tokens(node.get("label") or node.get("norm_label") or "")
        if tokens:
            index[" ".join(tokens)].add(node["id"])
    return index


def resolve_label_ids(label, index):
    """Resolve a claim label to candidate node ids (exact then prefix match)."""
    tokens = label_tokens(label)
    if not tokens:
        return set()
    exact = index.get(" ".join(tokens))
    if exact:
        return set(exact)
    resolved = set()
    n = len(tokens)
    for key, ids in index.items():
        key_tokens = key.split()
        if len(key_tokens) >= n and key_tokens[:n] == tokens:
            resolved |= ids
    return resolved


def prepare_edge_claims(claims, index):
    """Pre-resolve edge-claim endpoint labels into a predicate-keyed lookup."""
    prepared = defaultdict(list)
    edges = sorted((c for c in claims if c.get("kind") == "edge"), key=lambda c: c.get("id", ""))
    for claim in edges:
        subject_ids = resolve_label_ids(claim.get("subject", ""), index)
        object_ids = resolve_label_ids(claim.get("object", ""), index)
        if not subject_ids or not object_ids:
            continue
        prepared[claim.get("predicate")].append(
            {"id": claim["id"], "subject_ids": subject_ids, "object_ids": object_ids}
        )
    return prepared


def matching_claim_ids(prepared_claims, relation, source_id, target_id):
    """Sorted ids of edge claims whose endpoints match the link either way."""
    hits = [
        claim["id"]
        for claim in prepared_claims.get(relation, ())
        if (source_id in claim["subject_ids"] and target_id in claim["object_ids"])
        or (source_id in claim["object_ids"] and target_id in claim["subject_ids"])
    ]
    return sorted(hits)


def build_verdict_map(verdict_entries):
    """claim_id -> full verdict entry dict (verdict + optional qualifier)."""
    return {
        entry["claim_id"]: entry
        for entry in verdict_entries
        if isinstance(entry, dict) and "claim_id" in entry
    }


# ---------------------------------------------------------------------------
# Part A — pure helpers
# ---------------------------------------------------------------------------

def safe_node_id(node_id):
    return re.sub(r"[^A-Za-z0-9]", "_", str(node_id))


def sanitize_rule_token(node_id):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(node_id))


def baseline_for(entity_type):
    return ENTITY_BASELINE.get(entity_type, DEFAULT_BASELINE)


def weight_for(confidence):
    return CONFIDENCE_WEIGHTS.get(confidence, DEFAULT_BASELINE)


def compose_description(subject_label, relation, target_label):
    text = f"{subject_label} {str(relation).replace('_', ' ')} {target_label}"
    return text[:DESCRIPTION_MAX_CHARS]


def apply_verdict_filter(refs, verdict_map):
    """Return (drop_rule, mixed_qualifier|None) for a rule's claim refs.

    drop_rule is True iff the rule has refs and every resolved verdict is
    REFUTED. mixed_qualifier comes from the first MIXED ref, if any.
    """
    resolved = [verdict_map[r]["verdict"] for r in refs if r in verdict_map]
    drop = bool(resolved) and all(v == "REFUTED" for v in resolved)
    mixed_qualifier = None
    for ref in refs:
        entry = verdict_map.get(ref)
        if entry is not None and entry.get("verdict") == "MIXED":
            mixed_qualifier = entry.get("qualifier") or "mixed evidence"
            break
    return drop, mixed_qualifier


def build_rules(node, label, outbound_links, nodes_by_id, prepared_claims, verdict_map):
    """One DynamicsRule per outbound sign!=0 link, verdict-filtered.

    Returns (rules, stats_delta) where stats_delta carries dropped/mixed
    counts plus details for the review digest.
    """
    rules = []
    dropped = 0
    mixed_count = 0
    dropped_details = []
    for number, link in enumerate(outbound_links, start=1):
        target_id = link["target"]
        target_label = nodes_by_id[target_id]["label"]
        relation = link["relation"]
        direction = "up" if link["sign"] == 1 else "down"
        rule_id = f"RULE-{sanitize_rule_token(node['id'])}-{number:02d}"
        refs = matching_claim_ids(prepared_claims, relation, node["id"], target_id)
        base_description = compose_description(label, relation, target_label)
        drop, mixed_qualifier = apply_verdict_filter(refs, verdict_map)
        if drop:
            dropped += 1
            dropped_details.append(
                {
                    "node_id": node["id"],
                    "label": label,
                    "rule_id": rule_id,
                    "direction": direction,
                    "description": base_description,
                    "refs": [
                        {
                            "ref": ref,
                            "verdict": (
                                verdict_map[ref].get("verdict")
                                if ref in verdict_map
                                else None
                            ),
                        }
                        for ref in refs
                    ],
                }
            )
            continue
        prefix = f"[MIXED:{mixed_qualifier}] " if mixed_qualifier else ""
        description = f"{prefix}{base_description}"[:DESCRIPTION_MAX_CHARS]
        rules.append(
            DynamicsRule(
                rule_id=rule_id,
                description=description,
                claim_refs=refs,
                direction=direction,
                magnitude_hint=None,
            )
        )
        if mixed_qualifier:
            mixed_count += 1
    stats_delta = {
        "dropped_refuted_rules": dropped,
        "mixed_annotated": mixed_count,
        "dropped_rule_details": dropped_details,
    }
    return rules, stats_delta


def template_normal_role(label, entity_type, compartment, baseline_state, n_in, n_out):
    return (
        f"{label} is a {entity_type} located in {compartment}. "
        f"Baseline activity level {baseline_state:.2f}. "
        f"It receives {n_in} regulatory influences and exerts {n_out}."
    )


# ---------------------------------------------------------------------------
# Part B — LLM hub enrichment (gated behind --hub-enrich)
# ---------------------------------------------------------------------------

def build_enrich_prompt(card, dossier_text):
    rules_block = "\n".join(
        f"- {r.rule_id} [{r.direction}] {r.description} "
        f"(claim_refs: {', '.join(r.claim_refs) if r.claim_refs else 'none'})"
        for r in card.pathological_rules
    ) or "- (none)"
    return (
        "You are assisting an agent-based physiology simulator.\n"
        f"Agent node: {card.label}\n"
        f"Entity type: {card.entity_type}\n"
        f"Compartment: {card.compartment}\n"
        "Pathological rules derived from the literature graph:\n"
        f"{rules_block}\n"
        "\n"
        "Dossier excerpt:\n"
        f"{dossier_text}\n"
        "\n"
        "Write 2-4 sentences describing this agent's physiological function in "
        "healthy conditions. Plain text only."
    )


def enrich_hub_card(card, dossier_text):
    """Call `opencode run` for a hub card's healthy-role description.

    Returns stripped stdout on success; "" on any failure (caller falls back
    to the deterministic template text).
    """
    prompt = build_enrich_prompt(card, dossier_text)
    cmd = [
        os.environ.get("OPENCODE_BIN", "opencode"),
        "run",
        "--format",
        "default",
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=ENRICH_TIMEOUT_S,
            check=True,
        )
    except Exception as exc:  # any failure degrades to template text
        logger.warning("hub enrichment failed for %s: %s", card.id, exc)
        return ""
    return proc.stdout.strip()


def load_dossier_excerpt(vault_dir, source_note):
    if not vault_dir or not source_note:
        return ""
    path = Path(vault_dir) / source_note
    try:
        return path.read_text(errors="replace")[:DOSSIER_EXCERPT_CHARS]
    except OSError as exc:
        logger.warning("dossier unreadable for %s: %s", source_note, exc)
        return ""


# ---------------------------------------------------------------------------
# card assembly
# ---------------------------------------------------------------------------

def select_document_nodes(graph_nodes, tier_filter=None):
    selected = []
    for node in graph_nodes:
        if node.get("file_type") != "document":
            continue
        tier_name = node.get("tier")
        if tier_name not in TIER_BY_NAME:
            raise ValueError(f"node '{node.get('id')}' has unknown tier '{tier_name}'")
        if tier_filter is not None and tier_name not in tier_filter:
            continue
        selected.append(node)
    return selected


def build_endpoint_indexes(nodes_by_id):
    """Card-universe indexes over document-type nodes for endpoint resolution."""
    doc_ids = set()
    docs_by_lower = {}
    docs_by_norm = defaultdict(list)
    for node_id, node in nodes_by_id.items():
        if node.get("file_type") != "document":
            continue
        doc_ids.add(node_id)
        docs_by_lower.setdefault(node_id.lower(), node_id)
        docs_by_norm[node.get("norm_label")].append(node_id)
    return nodes_by_id, doc_ids, docs_by_lower, docs_by_norm


def resolve_endpoint_id(endpoint, nodes_by_id, doc_ids, docs_by_lower, docs_by_norm):
    """Resolve a raw graph endpoint id to a card-producing id.

    Order: exact match, then case-insensitive id match, then the endpoint's
    own node norm_label matched against document norm_labels (deterministic
    lowest id on ties). Returns None when no document counterpart exists.
    """
    if endpoint in doc_ids:
        return endpoint
    case_hit = docs_by_lower.get(endpoint.lower())
    if case_hit is not None:
        return case_hit
    node = nodes_by_id.get(endpoint)
    if node is not None:
        norm_hits = sorted(docs_by_norm.get(node.get("norm_label"), []))
        if norm_hits:
            return norm_hits[0]
    return None


def build_influence_edge(link, source_id=None):
    sign = int(link.get("sign") or 0)
    status = link.get("validation_status")
    neutral_ok = False
    if sign == 0:
        neutral_ok = True
    return InfluenceEdge(
        source_id=source_id if source_id is not None else link["source"],
        relation=link["relation"],
        sign=sign,
        weight=weight_for(link.get("confidence")),
        validation_status=status,
        neutral_ok=neutral_ok,
    )


def build_card(node, nodes_by_id, inbound_links, outbound_links, prepared_claims,
               verdict_map, endpoint_ctx=None, hub_enrich=False, vault_dir=None):
    label = node["label"]
    entity_type = node["entity_type"]
    compartment = node["compartment"]
    baseline_state = baseline_for(entity_type)

    ctx = endpoint_ctx or (None,) * 4

    def resolve(endpoint):
        if ctx[0] is None:
            return endpoint
        return resolve_endpoint_id(endpoint, *ctx)

    # neutral links are excluded unless flagged REFUTED/MIXED by the review
    kept_inbound = [
        link for link in inbound_links
        if link.get("sign", 0) != 0
        or link.get("validation_status") in NEUTRAL_KEEP_STATUSES
    ]
    inbound_edges = []
    unresolved_drops = 0
    for link in kept_inbound:
        source = resolve(link["source"])
        if source is None:
            unresolved_drops += 1
            continue
        inbound_edges.append(build_influence_edge(link, source_id=source))
    outbound_ids = []
    for link in outbound_links:
        target = resolve(link["target"])
        if target is None:
            unresolved_drops += 1
            continue
        outbound_ids.append(target)
    rules, stats_delta = build_rules(
        node, label, outbound_links, nodes_by_id, prepared_claims, verdict_map
    )

    n_in, n_out = len(inbound_edges), len(outbound_ids)
    tier = TIER_BY_NAME[node["tier"]]
    if tier is AgentTier.HUB:
        normal_role = HUB_PLACEHOLDER
        gap_reason = RULE_GAP_TEXT if not rules else None
    else:
        normal_role = template_normal_role(
            label, entity_type, compartment, baseline_state, n_in, n_out
        )
        gap_reason = None

    card = AgentCard(
        id=node["id"],
        label=label,
        entity_type=entity_type,
        compartment=compartment,
        tier=tier,
        community=int(node.get("community") or 0),
        baseline_state=baseline_state,
        normal_role=normal_role,
        pathological_rules=rules,
        inbound_edges=inbound_edges,
        outbound_ids=outbound_ids,
        rule_gap_reason=gap_reason,
        source_note=node.get("source_file"),
    )

    if tier is AgentTier.HUB and hub_enrich:
        dossier_text = load_dossier_excerpt(vault_dir, node.get("source_file"))
        enriched = enrich_hub_card(card, dossier_text)
        if enriched:
            payload = card.model_dump()
            payload["normal_role"] = enriched[:NORMAL_ROLE_MAX_CHARS]
            card = AgentCard(**payload)
        else:
            payload = card.model_dump()
            payload["normal_role"] = template_normal_role(
                label, entity_type, compartment, baseline_state, n_in, n_out
            )[:NORMAL_ROLE_MAX_CHARS]
            card = AgentCard(**payload)

    return card, {
        **stats_delta,
        "unresolved_endpoint_drops": unresolved_drops,
    }


def build_cards(graph, claims, verdicts, *, hub_enrich=False, vault_dir=None,
                tier_filter=None):
    """Deterministic card assembly for document-type nodes.

    Returns (cards, stats); stats aggregates refuted drops, MIXED prefixes and
    dropped-rule details across all built cards.
    """
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    nodes_by_id = {node["id"]: node for node in nodes}

    inbound_by_target = defaultdict(list)
    outbound_by_source = defaultdict(list)
    for link in links:
        inbound_by_target[link["target"]].append(link)
        outbound_by_source[link["source"]].append(link)

    index = build_label_index(nodes)
    prepared_claims = prepare_edge_claims(claims, index)
    verdict_map = build_verdict_map(verdicts)
    endpoint_ctx = build_endpoint_indexes(nodes_by_id)

    cards = []
    stats = {
        "dropped_refuted_rules": 0,
        "mixed_annotated": 0,
        "dropped_rule_details": [],
        "unresolved_endpoint_drops": 0,
    }
    for node in select_document_nodes(nodes, tier_filter=tier_filter):
        card, delta = build_card(
            node,
            nodes_by_id,
            inbound_by_target.get(node["id"], []),
            [l for l in outbound_by_source.get(node["id"], []) if l.get("sign", 0) != 0],
            prepared_claims,
            verdict_map,
            endpoint_ctx=endpoint_ctx,
            hub_enrich=hub_enrich,
            vault_dir=vault_dir,
        )
        cards.append(card)
        stats["dropped_refuted_rules"] += delta["dropped_refuted_rules"]
        stats["mixed_annotated"] += delta["mixed_annotated"]
        stats["unresolved_endpoint_drops"] += delta["unresolved_endpoint_drops"]
        stats["dropped_rule_details"].extend(delta["dropped_rule_details"])
    return cards, stats


# ---------------------------------------------------------------------------
# Part C — outputs
# ---------------------------------------------------------------------------

def assign_card_filenames(card_ids):
    """Map card id -> YAML filename, collision-free on any filesystem.

    Plain safe ids get '<safe_id>.yaml'; when two distinct ids sanitize to
    names that clash case-insensitively (e.g. rbfox1_Rbfox1 vs rbfox1_rbfox1),
    every card involved gets a deterministic '_<sha8-of-id>' suffix so one
    file can never overwrite another.
    """
    plain = {card_id: safe_node_id(card_id) + ".yaml" for card_id in card_ids}
    claims = defaultdict(set)
    for card_id, filename in plain.items():
        claims[filename.lower()].add(card_id)
    collided_ids = {
        card_id
        for lower_name, owners in claims.items()
        if len(owners) > 1
        for card_id in owners
    }
    filenames = dict(plain)
    for card_id in collided_ids:
        stem = plain[card_id][:-len(".yaml")]
        suffix = hashlib.sha256(card_id.encode("utf-8")).hexdigest()[:8]
        filenames[card_id] = f"{stem}_{suffix}.yaml"
    return filenames


def write_cards(cards, output_dir):
    """Write one YAML file per card; return manifest entries (sorted by id)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(cards, key=lambda c: c.id)
    filenames = assign_card_filenames([card.id for card in ordered])
    entries = []
    for card in ordered:
        filename = filenames[card.id]
        data = yaml.safe_dump(
            card.model_dump(mode="json"), sort_keys=False, allow_unicode=True
        ).encode("utf-8")
        (output_dir / filename).write_bytes(data)
        entries.append(
            {
                "id": card.id,
                "file": filename,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return entries


def build_manifest(entries, graph_sha256, stats, cards):
    counts_by_tier = Counter(card.tier.value for card in cards)
    counts_by_entity = Counter(card.entity_type for card in cards)
    card_set_hash = hashlib.sha256(
        "\n".join(sorted(entry["sha256"] for entry in entries)).encode()
    ).hexdigest()
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_graph_sha256": graph_sha256,
        "counts_by_tier": dict(sorted(counts_by_tier.items())),
        "counts_by_entity_type": dict(sorted(counts_by_entity.items())),
        "cards": entries,
        "card_set_hash": card_set_hash,
        "dropped_refuted_rules": stats["dropped_refuted_rules"],
        "mixed_annotated": stats["mixed_annotated"],
        "unresolved_endpoint_drops": stats.get("unresolved_endpoint_drops", 0),
    }


def format_ref_list(refs):
    parts = []
    for ref in refs:
        verdict = ref.get("verdict")
        parts.append(f"{ref['ref']} ({verdict})" if verdict else f"{ref['ref']} (?)")
    return ", ".join(parts) if parts else "(no matched claims)"


def annotate_ref(ref, verdict_map):
    entry = (verdict_map or {}).get(ref)
    verdict = entry.get("verdict") if entry else None
    return f"{ref} ({verdict})" if verdict else ref


def write_report(cards, stats, report_path, verdict_map=None):
    hubs = sorted((c for c in cards if c.tier is AgentTier.HUB), key=lambda c: c.id)
    details_by_node = defaultdict(list)
    for detail in stats.get("dropped_rule_details", []):
        details_by_node[detail["node_id"]].append(detail)
    lines = [
        "# Hub agent card review digest",
        "",
        f"generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "Proposed normal roles are `<LLM_ENRICH>` placeholders unless the "
        "builder ran with --hub-enrich.",
        "",
    ]
    for card in hubs:
        lines.extend(
            [
                f"## {card.id} ({card.label})",
                "",
                f"- tier: {card.tier.value} | entity_type: {card.entity_type} | "
                f"compartment: {card.compartment} | community: {card.community}",
                f"- proposed_normal_role: {card.normal_role}",
            ]
        )
        if card.rule_gap_reason:
            lines.append(f"- rule_gap_reason: {card.rule_gap_reason}")
        lines.append(f"- pathological rules ({len(card.pathological_rules)}):")
        if not card.pathological_rules:
            lines.append("  - (none surviving verdict filtering)")
        for rule in card.pathological_rules:
            refs = (
                ", ".join(annotate_ref(ref, verdict_map) for ref in rule.claim_refs)
                if rule.claim_refs
                else "(none)"
            )
            lines.append(f"  - `{rule.rule_id}` [{rule.direction}] {rule.description}")
            lines.append(f"    - claim_refs: {refs}")
        dropped = details_by_node.get(card.id, [])
        if dropped:
            lines.append("- dropped candidate rules (all refs REFUTED):")
            for detail in dropped:
                lines.append(
                    f"  - `{detail['rule_id']}` [{detail['direction']}] "
                    f"{detail['description']} — refs: "
                    f"{format_ref_list(detail['refs'])}"
                )
        lines.append("")
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def graph_sha256_of(graph, input_graph_path=None):
    if input_graph_path is not None:
        return hashlib.sha256(Path(input_graph_path).read_bytes()).hexdigest()
    canonical = json.dumps(graph, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def reconcile_output_dir(output_dir, entries):
    """Remove stale card YAMLs left by earlier builds (e.g. files of nodes
    later renamed, merged away, or collision-renumbered). Returns removed names."""
    keep = {e["file"] for e in entries}
    removed = []
    for p in sorted(Path(output_dir).glob("*.yaml")):
        if p.name == "_manifest.yaml" or p.name in keep:
            continue
        p.unlink()
        removed.append(p.name)
    return removed


def generate_outputs(graph, claims, verdicts, *, output_dir, report_path,
                     vault_dir=None, input_graph_path=None, hub_enrich=False,
                     only_hubs=False):
    """Build cards and write all artifacts; returns (manifest, cards)."""
    tier_filter = {"hub"} if only_hubs else None
    cards, stats = build_cards(
        graph,
        claims,
        verdicts,
        hub_enrich=hub_enrich,
        vault_dir=vault_dir,
        tier_filter=tier_filter,
    )
    entries = write_cards(cards, output_dir)
    removed = reconcile_output_dir(output_dir, entries)
    manifest = build_manifest(
        entries, graph_sha256_of(graph, input_graph_path), stats, cards
    )
    manifest["stale_files_removed"] = removed
    manifest_path = Path(output_dir) / "_manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    write_report(cards, stats, report_path, verdict_map=build_verdict_map(verdicts))
    return manifest, cards


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path) as handle:
        return json.load(handle)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Build agent cards (Part A) from graph_v2 + claims + verdicts; "
            "optionally enrich HUB-tier normal roles via the opencode CLI "
            "(Part B, --hub-enrich)."
        )
    )
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH,
                        help="graphify knowledge graph JSON")
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS,
                        help="extracted claims JSON")
    parser.add_argument("--verdicts", type=Path, default=DEFAULT_VERDICTS,
                        help="verdict entries JSON")
    parser.add_argument("--vault-dir", type=Path, default=Path("."),
                        help="directory holding dossier *.md files")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="destination directory for card YAML files")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT,
                        help="path of the hub review digest markdown")
    parser.add_argument("--hub-enrich", action="store_true",
                        help="call opencode CLI for hub normal-role text")
    parser.add_argument("--only-hubs", action="store_true",
                        help="build/write only HUB-tier cards")
    return parser


def main(argv=None):
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    graph = load_json(args.graph)
    claims = load_json(args.claims)
    verdicts = load_json(args.verdicts)
    manifest, cards = generate_outputs(
        graph,
        claims,
        verdicts,
        output_dir=args.output_dir,
        report_path=args.report,
        vault_dir=args.vault_dir,
        input_graph_path=args.graph,
        hub_enrich=args.hub_enrich,
        only_hubs=args.only_hubs,
    )
    print(
        f"wrote {len(cards)} cards to {args.output_dir} "
        f"(by tier: {manifest['counts_by_tier']}); "
        f"refuted rules dropped: {manifest['dropped_refuted_rules']}; "
        f"mixed annotated: {manifest['mixed_annotated']}; "
        f"card_set_hash: {manifest['card_set_hash']}"
    )
    print(f"hub digest: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
