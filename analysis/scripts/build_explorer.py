#!/usr/bin/env python3
"""Build the data files for the graph explorer (analysis/explorer/template.html).

Exports the graph that analysis/scripts/graph_inference.py reasons over as JSON files that sit
beside the page:

  nodes.json     one row per node:  [id, label, type, curated, flags, tier, source, slug]
                 flags: 1 drug, 2 inducer, 4 pain outcome, 8 core pain outcome (default ranking set);
                 slug is a short stable name (8 hex) that share links use, so they survive a rebuild
  edges.json     one row per link, signed links first (the order of graph_inference's links), then
                 unsigned ones:  [source, target, sign, weight, curated, ref, quote, status,
                 extra_papers, relation, hedged, key]   (source/target are rows of nodes.json;
                 key is stable and names the link in reviews)
  findings.json  the lists of the report (drug effects, targets, chokepoints, loops, calibration),
                 with paths given as rows of edges.json
  families.json  one entry per pain type with its outcome nodes and coverage statistics, and rows per
                 "type|evidence level": drugs [node, score, raised, lowered, steps, direct] and other
                 nodes [node, score, drives, suppresses, inhibiting drugs, paths]
  review.json    the unreviewed links that carry the most inference weight, with quality flags and
                 the 2026-11 review verdict where the link was in it

The page re-computes any node's paths in the browser with the same algorithm as the Python
(see test_build_explorer.py and the browser check run before each publish).

Usage: python3 analysis/scripts/build_explorer.py [--graph PATH] [--review PATH] [--out DIR]
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_inference as gi  # noqa: E402

DEFAULT_OUT = Path("analysis/explorer/dist")
TEMPLATE = Path(__file__).resolve().parents[1] / "explorer" / "template.html"
QUOTE_CHARS = 240
TOP = 15
REVIEW_ROWS = 800
AI_CODES = {"OK": 1, "CONTEXT": 2, "OVERSTATED": 3, "WEAK": 4, "WRONG": 5}
# review flags
F_HEDGED, F_ONE_PAPER, F_NAMES_NEITHER, F_NAMES_ONE, F_CONFLICT = 1, 2, 4, 8, 16
GENERIC = {"protein", "kinase", "receptor", "factor", "pathway", "signaling", "signalling", "cell", "cells",
           "neuron", "neurons", "channel", "transporter", "enzyme", "gene", "expression", "activation",
           "inhibitor", "antagonist", "agonist", "axis", "cascade", "complex", "family", "level", "model"}

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


def extra_papers(link):
    """Papers beyond the first: a crawled link's evidence list already holds its own paper, a curated
    link's holds only papers the crawler added."""
    n = len(link.get("crawler_evidence", []))
    return max(0, n - 1) if gi.is_crawled_link(link) else n


def link_key(link):
    """A stable name for a link, used to attach reviews to it."""
    raw = "|".join(str(link.get(k, "")) for k in ("source", "target", "sign", "relation", "source_pmid", "quote"))
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    return ("p" if gi.is_crawled_link(link) else "c") + digest


GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "κ": "kappa",
         "μ": "mu", "ω": "omega", "ε": "epsilon", "θ": "theta"}
SMALL_WORDS = {"the", "and", "for", "non", "type", "with", "from", "that", "into"}


def plain(text):
    """Lower-case text with Greek letters spelled out, so 'TNF-α' and 'TNF-alpha' compare equal."""
    return "".join(GREEK.get(c, c) for c in text.lower())


def name_tokens(label):
    """Words of a node's name that a quote about it would contain."""
    out = set()
    parts = [label.split("(")[0]] + re.findall(r"\(([^)]*)\)", label)
    for part in parts:
        for tok in re.findall(r"[a-z0-9]+", plain(part)):
            if tok in GENERIC or tok in SMALL_WORDS:
                continue
            if len(tok) >= 4 or (len(tok) >= 3 and tok.isalpha() and tok.isupper() is False) or \
                    (len(tok) >= 2 and any(c.isdigit() for c in tok)):
                out.add(tok)
    return out


def mentions(quote, label):
    q = plain(quote)
    return any(t in q for t in name_tokens(label))


def load_triage(review_path):
    """{(pmid, quote, source label, target label): (code, reason)} from the 2026-11 link review."""
    path = Path(review_path)
    if not path.exists():
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("fixed") or "").strip():
                continue                        # corrected since: the verdict no longer describes the link
            out[(r["pmid"], r["quote"], r["source"], r["target"])] = (AI_CODES.get(r["verdict"], 0), r["reason"])
    return out


