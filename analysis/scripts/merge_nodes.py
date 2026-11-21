#!/usr/bin/env python3
"""Apply curated node merges to graphify-out/graph_v2.json.

Reads analysis/claims/node_merges.yaml. Each entry folds the nodes listed in
`absorbs` into `survivor`: every link to or from an absorbed node is re-pointed
to the survivor, and the absorbed nodes are removed. The survivor keeps its id,
label and type, records the absorbed ids in merged_from, and has its tier
recomputed with build_graph_v2's thresholds from its curated links (crawled
links never set a curated node's tier).

Links that become identical (same source, target, relation and sign) are folded
into one: a curated link wins over a crawled one, and the crawler evidence of
both is kept, one entry per PMID (a crawled link's evidence list already holds
its own paper). The folded link takes the earlier position. A link between the
survivor and an absorbed node would become a self-loop and is dropped.

crawler/conflicts.yaml points at links by position, so the tool refuses to
remove a link at or before the last position the conflict log names.

The tool is idempotent: an entry whose absorbed nodes are already gone is
skipped. Run it again after any re-merge of the crawl that starts from an
older graph.
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
DEFAULT_MERGES = Path("analysis/claims/node_merges.yaml")
DEFAULT_CONFLICTS = Path("crawler/conflicts.yaml")


@dataclass
class MergeSummary:
    applied: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    moved_links: int = 0
    folded_links: int = 0
    dropped_self_loops: int = 0

    def render(self) -> str:
        return (
            f"node merges: applied={len(self.applied)} skipped_done={len(self.skipped)} "
            f"moved_links={self.moved_links} folded_duplicates={self.folded_links} "
            f"dropped_self_loops={self.dropped_self_loops}"
        )


def is_crawled(link):
    return link.get("origin") == "auto_crawled"


def own_evidence(link):
    """A crawled link's evidence list, with its own paper first if the list lacks it."""
    evidence = [dict(e) for e in link.get("crawler_evidence", [])]
    if is_crawled(link) and link.get("source_pmid") and \
            str(link["source_pmid"]) not in {str(e.get("pmid")) for e in evidence}:
        evidence.insert(0, {"pmid": str(link["source_pmid"]), "quote": link.get("quote", ""),
                            "predicate": link.get("relation"), "sign": link.get("sign")})
    return evidence


def fold(kept, other):
    """`kept` with `other` folded in: the curated link wins, evidence is unioned by PMID."""
    winner, loser = (other, kept) if is_crawled(kept) and not is_crawled(other) else (kept, other)
    merged = dict(winner)
    evidence = own_evidence(winner) if is_crawled(winner) else [dict(e) for e in winner.get("crawler_evidence", [])]
    seen = {str(e.get("pmid")) for e in evidence}
    for e in own_evidence(loser):
        if str(e.get("pmid")) not in seen:
            evidence.append(e)
            seen.add(str(e.get("pmid")))
    if evidence:
        merged["crawler_evidence"] = evidence
    return merged


def apply_merges(graph, merges, protect_through=-1):
    """Return (new_graph, summary); the input graph is not modified. No link at a position
    <= protect_through may be removed."""
    nodes = [dict(n) for n in graph["nodes"]]
    links = [dict(l) for l in graph["links"]]
    by_id = {n["id"]: n for n in nodes}
    summary = MergeSummary()
    canon = {}
    for position, merge in enumerate(merges):
        survivor = merge["survivor"]
        if survivor not in by_id:
            raise ValueError(f"merge #{position}: unknown survivor '{survivor}'")
        present = [a for a in merge["absorbs"] if a in by_id and a != survivor]
        if not present:
            summary.skipped.append(survivor)
            continue
        for a in present:
            canon[a] = survivor
        merged_from = list(by_id[survivor].get("merged_from") or [])
        by_id[survivor]["merged_from"] = merged_from + [a for a in present if a not in merged_from]
        summary.applied.append(survivor)
    if not canon:
        return {**graph, "nodes": nodes, "links": links}, summary

    survivors = set(canon.values())
    keep = []                       # (position, link) after re-pointing
    for position, link in enumerate(links):
        s0, t0 = link["source"], link["target"]
        s, t = canon.get(s0, s0), canon.get(t0, t0)
        if (s, t) != (s0, t0):
            summary.moved_links += 1
            if s == t:
                summary.dropped_self_loops += 1
                if position <= protect_through:
                    raise ValueError(f"merge would drop link #{position}, which the conflict log names")
                continue
            link = {**link, "source": s, "target": t}
        keep.append((position, link))

    out, slot = [], {}
    for position, link in keep:
        touches = link["source"] in survivors or link["target"] in survivors
        key = (link["source"], link["target"], link.get("relation"), link.get("sign"))
        if touches and key in slot:
            if position <= protect_through:
                raise ValueError(f"merge would fold away link #{position}, which the conflict log names")
            out[slot[key]] = fold(out[slot[key]], link)
            summary.folded_links += 1
            continue
        if touches:
            slot[key] = len(out)
        out.append(link)

    nodes = [n for n in nodes if n["id"] not in canon]
    # tiers of curated nodes come from curated links (build_graph_v2 ran before any crawl), so
    # crawled links do not count here either
    degrees = compute_degrees(nodes, [l for l in out if not is_crawled(l)])
    for nid in survivors:
        by_id[nid]["tier"] = assign_tier(degrees[nid])
    return {**graph, "nodes": nodes, "links": out}, summary


def last_conflict_position(path):
    path = Path(path)
    if not path.exists():
        return -1
    data = yaml.safe_load(path.read_text()) or {}
    return max((c.get("edge_index", -1) for c in data.get("conflicts", [])), default=-1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--merges", type=Path, default=DEFAULT_MERGES)
    parser.add_argument("--conflicts", type=Path, default=DEFAULT_CONFLICTS)
    args = parser.parse_args(argv)

    graph = json.loads(args.graph.read_text())
    merges = yaml.safe_load(args.merges.read_text()) or []
    new_graph, summary = apply_merges(graph, merges, last_conflict_position(args.conflicts))
    if summary.applied:
        args.graph.write_text(json.dumps(new_graph, indent=2, ensure_ascii=False) + "\n")
    print(summary.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
