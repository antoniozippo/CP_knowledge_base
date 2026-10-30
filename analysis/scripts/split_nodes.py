#!/usr/bin/env python3
"""Apply curated node splits to graphify-out/graph_v2.json.

Reads analysis/claims/node_splits.yaml. For each split, a new node is made
from a copy of the source node (fields in `new_node` override; merged_from
is cleared and split_from / split_source_ref record provenance), and every
link between the source and an id in `move_with` is re-pointed to the new
node, in whichever direction it runs. Tiers of both nodes are recomputed
from their new degrees with build_graph_v2's thresholds.

The tool is idempotent: a split whose new node already exists is skipped.
A listed endpoint with no link to the source is an error, so the spec
cannot silently drift from the graph.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_graph_v2 import assign_tier, compute_degrees  # noqa: E402

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_SPLITS = Path("analysis/claims/node_splits.yaml")


@dataclass
class SplitSummary:
    applied: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    moved_links: int = 0

    def render(self) -> str:
        return (
            f"node splits: applied={len(self.applied)} skipped_existing={len(self.skipped)} "
            f"moved_links={self.moved_links}"
        )


def apply_splits(graph, splits):
    """Return (new_graph, summary); the input graph is not modified."""
    nodes = [dict(n) for n in graph["nodes"]]
    links = [dict(l) for l in graph["links"]]
    by_id = {n["id"]: n for n in nodes}
    summary = SplitSummary()
    for position, split in enumerate(splits):
        source_id = split["source"]
        new_fields = split["new_node"]
        new_id = new_fields["id"]
        if source_id not in by_id:
            raise ValueError(f"split #{position}: unknown source node '{source_id}'")
        if new_id in by_id:
            summary.skipped.append(new_id)
            continue
        move_with = set(split["move_with"])
        linked = {
            l["target"] if l["source"] == source_id else l["source"]
            for l in links
            if source_id in (l["source"], l["target"])
        }
        missing = sorted(move_with - linked)
        if missing:
            raise ValueError(
                f"split #{position}: no link between '{source_id}' and: {', '.join(missing)}"
            )
        new_node = {**by_id[source_id], **new_fields}
        # graph convention (and crawler exact-match key): lowercased label
        new_node["norm_label"] = new_node["label"].lower()
        new_node["merged_from"] = []
        new_node["split_from"] = source_id
        new_node["split_source_ref"] = split.get("source_ref")
        nodes.append(new_node)
        by_id[new_id] = new_node
        for link in links:
            if link["source"] == source_id and link["target"] in move_with:
                link["source"] = new_id
                summary.moved_links += 1
            elif link["target"] == source_id and link["source"] in move_with:
                link["target"] = new_id
                summary.moved_links += 1
        degrees = compute_degrees(nodes, links)
        for nid in (source_id, new_id):
            by_id[nid]["tier"] = assign_tier(degrees[nid])
        summary.applied.append(new_id)
    return {**graph, "nodes": nodes, "links": links}, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--splits", type=Path, default=DEFAULT_SPLITS)
    args = parser.parse_args(argv)

    graph = json.loads(args.graph.read_text())
    splits = yaml.safe_load(args.splits.read_text()) or []
    new_graph, summary = apply_splits(graph, splits)
    if summary.applied:
        args.graph.write_text(json.dumps(new_graph, indent=2, ensure_ascii=False) + "\n")
    print(summary.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
