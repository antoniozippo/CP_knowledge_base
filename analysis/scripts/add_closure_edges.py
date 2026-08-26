#!/usr/bin/env python3
"""Apply evidence-backed dynamic-closure edges to graphify-out/graph_v2.json.

Task 2.4b Part B. Reads curated proposals from analysis/claims/
closure_edges.yaml, resolves every endpoint label to an existing
document-type node id (exact id, case-insensitive id, norm_label — the same
resolution ladder as simulator/build_cards.py), skips any (source, target)
pair that already exists as a link, and appends the remaining links with
full provenance:

    {relation, sign, confidence: "INFERRED_CLOSURE", weight: null,
     origin: "dynamic_closure", quote, source_ref}

validation_status and confidence_score keys are intentionally omitted:
graph tooling treats the presence of validation_status as a review verdict
and of confidence_score as a numeric model score, neither of which applies
to curated closure edges. weight stays null on the link; the card builder
maps confidence to a numeric weight via its CONFIDENCE_WEIGHTS map
(INFERRED_CLOSURE -> 0.5).
The tool is idempotent: a second run adds nothing because every applied
pair is then skipped as a duplicate.
"""

import argparse
import copy
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_PROPOSALS = Path("analysis/claims/closure_edges.yaml")

REQUIRED_FIELDS = ("source_label", "target_label", "relation", "sign", "quote", "source_file")


@dataclass
class ClosureSummary:
    proposed: int = 0
    added: int = 0
    updated: int = 0
    skipped_duplicates: int = 0
    unresolved: list = field(default_factory=list)

    def render(self) -> str:
        return (
            f"closure edges: proposed={self.proposed} added={self.added} "
            f"updated={self.updated} "
            f"skipped_duplicates={self.skipped_duplicates} unresolved={len(self.unresolved)}"
        )


# ---------------------------------------------------------------------------
# endpoint resolution (mirrors simulator/build_cards.py)
# ---------------------------------------------------------------------------

def _norm_tokens(label):
    import re

    text = re.sub(r"\([^)]*\)", " ", str(label).lower())
    text = re.sub(r"[^\w\s]+", " ", text)
    return [tok for tok in text.split() if tok]


def build_document_indexes(nodes):
    """Index document-type nodes for label -> id resolution."""
    by_id = {}
    by_lower = {}
    by_norm = defaultdict(list)
    norm_token_index = defaultdict(set)
    for node in nodes:
        if node.get("file_type") != "document":
            continue
        node_id = node["id"]
        by_id[node_id] = node
        by_lower.setdefault(node_id.lower(), node_id)
        by_norm[node.get("norm_label")].append(node_id)
        key = " ".join(_norm_tokens(node.get("label") or node.get("norm_label") or ""))
        if key:
            norm_token_index[key].add(node_id)
    return by_id, by_lower, by_norm, norm_token_index


def resolve_label_to_id(label, indexes):
    """Resolve one label to a document node id or None.

    Order: exact id, case-insensitive id, exact norm_label, token-prefix
    match over labels (deterministic lowest id on ties).
    """
    by_id, by_lower, by_norm, norm_token_index = indexes
    if label in by_id:
        return label
    case_hit = by_lower.get(str(label).lower())
    if case_hit is not None:
        return case_hit
    hits = sorted(by_norm.get(label, [])) or sorted(
        {nid for key, ids in by_norm.items() if key and key.lower() == str(label).lower() for nid in ids}
    )
    if hits:
        return hits[0]
    tokens = _norm_tokens(label)
    if not tokens:
        return None
    n = len(tokens)
    resolved = set()
    for key, ids in norm_token_index.items():
        key_tokens = key.split()
        if len(key_tokens) >= n and key_tokens[:n] == tokens:
            resolved |= ids
    return min(sorted(resolved)) if resolved else None


def resolve_proposal_endpoints(proposal, nodes):
    """Attach resolved source/target ids to one proposal dict (raises on failure)."""
    indexes = build_document_indexes(nodes)
    source_id = resolve_label_to_id(proposal["source_label"], indexes)
    target_id = resolve_label_to_id(proposal["target_label"], indexes)
    proposal = dict(proposal)
    proposal["source"] = source_id
    proposal["target"] = target_id
    return proposal


# ---------------------------------------------------------------------------
# application
# ---------------------------------------------------------------------------

