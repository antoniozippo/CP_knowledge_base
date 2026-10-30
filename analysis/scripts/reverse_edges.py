#!/usr/bin/env python3
"""Apply curated edge-direction corrections to graphify-out/graph_v2.json.

build_graph_v2.py reads every relation's sign along the stored
source->target direction. Some active-voice edges were extracted with
endpoints swapped: the relation describes an action of the stored TARGET
on the stored SOURCE (e.g. "ROCK -inhibits-> Fasudil" for "fasudil
inhibits ROCK"), so in simulation the source drives the drug/tool/regulator
instead of being driven by it. Passive "*_by" relations are already zeroed
there; these are not detectable from the relation string alone.

Reads curated entries from analysis/claims/edge_reversals.yaml. Each entry
names one existing link by its stored (source, target, relation, sign) and
an action:

    reverse     swap source and target; relation and sign are kept
    neutralize  set sign to 0 (the corrected orientation is already encoded
                by another link, so reversing would duplicate the pair)

Corrected links gain provenance keys and keep everything else (confidence,
validation_status, source_file, ...):

    {correction: "reversed" | "neutralized_duplicate",
     original_source, original_target, original_sign,
     correction_quote, correction_source_ref}

The tool is idempotent: an entry whose link already carries its correction
is counted as already_applied. Any entry that matches no link (corrected or
not), matches several, disagrees on sign, or whose reversal would duplicate
an existing signed pair raises ValueError and the graph is left untouched.
Run it after add_closure_edges.py and before simulator/build_cards.py.
"""

import argparse
import copy
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_REVERSALS = Path("analysis/claims/edge_reversals.yaml")

REQUIRED_FIELDS = ("source", "target", "relation", "sign", "action", "quote", "source_file")
ACTIONS = {"reverse": "reversed", "neutralize": "neutralized_duplicate"}
QUOTE_MAX_CHARS = 400


@dataclass
class ReversalSummary:
    proposed: int = 0
    reversed: int = 0
    neutralized: int = 0
    already_applied: int = 0
    errors: list = field(default_factory=list)

    def render(self) -> str:
        return (
            f"edge reversals: proposed={self.proposed} reversed={self.reversed} "
            f"neutralized={self.neutralized} already_applied={self.already_applied}"
        )


def _validate_entry(entry, position):
    missing = [f for f in REQUIRED_FIELDS if entry.get(f) is None]
    if missing:
        raise ValueError(f"entry #{position} missing fields: {', '.join(missing)}")
    if entry["action"] not in ACTIONS:
        raise ValueError(
            f"entry #{position} action must be one of {', '.join(sorted(ACTIONS))}"
        )
    if int(entry["sign"]) not in (-1, 1):
        raise ValueError(f"entry #{position} sign must be -1 or 1 (only signed links are corrected)")
    if entry["source"] == entry["target"]:
        raise ValueError(f"entry #{position} source and target are identical")
    if len(str(entry["quote"])) > QUOTE_MAX_CHARS:
        raise ValueError(f"entry #{position} quote exceeds {QUOTE_MAX_CHARS} chars")


def _source_ref(entry):
    location = entry.get("source_location")
    return f"{entry['source_file']}:{location}" if location else entry["source_file"]


def _describe(entry):
    return f"{entry['source']} -{entry['relation']}({int(entry['sign']):+d})-> {entry['target']}"


def _is_applied(link, entry):
    """True when `link` already carries this entry's correction."""
    if link.get("relation") != entry["relation"]:
        return False
    if link.get("correction") != ACTIONS[entry["action"]]:
        return False
    return (
        link.get("original_source") == entry["source"]
        and link.get("original_target") == entry["target"]
    )


def apply_edge_reversals(graph, entries):
    """Pure core: return (new_graph, ReversalSummary); raises ValueError on any
    unresolvable entry (graph left untouched in that case)."""
    new_graph = copy.deepcopy(graph)
    links = new_graph["links"]
    summary = ReversalSummary(proposed=len(entries))
    node_ids = {node["id"] for node in new_graph.get("nodes", [])}

    keyed = [
        (i, l) for i, l in enumerate(links)
        if "correction" not in l
    ]
    errors = []
    plan = []
    claimed = set()
    for position, entry in enumerate(entries):
        _validate_entry(entry, position)
        for endpoint in (entry["source"], entry["target"]):
            if endpoint not in node_ids:
                errors.append(f"#{position} {_describe(entry)}: unknown node {endpoint}")
        if any(_is_applied(l, entry) for l in links):
            summary.already_applied += 1
            continue
        hits = [
            (i, l) for i, l in keyed
            if l["source"] == entry["source"]
            and l["target"] == entry["target"]
            and l.get("relation") == entry["relation"]
        ]
        if not hits:
            errors.append(f"#{position} {_describe(entry)}: no matching link")
            continue
        if len(hits) > 1:
            errors.append(f"#{position} {_describe(entry)}: {len(hits)} matching links (ambiguous)")
            continue
        index, link = hits[0]
        if int(link.get("sign") or 0) != int(entry["sign"]):
            errors.append(
                f"#{position} {_describe(entry)}: stored sign is {link.get('sign')}"
            )
            continue
        if index in claimed:
            errors.append(f"#{position} {_describe(entry)}: link already claimed by another entry")
            continue
        claimed.add(index)
        plan.append((index, entry))

    signed_pairs = {
        (l["source"], l["target"])
        for i, l in enumerate(links)
        if int(l.get("sign") or 0) != 0 and i not in claimed
    }
    for index, entry in plan:
        if entry["action"] != "reverse":
            continue
        flipped = (entry["target"], entry["source"])
        if flipped in signed_pairs:
            errors.append(
                f"{_describe(entry)}: reversed pair already has a signed link; "
                "use action: neutralize"
            )
        signed_pairs.add(flipped)

    if errors:
        summary.errors = errors
        raise ValueError(f"edge reversal errors ({len(errors)}): " + "; ".join(errors))

    for index, entry in plan:
        link = links[index]
        link["correction"] = ACTIONS[entry["action"]]
        link["original_source"] = entry["source"]
        link["original_target"] = entry["target"]
        link["original_sign"] = int(entry["sign"])
        link["correction_quote"] = entry["quote"]
        link["correction_source_ref"] = _source_ref(entry)
        if entry["action"] == "reverse":
            link["source"], link["target"] = entry["target"], entry["source"]
            summary.reversed += 1
        else:
            link["sign"] = 0
            summary.neutralized += 1
    return new_graph, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--reversals", type=Path, default=DEFAULT_REVERSALS)
    parser.add_argument(
        "--check", action="store_true",
        help="exit 1 without writing when any entry is not yet applied",
    )
    args = parser.parse_args(argv)

    graph = json.loads(args.graph.read_text())
    entries = yaml.safe_load(args.reversals.read_text()) or []
    try:
        new_graph, summary = apply_edge_reversals(graph, entries)
    except ValueError as exc:
        raise SystemExit(str(exc))
    print(summary.render())
    pending = summary.reversed + summary.neutralized
    if args.check:
        return 1 if pending else 0
    if pending:
        args.graph.write_text(json.dumps(new_graph, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
