#!/usr/bin/env python3
"""Apply curated edge-direction corrections to graphify-out/graph_v2.json.

Reads analysis/claims/edge_reversals.yaml. Each entry names a link as it is
stored (source, target, relation) whose relation describes the target acting
on the source. The link's endpoints are swapped and its relation kept, so the
relation's sign (build_graph_v2.relation_sign) reads along the corrected
direction; an entry's optional `sign` overrides it where the corrected
target's state has inverted polarity (barrier nodes model leak). Corrected
links record provenance:

    {direction_corrected: true, direction_quote, direction_ref,
     sign_before_reversal (only when the sign changed)}

validation_status, confidence and every other field are kept: a direction
fix is not new evidence. When the corrected link already exists with the
same sign, the stored one is dropped as a duplicate.

The tool is idempotent: an entry whose link only exists in the corrected
direction is skipped. An entry matching no link in either direction is an
error, so the spec cannot silently drift from the graph.

find_direction_suspects() is the audit heuristic behind the spec: signed
links whose target looks like an intervention, tool or injury model while
the source does not.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_REVERSALS = Path("analysis/claims/edge_reversals.yaml")

REQUIRED_FIELDS = ("source", "target", "relation", "source_file", "quote")

INTERVENTION_LABEL = re.compile(
    r"shRNA|\bAAV|knockout|knockdown|\bmodel\b|stimulation|enrichment|inhibitor|"
    r"antagonist|antibod|blocker|blockade|DREADD|optogenetic|gene therapy|-Fc\b|"
    r"rescue|sequestering",
    re.IGNORECASE,
)


@dataclass
class ReversalSummary:
    reversed: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    dropped_duplicates: list = field(default_factory=list)
    sign_overrides: int = 0

    def render(self) -> str:
        return (
            f"edge reversals: reversed={len(self.reversed)} "
            f"skipped_applied={len(self.skipped)} "
            f"dropped_duplicates={len(self.dropped_duplicates)} "
            f"sign_overrides={self.sign_overrides}"
        )


def _validate_entry(entry, position, node_ids):
    missing = [f for f in REQUIRED_FIELDS if entry.get(f) is None]
    if missing:
        raise ValueError(f"reversal #{position} missing fields: {', '.join(missing)}")
    if "sign" in entry and int(entry["sign"]) not in (-1, 1):
        raise ValueError(f"reversal #{position}: sign override must be -1 or 1")
    if len(str(entry["quote"])) > 400:
        raise ValueError(f"reversal #{position} quote exceeds 400 chars")
    unknown = [nid for nid in (entry["source"], entry["target"]) if nid not in node_ids]
    if unknown:
        raise ValueError(f"reversal #{position}: unknown node(s) {', '.join(unknown)}")


def _key(link):
    return link["source"], link["target"], link["relation"]


def apply_reversals(graph, reversals):
    """Return (new_graph, summary); the input graph is not modified."""
    links = [dict(l) for l in graph["links"]]
    node_ids = {n["id"] for n in graph["nodes"]}
    summary = ReversalSummary()
    dropped = set()
    for position, entry in enumerate(reversals):
        _validate_entry(entry, position, node_ids)
        s, t, rel = entry["source"], entry["target"], entry["relation"]
        label = f"{s} -{rel}-> {t}"
        live = [i for i in range(len(links)) if i not in dropped]
        stored = [i for i in live if _key(links[i]) == (s, t, rel)]
        corrected = [i for i in live if _key(links[i]) == (t, s, rel)]
        if len(stored) > 1:
            raise ValueError(f"reversal #{position}: {len(stored)} links match {label}")
        if not stored:
            if corrected:
                summary.skipped.append(label)
                continue
            raise ValueError(f"reversal #{position}: no link {label} in either direction")
        idx = stored[0]
        link = links[idx]
        sign = int(entry.get("sign", link.get("sign", 0)))
        if sign == 0:
            raise ValueError(f"reversal #{position}: {label} is unsigned")
        if corrected:
            if any(links[j].get("sign") == sign for j in corrected):
                dropped.add(idx)
                summary.dropped_duplicates.append(label)
                continue
            raise ValueError(
                f"reversal #{position}: corrected link for {label} exists with another sign"
            )
        note = entry.get("note")
        new_link = {
            **link,
            "source": t,
            "target": s,
            "sign": sign,
            "direction_corrected": True,
            "direction_quote": entry["quote"],
            "direction_ref": f"{entry['source_file']} | {note}" if note else entry["source_file"],
        }
        if sign != link.get("sign"):
            new_link["sign_before_reversal"] = link.get("sign")
            summary.sign_overrides += 1
        links[idx] = new_link
        summary.reversed.append(label)
    kept = [l for i, l in enumerate(links) if i not in dropped]
    return {**graph, "links": kept}, summary


def is_intervention_like(node):
    return node.get("entity_type") == "drug" or bool(
        INTERVENTION_LABEL.search(node.get("label") or "")
    )


def find_direction_suspects(graph):
    """Signed causal links pointing from a mechanism node into an
    intervention/tool/model node: the usual shape of a reversed extraction."""
    by_id = {n["id"]: n for n in graph["nodes"]}
    return [
        link
        for link in graph["links"]
        if link.get("sign", 0) != 0
        and link["relation"] != "rationale_for"
        and is_intervention_like(by_id[link["target"]])
        and not is_intervention_like(by_id[link["source"]])
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--reversals", type=Path, default=DEFAULT_REVERSALS)
    args = parser.parse_args(argv)

    graph = json.loads(args.graph.read_text())
    reversals = yaml.safe_load(args.reversals.read_text()) or []
    new_graph, summary = apply_reversals(graph, reversals)
    if summary.reversed or summary.dropped_duplicates:
        args.graph.write_text(json.dumps(new_graph, indent=2, ensure_ascii=False) + "\n")
    print(summary.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