def triage_path_for(review_path):
    """The review CSV that sits beside the wrong-link list graph_inference reads."""
    return review_path


def build_data(graph, review_path=gi.DEFAULT_REVIEW):
    """The explorer's files as {name: data}."""
    sg = gi.SignedGraph(graph, review_path)
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    order = sorted(nodes_by_id)
    idx = {nid: i for i, nid in enumerate(order)}
    nodes = []
    for nid in order:
        node = nodes_by_id[nid]
        crawled = node.get("file_type") == "crawled"
        flags = ((1 if nid in sg.drugs else 0) | (2 if nid in sg.inducers else 0)
                 | (4 if nid in sg.pain else 0) | (8 if nid in sg.core else 0))
        src = (f"PMID {node['source_pmid']}" if node.get("source_pmid") else "") if crawled \
            else Path(str(node.get("source_file") or "")).name
        nodes.append([nid, node["label"], node.get("entity_type") or "", 0 if crawled else 1, flags,
                      "" if crawled else (node.get("tier") or ""), src, hashlib.md5(nid.encode("utf-8")).hexdigest()[:8]])
    assert len({n[7] for n in nodes}) == len(nodes), "node slugs are not unique"

    triage = load_triage(review_path)
    edge_index, edges, keys = {}, [], []
    pair_signs = defaultdict(set)
    for s, t, sign, w, link in sg.edges:
        pair_signs[(s, t)].add(sign)

    def edge_row(s, t, sign, w, link):
        quote = (link.get("quote") or "").replace("\n", " ")
        return [idx[s], idx[t], sign, round(w, 4), 0 if gi.is_crawled_link(link) else 1, ref_of(link),
                quote[:QUOTE_CHARS], status_of(link), extra_papers(link),
                link.get("relation") or "", 1 if gi.edge_hedged((s, t, sign, w, link)) else 0, link_key(link)]

    for k, (s, t, sign, w, link) in enumerate(sg.edges):
        edge_index[(s, t, sign)] = k
        edges.append(edge_row(s, t, sign, w, link))
    seen_unsigned = set()
    for link in graph["links"]:
        if link["sign"] != 0:
            continue
        key = (link["source"], link["target"], link.get("relation"))
        if key in seen_unsigned or link["source"] not in idx or link["target"] not in idx:
            continue
        seen_unsigned.add(key)
        edges.append(edge_row(link["source"], link["target"], 0, 0.0, link))
    keys = [e[11] for e in edges]
    assert len(keys) == len(set(keys)), "link keys are not unique"

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
                 "max_len": gi.MAX_LEN, "target_len": gi.TARGET_LEN, "decay": gi.PATH_DECAY,
                 "unsigned": len(edges) - len(sg.edges),
                 "curated_only_drugs": len(gi.drug_effects(sg, edge_ok=gi.make_edge_ok(curated_only=True)))},
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

    return {"nodes": nodes, "edges": edges, "findings": findings,
            "families": build_families(sg, idx, edge_index),
            "review": build_review(sg, drugs, edge_index, idx, nodes_by_id, triage, pair_signs)}


def direct_code(signs):
    return 0 if not signs else (2 if len(signs) > 1 else signs[0])


EVIDENCE = (("all", None), ("corroborated", dict(min_papers=2, no_hedged=True)), ("curated", dict(curated_only=True)))


