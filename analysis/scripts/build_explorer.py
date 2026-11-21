#!/usr/bin/env python3
"""Build the data files for the graph explorer (analysis/explorer/template.html).

Exports the signed graph that analysis/scripts/graph_inference.py reasons over, plus the
precomputed findings, as three JSON files that sit beside the page:

  nodes.json     one row per node:  [id, label, type, curated, flags]
                 flags: 1 drug, 2 inducer, 4 pain outcome, 8 core pain outcome (ranking set)
  edges.json     one row per signed link:  [source, target, sign, weight, curated, ref, quote,
                 status, extra_papers]   (source/target are row numbers in nodes.json)
  findings.json  the lists of the report (drug effects, targets, chokepoints, loops, calibration)
                 with paths given as row numbers in edges.json

The page re-computes any node's paths in the browser with the same algorithm as the Python
(see test_build_explorer.py and the browser check in the commit that added this file).

Usage: python3 analysis/scripts/build_explorer.py [--graph PATH] [--review PATH] [--out DIR]
"""

import argparse
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_inference as gi  # noqa: E402

DEFAULT_OUT = Path("analysis/explorer/dist")
TEMPLATE = Path(__file__).resolve().parents[1] / "explorer" / "template.html"
QUOTE_CHARS = 240
TOP = 15

HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>')


def status_of(link):
    if gi.is_crawled_link(link):
        return "unreviewed"
    if link.get("validation_status"):
        return link["validation_status"].lower()
    if link.get("confidence") == "INFERRED_CLOSURE" or link.get("origin") == "dynamic_closure":
        return "inferred"
    return "curated"


def ref_of(link):
    if gi.is_crawled_link(link):
        return f"PMID {link.get('source_pmid')}"
    return link.get("source_ref") or link.get("source_file") or "curated"


