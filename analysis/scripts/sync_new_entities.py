"""Sync document-type entities from the raw graphify graph into graph_v2.

Handles two drift sources after a graphify refresh:
1. New document nodes absent from graph_v2 — EXCLUDING label-collisions that
   were deliberately merged away during v2 deduplication (merge-sources).
2. Raw links touching newly-synced nodes — imported through the same canonical
   map used by build_graph_v2 (merge-sources redirect to their survivors),
   skipping duplicates and self-loops, with signs assigned by relation_sign.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_graph_v2 import (
    assign_tier,
    build_canonical_map,
    classify_compartment,
    classify_entity_type,
    normalize_label,
    redirect_links,
    sign_edges,
)


def find_missing_nodes(raw_nodes, v2_nodes):
    """Document nodes absent from v2 by id AND whose normalized label does not
    collide with an existing v2 node (those are merge-sources of survivors)."""
    v2_ids = {n["id"] for n in v2_nodes}
    v2_norms = {normalize_label(n["label"]) for n in v2_nodes}
    missing, skipped_merge_sources = [], []
    for n in raw_nodes:
        if n.get("file_type") != "document" or n["id"] in v2_ids:
            continue
        if normalize_label(n["label"]) in v2_norms:
            skipped_merge_sources.append(n["id"])
        else:
            missing.append(n)
    return missing, skipped_merge_sources


def enrich(raw_node, degree=0):
    node = dict(raw_node)
    label = raw_node["label"]
    node["entity_type"] = classify_entity_type(label)
    node["compartment"] = classify_compartment(label)
    node["tier"] = assign_tier(degree)
    node.setdefault("norm_label", label.lower())
    return node


def _existing_triples(links):
    return {(l.get("source"), l.get("target"), l.get("relation", "")) for l in links}


def import_links(raw_links, v2_links, canon, added_canonical_ids):
    """Redirect raw links through the canonical map; keep those touching a
    newly-added node (by canonical id), resolving to distinct existing
    endpoints and not already present (by source/target/relation triple)."""
    candidates = [
        l for l in raw_links
        if canon.get(l.get("source"), l.get("source")) in added_canonical_ids
        or canon.get(l.get("target"), l.get("target")) in added_canonical_ids
    ]
    redirected, _, _ = redirect_links([dict(l) for l in candidates], canon)
    seen = _existing_triples(v2_links)
    fresh = []
    signed, flagged = sign_edges([l for l in redirected])
    for l in signed:
        triple = (l["source"], l["target"], l.get("relation", ""))
        if triple in seen:
            continue
        seen.add(triple)
        fresh.append(l)
    return fresh, sorted(flagged)


def sync(graph_v2_path, raw_graph_path, with_links=False):
    v2 = json.loads(Path(graph_v2_path).read_text())
    raw = json.loads(Path(raw_graph_path).read_text())
    missing, skipped_merge_sources = find_missing_nodes(raw["nodes"], v2["nodes"])

    added_nodes = [enrich(n) for n in missing]
    v2["nodes"].extend(added_nodes)

    added_link_count = 0
    link_flagged = []
    if with_links and added_nodes:
        # include merge-source documents in the map so their links redirect onto survivors
        v2_ids = {n["id"] for n in v2["nodes"]}
        extra_docs = [n for n in raw["nodes"]
                      if n.get("file_type") == "document" and n["id"] not in v2_ids]
        canon = build_canonical_map(v2["nodes"] + extra_docs)
        added_canonical_ids = {canon.get(n["id"], n["id"]) for n in added_nodes}
        fresh, link_flagged = import_links(
            raw["links"], v2["links"], canon, added_canonical_ids
        )
        # recompute tier for new nodes using final degrees
        deg = {}
        for l in v2["links"] + fresh:
            deg[l["source"]] = deg.get(l["source"], 0) + 1
            deg[l["target"]] = deg.get(l["target"], 0) + 1
        for n in added_nodes:
            n["tier"] = assign_tier(deg.get(n["id"], 0))
        v2["links"].extend(fresh)
        added_link_count = len(fresh)

    summary = {
        "added_nodes": len(added_nodes),
        "added_node_ids": [n["id"] for n in added_nodes],
        "skipped_merge_sources": len(skipped_merge_sources),
        "added_links": added_link_count,
        "passive_flagged_relations": link_flagged,
        "nodes_total": len(v2["nodes"]),
        "links_total": len(v2["links"]),
    }
    Path(graph_v2_path).write_text(json.dumps(v2, indent=2, ensure_ascii=False))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-v2", default="graphify-out/graph_v2.json")
    parser.add_argument("--raw-graph", default="graphify-out/graph.json")
    parser.add_argument("--with-links", action="store_true",
                        help="also import raw links touching synced nodes")
    args = parser.parse_args(argv)
    summary = sync(args.graph_v2, args.raw_graph, with_links=args.with_links)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
