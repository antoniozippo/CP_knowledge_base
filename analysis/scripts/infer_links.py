#!/usr/bin/env python3
"""Infer novel-edge candidates from graphify-out/graph_v2.json structure.

Two candidate classes are produced into analysis/claims/link_candidates.json:

 1. Co-occurrence link prediction (evidence_basis="structure"): Adamic-Adar +
    Jaccard over neighbor sets of the UNDIRECTED projection. Only node pairs
    NOT currently linked AND living in different communities are considered
    (intra-community density is already covered by clustering). Pairs whose
    labels are near-duplicates after parenthetical stripping are excluded.
    Kept: top N by combined rank (sum of Adamic-Adar rank and Jaccard rank).

 2. Signed triad closure (evidence_basis="triad"): for directed 2-paths
    a -> b -> c over sign != 0 links where a and c share NO link in either
    direction, propose edge a<->c with inferred_sign = product of signs
    (composition rule). Supports are grouped per unordered endpoint pair;
    when paths disagree on the product, the majority product wins
    (ties: higher summed confidence, then positive sign). confidence =
    min(link confidence_score) across supporting paths. Kept: top N by
    (distinct supporting intermediates desc, min-confidence desc).

Output is fully deterministic: no timestamps, canonical endpoint order
(id-sorted), stable ranking tie-breakers, sequential LC-#### / TC-#### ids.

Usage:
  python analysis/scripts/infer_links.py [--graph PATH] [--output PATH]
                                         [--top-cooccur N] [--top-triad N]
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_OUTPUT = Path("analysis/claims/link_candidates.json")

PAREN_RE = re.compile(r"\([^)]*\)")
NON_WORD_RE = re.compile(r"[^\w\s]+")
WHITESPACE_RE = re.compile(r"\s+")

SHARED_NEIGHBOR_CAP = 8
FLOAT_DIGITS = 6


def normalize_label(label):
    """Lowercase paren-free label used for near-duplicate detection."""
    text = PAREN_RE.sub(" ", str(label).lower())
    text = NON_WORD_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def load_graph(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_adjacency(nodes, links):
    """Undirected projection: node id -> set of neighbor ids."""
    adjacency = {node["id"]: set() for node in nodes}
    for link in links:
        src, dst = link["source"], link["target"]
        if src != dst and src in adjacency and dst in adjacency:
            adjacency[src].add(dst)
            adjacency[dst].add(src)
    return adjacency


def _round(value):
    return round(value, FLOAT_DIGITS)


def infer_cooccurrence_candidates(nodes, links, top_n=60):
    """Score all eligible unlinked cross-community pairs (Adamic-Adar, Jaccard)."""
    adjacency = build_adjacency(nodes, links)
    by_id = {node["id"]: node for node in nodes}
    existing = {frozenset((link["source"], link["target"])) for link in links}
    normalized = {
        nid: normalize_label(by_id[nid].get("label") or "")
        for nid in adjacency
    }

    scored = []
    ordered_ids = sorted(adjacency)
    for pos, node_a in enumerate(ordered_ids):
        neigh_a = adjacency[node_a]
        for node_b in ordered_ids[pos + 1:]:
            if frozenset((node_a, node_b)) in existing:
                continue
            info_a, info_b = by_id[node_a], by_id[node_b]
            if info_a.get("community") == info_b.get("community"):
                continue
            if normalized[node_a] == normalized[node_b]:
                continue
            common = neigh_a & adjacency[node_b]
            # networkx convention: degree-1 common neighbors contribute 1/log(1).
            adamic_adar = sum(
                1.0 / math.log(len(adjacency[mid]))
                for mid in common
                if len(adjacency[mid]) > 1
            )
            union = neigh_a | adjacency[node_b]
            jaccard = len(common) / len(union) if union else 0.0
            scored.append((node_a, node_b, adamic_adar, jaccard, common))

    rank_aa = {
        (row[0], row[1]): idx
        for idx, row in enumerate(
            sorted(scored, key=lambda r: (-r[2], r[0], r[1]))
        )
    }
    rank_jac = {
        (row[0], row[1]): idx
        for idx, row in enumerate(
            sorted(scored, key=lambda r: (-r[3], r[0], r[1]))
        )
    }
    scored.sort(key=lambda r: (rank_aa[(r[0], r[1])] + rank_jac[(r[0], r[1])],
                               r[0], r[1]))

    candidates = []
    for node_a, node_b, adamic_adar, jaccard, common in scored[:top_n]:
        info_a, info_b = by_id[node_a], by_id[node_b]
        ranked_shared = sorted(common, key=lambda nid: (len(adjacency[nid]),
                                                        normalized[nid]))
        candidates.append({
            "node_a": node_a,
            "node_b": node_b,
            "label_a": info_a["label"],
            "label_b": info_b["label"],
            "community_a": info_a.get("community"),
            "community_b": info_b.get("community"),
            "entity_type_a": info_a.get("entity_type"),
            "entity_type_b": info_b.get("entity_type"),
            "compartment_a": info_a.get("compartment"),
            "compartment_b": info_b.get("compartment"),
            "tier_a": info_a.get("tier"),
            "tier_b": info_b.get("tier"),
            "adamic_adar": _round(adamic_adar),
            "jaccard": _round(jaccard),
            "shared_neighbors": [by_id[nid]["label"]
                                 for nid in ranked_shared[:SHARED_NEIGHBOR_CAP]],
            "evidence_basis": "structure",
        })
    return candidates


def infer_triad_candidates(nodes, links, top_n=40):
    """Close signed directed 2-paths a->b->c whose endpoints are unlinked."""
    by_id = {node["id"]: node for node in nodes}
    signed_out = defaultdict(list)
    for link in links:
        sign = link.get("sign", 0)
        if sign == 0:
            continue
        signed_out[link["source"]].append(
            (link["target"], int(sign),
             float(link.get("confidence_score", 1.0)))
        )
    existing = {frozenset((link["source"], link["target"])) for link in links}
    normalized = {
        node["id"]: normalize_label(node.get("label") or "") for node in nodes
    }

    supports = defaultdict(list)
    for src in sorted(signed_out):
        for mid, s_first, conf_first in sorted(signed_out[src]):
            for dst, s_second, conf_second in sorted(signed_out[mid]):
                if dst == src or frozenset((src, dst)) in existing:
                    continue
                lo, hi = (src, dst) if src <= dst else (dst, src)
                if normalized[lo] == normalized[hi]:
                    continue
                s1, s2 = ((s_first, s_second) if lo == src
                          else (s_second, s_first))
                supports[(lo, hi)].append({
                    "via": mid,
                    "s1": s1,
                    "s2": s2,
                    "conf": min(conf_first, conf_second),
                    "product": s_first * s_second,
                })

    aggregated = []
    for (lo, hi) in sorted(supports):
        paths = supports[(lo, hi)]
        tally = defaultdict(lambda: [0, 0.0])
        for path in paths:
            tally[path["product"]][0] += 1
            tally[path["product"]][1] += path["conf"]
        winning_sign = max(
            tally,
            key=lambda product: (tally[product][0], tally[product][1],
                                 product),
        )
        chosen = sorted(
            (path for path in paths if path["product"] == winning_sign),
            key=lambda p: (p["via"], p["s1"], p["s2"]),
        )
        distinct_mids = {p["via"] for p in chosen}
        aggregated.append({
            "node_a": lo,
            "node_c": hi,
            "label_a": by_id[lo]["label"],
            "label_c": by_id[hi]["label"],
            "inferred_sign": winning_sign,
            "support_paths": [
                {"via": p["via"], "s1": p["s1"], "s2": p["s2"]}
                for p in chosen[:5]
            ],
            "n_support": len(distinct_mids),
            "min_confidence": _round(min(p["conf"] for p in chosen)),
            "evidence_basis": "triad",
        })

    aggregated.sort(key=lambda r: (-r["n_support"], -r["min_confidence"],
                                   r["node_a"], r["node_c"],
                                   -r["inferred_sign"]))
    return aggregated[:top_n]


def build_output(graph, top_cooccur, top_triad, source_graph):
    cooccur = infer_cooccurrence_candidates(
        graph["nodes"], graph["links"], top_n=top_cooccur
    )
    triads = infer_triad_candidates(
        graph["nodes"], graph["links"], top_n=top_triad
    )
    for idx, record in enumerate(cooccur, start=1):
        record_final = {"id": f"LC-{idx:04d}"}
        record_final.update(record)
        record.clear()
        record.update(record_final)
    for idx, record in enumerate(triads, start=1):
        record_final = {"id": f"TC-{idx:04d}"}
        record_final.update(record)
        record.clear()
        record.update(record_final)

    return {
        "source_graph": source_graph,
        "built_from_commit": graph.get("built_at_commit"),
        "cooccurrence_candidates": cooccur,
        "triad_candidates": triads,
        "summary": {
            "n_nodes": len(graph["nodes"]),
            "n_links": len(graph["links"]),
            "n_cooccurrence_candidates": len(cooccur),
            "n_triad_candidates": len(triads),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-cooccur", type=int, default=60)
    parser.add_argument("--top-triad", type=int, default=40)
    args = parser.parse_args(argv)

    graph = load_graph(args.graph)
    output = build_output(graph, args.top_cooccur, args.top_triad,
                          str(args.graph))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    summary = output["summary"]
    print(f"Graph: {summary['n_nodes']} nodes, {summary['n_links']} links "
          f"({args.graph})")
    print(f"Co-occurrence candidates: {summary['n_cooccurrence_candidates']}")
    print(f"Signed-triad candidates: {summary['n_triad_candidates']}")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