def build_data(graph, review_path=gi.DEFAULT_REVIEW):
    """(nodes, edges, findings) for the explorer."""
    sg = gi.SignedGraph(graph, review_path)
    used = sorted({e[0] for e in sg.edges} | {e[1] for e in sg.edges} | sg.core)
    idx = {nid: i for i, nid in enumerate(used)}
    nodes = []
    for nid in used:
        node = sg.nodes[nid]
        flags = ((1 if nid in sg.drugs else 0) | (2 if nid in sg.inducers else 0)
                 | (4 if nid in sg.pain else 0) | (8 if nid in sg.core else 0))
        nodes.append([nid, node["label"], node.get("entity_type") or "",
                      0 if node.get("file_type") == "crawled" else 1, flags])
    edge_index = {}
    edges = []
    for k, (s, t, sign, w, link) in enumerate(sg.edges):
        edge_index[(s, t, sign)] = k
        edges.append([idx[s], idx[t], sign, round(w, 4), 0 if gi.is_crawled_link(link) else 1, ref_of(link),
                      (link.get("quote") or "").replace("\n", " ")[:QUOTE_CHARS], status_of(link),
                      len(link.get("crawler_evidence", []))])

    def path_ids(path):
        return [edge_index[(e[0], e[1], e[2])] for e in path]

    def best(paths, sign):
        pool = [p for p in paths if gi.path_sign(p) == sign]
        return min(pool, key=lambda p: (len(p), -gi.path_weight(p))) if pool else None

    drugs = gi.drug_effects(sg)
    targets = gi.target_effects(sg)
    choke = gi.chokepoints(sg)
    loops = gi.feedback_loops(sg)
    cal = gi.calibration(sg)

    def drug_row(nid, r, sign):
        p = best(r["paths"], sign)
        return {"node": idx[nid], "score": round(r["net"], 3), "neg": r["n_neg"], "pos": r["n_pos"],
                "mediators": r["mediators"], "direct": r["direct"], "path": path_ids(p) if p else []}

    cand = sorted(((n, r) for n, r in drugs.items() if r["net"] <= -1.0 and not r["direct"]
                   and r["mediators"] >= 2 and r["agreement"] >= 0.8), key=lambda x: (x[1]["net"], -x[1]["mediators"], x[0]))
    raising = sorted(((n, r) for n, r in drugs.items() if r["net"] >= 1.0 and r["mediators"] >= 2
                      and r["agreement"] >= 0.8), key=lambda x: (-x[1]["net"], x[0]))
    double = gi.double_edged(drugs)
    drivers = sorted(((n, r) for n, r in targets.items() if n not in sg.inducers and r["net"] > 0 and r["drives"] >= 2),
                     key=lambda x: (-x[1]["net"], x[0]))
    gaps = [(n, r) for n, r in drivers if not r["inhibitors"] and sg.etype(n) in ("molecule", "receptor", "channel", "pathway")]
    inducers = sorted(((n, r) for n, r in targets.items() if n in sg.inducers and r["net"] > 0 and r["drives"] >= 2),
                      key=lambda x: (-x[1]["net"], x[0]))
    suppressors = sorted(((n, r) for n, r in targets.items() if n not in sg.inducers and r["net"] < 0 and r["suppresses"] >= 2),
                         key=lambda x: (x[1]["net"], x[0]))

    def target_row(n, r):
        return {"node": idx[n], "score": round(r["net"], 3), "drives": r["drives"], "suppresses": r["suppresses"],
                "inhibitors": len(r["inhibitors"])}

    pairs = [c for c in loops if len(c["nodes"]) == 2 and c["sign"] > 0]
    longer = [c for c in loops if len(c["nodes"]) > 2 and c["sign"] > 0]
    pairs.sort(key=lambda c: (-round(c["weight"], 9), c["nodes"]))
    longer.sort(key=lambda c: (-round(c["weight"], 9), len(c["nodes"]), c["nodes"]))
    hubs = Counter(n for c in longer for n in c["nodes"])

    def loop_row(c):
        return {"nodes": [idx[n] for n in c["nodes"]], "weight": round(c["weight"], 3),
                "inhibitory": sum(1 for e in c["edges"] if e["sign"] < 0)}

    crawled = sum(1 for e in sg.edges if gi.is_crawled_link(e[4]))
    findings = {
        "meta": {"links": len(sg.edges), "crawled": crawled, "curated": len(sg.edges) - crawled, "nodes": len(nodes),
                 "pain_nodes": len(sg.pain), "core": sorted(idx[n] for n in sg.core), "excluded": dict(sg.excluded),
                 "max_len": gi.MAX_LEN, "target_len": gi.TARGET_LEN, "decay": gi.PATH_DECAY},
        "calibration": {
            "two_hop": cal["two_hop"], "by_support": {str(k): v for k, v in cal["two_hop_by_support"].items()},
            "loo": {f"{a}/{b}": v for (a, b), v in cal["loo"].items()}, "loo_n": cal["loo_n"],
            "base_rate": round(cal["base_rate_negative"], 3), "auc": round(cal["auc"], 3), "auc_n": list(cal["auc_n"]),
            "n_pain_raising": cal["n_pain_raising"],
        },
        "pain_raising": [drug_row(n, r, 1) for n, r in raising],
        "double_edged": [drug_row(n, r, 1 if r["direct"] == [-1] else -1) for n, r in double],
        "candidates": [drug_row(n, r, -1) for n, r in cand[:TOP]],
        "n_candidates": len(cand),
        "drivers": [target_row(n, r) for n, r in drivers[:TOP]],
        "gaps": [target_row(n, r) for n, r in gaps[:10]], "n_gaps": len(gaps),
        "inducers": [target_row(n, r) for n, r in inducers[:10]],
        "suppressors": [target_row(n, r) for n, r in suppressors[:10]],
        "chokepoints": {"sources": len(choke["sources"]), "paths": choke["n_paths"],
                        "ranked": [{"node": idx[n], "share": round(s, 4)} for n, s in choke["ranked"][:TOP]]},
        "loops": {"n_pairs": len([c for c in loops if len(c["nodes"]) == 2]), "n_pos_pairs": len(pairs),
                  "n_longer": len([c for c in loops if len(c["nodes"]) > 2]), "n_pos_longer": len(longer),
                  "pairs": [loop_row(c) for c in pairs[:8]], "longer": [loop_row(c) for c in longer[:8]],
                  "hubs": [{"node": idx[n], "count": k} for n, k in hubs.most_common(10)]},
        "duplicates": [{"crawled": sg.label(c), "curated": idx[k] if k in idx else None, "links": n}
                       for c, k, n in gi.duplicate_nodes(sg)[:10]],
    }
    return nodes, edges, findings


def write_lines(path, rows):
    """A JSON array with one row per line, so a diff and a reader see the rows."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("[\n")
        fh.write(",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows))
        fh.write("\n]\n")


def write_site(out_dir, nodes, edges, findings):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_lines(out / "nodes.json", nodes)
    write_lines(out / "edges.json", edges)
    (out / "findings.json").write_text(json.dumps(findings, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    page = TEMPLATE.read_text(encoding="utf-8")
    (out / "index.html").write_text(page, encoding="utf-8")
    # a complete document for opening the page outside the artifact viewer (local checks)
    (out / "local.html").write_text(HEAD + page + "</body></html>", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(gi.DEFAULT_GRAPH))
    ap.add_argument("--review", default=str(gi.DEFAULT_REVIEW))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    graph = json.loads(Path(args.graph).read_text())
    nodes, edges, findings = build_data(graph, args.review)
    write_site(args.out, nodes, edges, findings)
    print(f"wrote {len(nodes)} nodes, {len(edges)} links -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
