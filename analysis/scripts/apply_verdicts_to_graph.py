#!/usr/bin/env python3
"""Propagate literature-review verdicts from claims onto knowledge-graph edges.

Pipeline:
 1. Load graphify-out/graph_v2.json (nodes + links), analysis/claims/claims.json
    (kind == "edge" claims) and analysis/claims/verdicts.json.
 2. For every edge claim whose verdict is not UNREVIEWED, find matching graph
    links: identical relation string AND endpoint labels resolving to the
    link's source/target node ids in either order. Labels may carry
    parenthetical qualifiers, so resolution compares lowercase tokens with a
    prefix match against norm_label-style token lists (exact token equality
    wins when several nodes share a prefix).
 3. Annotate each matched link with validation_status = "<verdict>".
    confidence/sign/relation and all other fields are never modified.
 4. Rewrite the graph file in place (derived artifact). --dry-run prints the
    summary without writing.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_CLAIMS = Path("analysis/claims/claims.json")
DEFAULT_VERDICTS = Path("analysis/claims/verdicts.json")

PAREN_RE = re.compile(r"\([^)]*\)")
NON_WORD_RE = re.compile(r"[^\w\s]+")
WHITESPACE_RE = re.compile(r"\s+")

REVIEWABLE_VERDICTS = {"CONFIRMED", "EXTENDED", "REFUTED", "MIXED", "NO_EVIDENCE_FOUND"}


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
    """Resolve a claim label to candidate node ids.

    Exact token-sequence equality takes precedence; otherwise fall back to a
    lowercase prefix match on the indexed token lists so labels with (or
    without) parenthetical qualifiers still resolve.
    """
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


def apply_verdicts(graph, claims, verdict_map):
    """Annotate graph['links'] in place; return a match report dict."""
    index = build_label_index(graph["nodes"])
    edges = sorted(
        (c for c in claims if c.get("kind") == "edge"), key=lambda c: c["id"]
    )
    matched_by_verdict = Counter()
    links_by_verdict = Counter()
    ambiguous = []
    unmatched = []
    annotated = 0

    for claim in edges:
        claim_id = claim["id"]
        verdict = verdict_map.get(claim_id)
        if verdict is None or verdict == "UNREVIEWED":
            continue
        subject_ids = resolve_label_ids(claim.get("subject", ""), index)
        object_ids = resolve_label_ids(claim.get("object", ""), index)
        hits = [
            link
            for link in graph["links"]
            if link.get("relation") == claim.get("predicate")
            and (
                (link.get("source") in subject_ids and link.get("target") in object_ids)
                or (link.get("source") in object_ids and link.get("target") in subject_ids)
            )
        ]
        if not hits:
            unmatched.append(claim_id)
            continue
        matched_by_verdict[verdict] += 1
        links_by_verdict[verdict] += len(hits)
        annotated += len(hits)
        if len(hits) > 1:
            ambiguous.append({"claim_id": claim_id, "matches": len(hits)})
        for link in hits:
            link["validation_status"] = verdict

    distinct = sum(
        1 for link in graph["links"] if "validation_status" in link
    )
    return {
        "reviewed_claims": sum(matched_by_verdict.values()) + len(unmatched),
        "matched_claims": sum(matched_by_verdict.values()),
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "links_annotated": annotated,
        "distinct_links": distinct,
        "matched_claims_by_verdict": dict(matched_by_verdict),
        "links_annotated_by_verdict": dict(links_by_verdict),
    }


def format_summary(report):
    lines = [
        "Edge-claim verdict propagation",
        f"  reviewed edge claims : {report['reviewed_claims']}",
        f"  matched claims       : {report['matched_claims']}",
        f"  unmatched claims     : {len(report['unmatched'])}",
        f"  link annotations     : {report['links_annotated']} "
        f"({report['distinct_links']} distinct links)",
        f"  ambiguous claims     : {len(report['ambiguous'])}",
    ]
    for item in report["ambiguous"]:
        lines.append(f"    {item['claim_id']}: {item['matches']} links")
    verdicts = sorted(
        set(report["matched_claims_by_verdict"]) | set(report["links_annotated_by_verdict"])
    )
    if verdicts:
        lines.append("  by verdict (claims matched / links annotated):")
    for verdict in verdicts:
        lines.append(
            f"    {verdict:<18} "
            f"{report['matched_claims_by_verdict'].get(verdict, 0)} / "
            f"{report['links_annotated_by_verdict'].get(verdict, 0)}"
        )
    if report["unmatched"]:
        lines.append("  unmatched claim ids:")
        for claim_id in report["unmatched"]:
            lines.append(f"    {claim_id}")
    else:
        lines.append("  unmatched claim ids: (none)")
    return "\n".join(lines)


def load_json(path):
    with open(path) as handle:
        return json.load(handle)


def verdict_list_to_map(verdict_entries):
    return {
        entry["claim_id"]: entry["verdict"]
        for entry in verdict_entries
        if isinstance(entry, dict) and "claim_id" in entry and "verdict" in entry
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Apply literature verdicts to graph edges as validation_status"
    )
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH,
                        help="graph JSON to annotate in place")
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS,
                        help="extracted claims JSON")
    parser.add_argument("--verdicts", type=Path, default=DEFAULT_VERDICTS,
                        help="verdict entries JSON (list of {claim_id, verdict})")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the summary without writing the graph")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    graph = load_json(args.graph)
    claims = load_json(args.claims)
    verdict_map = verdict_list_to_map(load_json(args.verdicts))
    report = apply_verdicts(graph, claims, verdict_map)
    print(format_summary(report))
    if args.dry_run:
        print("dry run: graph file left untouched")
        return 0
    with open(args.graph, "w") as handle:
        json.dump(graph, handle, indent=2, ensure_ascii=False)
    print(f"wrote {args.graph}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
