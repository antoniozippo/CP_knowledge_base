#!/usr/bin/env python3
"""How much of the two-hop sign agreement comes from the paths, and how much from base rates?

graph_inference.calibration reports how often a direct link's sign matches the sign composed
along its two-hop paths (about 90% on the chronic-pain graph). This script sets that number
beside baselines on the same links:

  majority      the more common sign among the evaluated links
  source        each source node's usual sign: the majority sign of its other out-links
                (drugs mostly inhibit, cytokines mostly raise)
  shuffled      composition after shuffling signs across all links, and within each source's
                out-links (which keeps every source's usual sign)

and repeats the comparison with only the paths whose links come from papers (or, for curated
links, dossiers) other than the direct link's own: one paper reporting all three steps makes
agreement automatic. Where composition and the source baseline disagree is the only place the
path adds information; how often it is right there is the honest measure of what paths add.

Usage: python3 analysis/scripts/calibration_baselines.py [--graph PATH] [--review PATH] [--shuffles N]
"""

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_inference as gi  # noqa: E402


def sources_of(link):
    """Where a link's evidence comes from: its papers, or for a curated link its dossier too."""
    out = {str(e.get("pmid")) for e in link.get("crawler_evidence", [])}
    if gi.is_crawled_link(link):
        out.add(str(link.get("source_pmid")))
    else:
        out.add("file:" + str(link.get("source_file") or link.get("source_ref")))
    return out


def evaluation_cases(edges):
    """[(k, [(a, b), ...])]: edge k = s -> t2 with one sign, and its two-hop paths s -a-> t -b-> t2,
    as graph_inference.calibration counts them."""
    out = defaultdict(list)
    for k, e in enumerate(edges):
        out[e[0]].append(k)
    signs = defaultdict(set)
    for e in edges:
        signs[(e[0], e[1])].add(e[2])
    cases = []
    for k, (s, t2, _, _, _) in enumerate(edges):
        if len(signs[(s, t2)]) > 1:
            continue
        paths = [(a, b) for a in out[s] for b in out[edges[a][1]]
                 if edges[b][1] == t2 and edges[a][1] != t2 and edges[b][0] != s]
        if paths:
            cases.append((k, paths))
    return cases


def independent(edges, k, paths):
    """The paths none of whose links shares a source with link k."""
    own = sources_of(edges[k][4])
    return [(a, b) for a, b in paths
            if not (sources_of(edges[a][4]) & own) and not (sources_of(edges[b][4]) & own)]


def composed(edges, signs, paths):
    return sum(signs[a] * signs[b] * edges[a][3] * edges[b][3] for a, b in paths)


def source_tendency(edges, signs):
    """k -> sum of the signs of the source's other out-links (its usual sign, leave-one-out)."""
    total = defaultdict(int)
    for e, s in zip(edges, signs):
        total[e[0]] += s
    return lambda k: total[edges[k][0]] - signs[k]


def head_to_head(edges, cases, indep):
    """Composition and the source baseline on the cases where both make a call."""
    signs = [e[2] for e in edges]
    tend = source_tendency(edges, signs)
    n = comp = src = dis = dis_comp = 0
    for k, paths in cases:
        if indep:
            paths = independent(edges, k, paths)
            if not paths:
                continue
        net, v = composed(edges, signs, paths), tend(k)
        if net == 0 or v == 0:
            continue
        truth = signs[k] > 0
        c, s_ = (net > 0) == truth, (v > 0) == truth
        n += 1
        comp += c
        src += s_
        if (net > 0) != (v > 0):
            dis += 1
            dis_comp += c
    return {"n": n, "composition": comp, "source": src, "disagree": dis, "composition_right_when_disagree": dis_comp}


def shuffled(edges, cases, within_source, rnd):
    signs = [e[2] for e in edges]
    perm = signs[:]
    if within_source:
        by_src = defaultdict(list)
        for k, e in enumerate(edges):
            by_src[e[0]].append(k)
        for ks in by_src.values():
            vals = [signs[k] for k in ks]
            rnd.shuffle(vals)
            for k, v in zip(ks, vals):
                perm[k] = v
    else:
        rnd.shuffle(perm)
    ok = n = 0
    for k, paths in cases:
        net = composed(edges, perm, paths)
        if net:
            ok += (net > 0) == (perm[k] > 0)
            n += 1
    return ok / n if n else float("nan")


def wilson(k, n, z=1.96):
    if not n:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def compare(sg, shuffles=30, seed=1):
    edges = sg.edges
    cases = evaluation_cases(edges)
    signs = [e[2] for e in edges]
    evaluated = [signs[k] for k, _ in cases]
    rnd = random.Random(seed)
    return {
        "cases": len(cases),
        "majority": max(evaluated.count(1), evaluated.count(-1)) / len(evaluated) if evaluated else float("nan"),
        "all_paths": head_to_head(edges, cases, indep=False),
        "independent_paths": head_to_head(edges, cases, indep=True),
        "shuffled_all": sum(shuffled(edges, cases, False, rnd) for _ in range(shuffles)) / shuffles,
        "shuffled_within_source": sum(shuffled(edges, cases, True, rnd) for _ in range(shuffles)) / shuffles,
    }


def render(r):
    lines = [f"Links with a single sign and at least one two-hop path: {r['cases']}",
             f"Majority sign among them: {r['majority']:.1%}",
             f"Composition with signs shuffled across all links: {r['shuffled_all']:.1%}",
             f"Composition with signs shuffled within each source's out-links: {r['shuffled_within_source']:.1%}",
             ""]
    for key, title in (("all_paths", "All paths"), ("independent_paths", "Paths from other papers only")):
        h = r[key]
        if not h["n"]:
            continue
        lo, hi = wilson(h["composition_right_when_disagree"], h["disagree"])
        lines += [f"{title} (n = {h['n']}): composition {h['composition'] / h['n']:.1%}, "
                  f"source baseline {h['source'] / h['n']:.1%}; they disagree on {h['disagree']}, where composition "
                  f"is right {h['composition_right_when_disagree']} times "
                  f"({h['composition_right_when_disagree'] / max(h['disagree'], 1):.0%}, 95% CI {lo:.0%}-{hi:.0%})"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(gi.DEFAULT_GRAPH))
    ap.add_argument("--review", default=str(gi.DEFAULT_REVIEW))
    ap.add_argument("--shuffles", type=int, default=30)
    args = ap.parse_args(argv)
    sg = gi.SignedGraph(json.loads(Path(args.graph).read_text()), args.review)
    print(render(compare(sg, args.shuffles)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