def _validate_proposal(proposal, position):
    missing = [f for f in REQUIRED_FIELDS if proposal.get(f) is None]
    if missing:
        raise ValueError(f"proposal #{position} missing fields: {', '.join(missing)}")
    status = proposal.get("validation_status")
    if int(proposal["sign"]) == 0 and status not in ("REFUTED", "MIXED"):
        raise ValueError(
            f"proposal #{position}: sign 0 allowed only with validation_status REFUTED/MIXED (quarantine)"
        )
    if int(proposal["sign"]) not in (-1, 0, 1):
        raise ValueError(f"proposal #{position} sign must be -1, 0 or 1")
    if len(str(proposal["quote"])) > 400:
        raise ValueError(f"proposal #{position} quote exceeds 400 chars")


def apply_closure_edges(graph, proposals, update_quotes=False):
    """Pure core: return (new_graph, ClosureSummary); raises ValueError when
    any endpoint fails to resolve (graph left untouched in that case).

    With update_quotes=True, proposals whose (source, target) pair already
    exists as an origin=="dynamic_closure" link get their quote and
    source_ref metadata rewritten in place instead of being skipped.
    Topology (endpoints, relation, sign, confidence) is never modified."""
    new_graph = copy.deepcopy(graph)
    summary = ClosureSummary(proposed=len(proposals))

    checked = []
    unresolved = []
    for i, proposal in enumerate(proposals):
        _validate_proposal(proposal, i)
        resolved = resolve_proposal_endpoints(proposal, new_graph["nodes"])
        if resolved["source"] is None or resolved["target"] is None:
            bad = [
                label
                for label, rid in (
                    (resolved["source_label"], resolved["source"]),
                    (resolved["target_label"], resolved["target"]),
                )
                if rid is None
            ]
            unresolved.append({"index": i, "labels": bad})
            continue
        checked.append(resolved)

    if unresolved:
        detail = "; ".join(
            f"#{u['index']}: {', '.join(u['labels'])}" for u in unresolved
        )
        raise ValueError(f"unresolved endpoints ({len(unresolved)}): {detail}")

    links_by_pair = {}
    for link in new_graph["links"]:
        links_by_pair.setdefault((link["source"], link["target"]), []).append(link)
    existing_signed_pairs = {
        pair for pair, links in links_by_pair.items()
        if any(l.get("sign", 0) != 0 for l in links)
    }

    def _source_ref(resolved):
        note = resolved.get("source_ref_note")
        ref = resolved["source_file"]
        return f"{ref} | {note}" if note else ref

    for resolved in checked:
        pair = (resolved["source"], resolved["target"])
        if update_quotes:
            closure_links = [
                l for l in links_by_pair.get(pair, [])
                if l.get("origin") == "dynamic_closure"
            ]
            if closure_links:
                new_ref = _source_ref(resolved)
                if (
                    closure_links[0]["quote"] == resolved["quote"]
                    and closure_links[0]["source_ref"] == new_ref
                ):
                    summary.skipped_duplicates += 1
                else:
                    closure_links[0]["quote"] = resolved["quote"]
                    closure_links[0]["source_ref"] = new_ref
                    summary.updated += 1
                continue
        if pair in existing_signed_pairs:
            summary.skipped_duplicates += 1
            continue
        new_graph["links"].append(
            {
                "relation": resolved["relation"],
                "confidence": resolved.get("confidence", "INFERRED_CLOSURE"),
                "source_file": resolved["source_file"],
                "source_location": None,
                "weight": None,
                "source": resolved["source"],
                "target": resolved["target"],
                "sign": int(resolved["sign"]),
                "origin": "dynamic_closure",
                "quote": resolved["quote"],
                "source_ref": _source_ref(resolved),
            }
        )
        if resolved.get("validation_status"):
            new_graph["links"][-1]["validation_status"] = resolved["validation_status"]
        existing_signed_pairs.add(pair)
        links_by_pair.setdefault(pair, []).append(new_graph["links"][-1])
        summary.added += 1
    return new_graph, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument(
        "--update-quotes", action="store_true",
        help="rewrite quote/source_ref on existing origin=='dynamic_closure' "
             "links whose pair matches a proposal; never changes topology",
    )
    args = parser.parse_args(argv)

    graph = json.loads(args.graph.read_text())
    proposals = yaml.safe_load(args.proposals.read_text()) or []
    new_graph, summary = apply_closure_edges(graph, proposals, update_quotes=args.update_quotes)
    if summary.unresolved:
        raise SystemExit(summary.render())
    if summary.added or summary.updated:
        args.graph.write_text(json.dumps(new_graph, indent=2, ensure_ascii=False) + "\n")
    print(summary.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