def build_families(sg, idx, edge_index):
    """Per pain type: its outcome nodes and coverage statistics, plus for each evidence level
    (all links / corroborated: curated or two papers and not hedged / curated only) the analysis of
    every drug and every other node against that pain type."""
    fams, rows = [], {}
    for key, label, outcomes in gi.pain_families(sg):
        for ev, opts in EVIDENCE:
            ok = gi.make_edge_ok(**opts) if opts else None
            drugs = gi.drug_effects(sg, outcomes=outcomes, edge_ok=ok)
            targets = gi.target_effects(sg, outcomes=outcomes, edge_ok=ok)
            rows[f"{key}|{ev}"] = {
                "drugs": [[idx[n], round(r["net"], 3), r["n_pos"], r["n_neg"], r["mediators"], direct_code(r["direct"])]
                          for n, r in sorted(drugs.items())],
                "targets": [[idx[n], round(r["net"], 3), r["drives"], r["suppresses"], len(r["inhibitors"]), r["n_paths"]]
                            for n, r in sorted(targets.items())],
            }
            if ev == "all":
                all_drugs, all_targets = drugs, targets
        drugs, targets = all_drugs, all_targets
        into = [e for o in outcomes for e in sg.inn.get(o, ())]
        papers = {e[4].get("source_pmid") for e in into if gi.is_crawled_link(e[4])}
        fams.append({
            "key": key, "label": label, "outcomes": sorted(idx[n] for n in outcomes),
            "stats": {
                "outcomes": len(outcomes), "links_in": len(into),
                "curated_in": sum(1 for e in into if not gi.is_crawled_link(e[4])), "papers": len(papers),
                "drivers": sum(1 for n, r in targets.items() if n not in sg.inducers and r["net"] >= 2 and r["drives"] >= 2),
                "suppressors": sum(1 for n, r in targets.items() if n not in sg.inducers and r["net"] <= -2 and r["suppresses"] >= 2),
                "drugs_lower": sum(1 for r in drugs.values() if r["net"] <= -1 and r["mediators"] >= 2),
                "drugs_raise": sum(1 for r in drugs.values() if r["net"] >= 1 and r["mediators"] >= 2),
                "gaps": sum(1 for n, r in targets.items() if n not in sg.inducers and r["net"] >= 2 and r["drives"] >= 2
                            and not r["inhibitors"] and sg.etype(n) in ("molecule", "receptor", "channel", "pathway")),
            },
        })
    return {"families": fams, "rows": rows, "evidence": [e for e, _ in EVIDENCE]}


def build_review(sg, drugs, edge_index, idx, nodes_by_id, triage, pair_signs):
    """The unreviewed links that carry the most weight in drug -> pain and injury -> pain paths."""
    impact = Counter()
    for r in drugs.values():
        for p in r["paths"]:
            w = gi.path_weight(p)
            for e in p:
                impact[(e[0], e[1], e[2])] += w
    choke = gi.chokepoints(sg)
    dist = sg.distance_to(sg.core)
    for src in choke["sources"]:
        for p in sg.paths(src, sg.core, gi.CHOKE_LEN, dist):
            w = gi.path_weight(p)
            for e in p:
                impact[(e[0], e[1], e[2])] += w
    edge_by_key = {(e[0], e[1], e[2]): e for e in sg.edges}
    rows = []
    for key, value in impact.most_common():
        edge = edge_by_key[key]
        link = edge[4]
        if not gi.is_crawled_link(link):
            continue
        quote = (link.get("quote") or "").replace("\n", " ")
        s_label, t_label = nodes_by_id[edge[0]]["label"], nodes_by_id[edge[1]]["label"]
        flags = 0
        if gi.edge_hedged(edge):
            flags |= F_HEDGED
        if extra_papers(link) == 0:
            flags |= F_ONE_PAPER
        has_s, has_t = mentions(quote, s_label), mentions(quote, t_label)
        if not has_s and not has_t:
            flags |= F_NAMES_NEITHER
        elif not (has_s and has_t):
            flags |= F_NAMES_ONE
        if len(pair_signs[(edge[0], edge[1])]) > 1:
            flags |= F_CONFLICT
        ai = triage.get((str(link.get("source_pmid")), quote, s_label, t_label), (0, ""))
        rows.append([edge_index[key], round(value, 3), flags, ai[0], ai[1]])
        if len(rows) >= REVIEW_ROWS:
            break
    return {"rows": rows, "flags": {"hedged": F_HEDGED, "one_paper": F_ONE_PAPER, "names_neither": F_NAMES_NEITHER,
                                    "names_one": F_NAMES_ONE, "conflict": F_CONFLICT}}


def write_lines(path, rows):
    """A JSON array with one row per line, so a diff and a reader see the rows."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("[\n")
        fh.write(",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows))
        fh.write("\n]\n")


def write_site(out_dir, data):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_lines(out / "nodes.json", data["nodes"])
    write_lines(out / "edges.json", data["edges"])
    for name in ("findings", "families", "review"):
        (out / f"{name}.json").write_text(json.dumps(data[name], ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
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
    data = build_data(graph, args.review)
    write_site(args.out, data)
    print(f"wrote {len(data['nodes'])} nodes, {len(data['edges'])} links, {len(data['families']['families'])} pain types, "
          f"{len(data['review']['rows'])} review rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
