#!/usr/bin/env python3
"""Correct crawled relationships the extractor got wrong, in the extractions and the graph.

Two kinds of correction:

1. Listed corrections (crawler/review/extraction_corrections_2026-11.yaml): a relationship,
   named by PMID + verbatim quote + its extracted fields, is dropped or replaced. The change is
   written to crawler/extractions/<pmid>.json, so a re-merge reproduces it, and to the graph.
   A replacement may move a finding to a context-specific node (`new_node`), created as the
   crawler would create it.
2. The sign rule (crawler/extractor.py:normalize_sign): where an extracted sign contradicted its
   direction verb, the verb's sign used to win. Links built that way move to the extracted sign
   with the predicate "modulates", which is what a re-merge now produces.

In the graph a correction moves one paper's evidence (PMID + quote) off the link that holds it.
A dropped paper is simply removed. A corrected one joins the link with the corrected source,
target and sign, as the crawler would have filed it: an existing link takes it as evidence, or
the link it came from is rewritten in place when that paper was its only one, or a new crawled
link is added. A link left with no paper is removed; one whose primary paper left takes its next
paper as primary. Links at or before the last position crawler/conflicts.yaml names are never
removed. Every run is idempotent.

Usage: python3 crawler/correct_links.py [--graph PATH] [--corrections PATH] [--dry-run]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler.classify import (  # noqa: E402
    COMPARTMENT_RULES, ENTITY_TYPE_RULES, first_match, node_id_from_name, normalize_label)
from crawler.extractor import PREDICATE_SIGN, normalize_sign  # noqa: E402

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_CORRECTIONS = Path("crawler/review/extraction_corrections_2026-11.yaml")
DEFAULT_CONFLICTS = Path("crawler/conflicts.yaml")
EXTRACTIONS_DIR = Path("crawler/extractions")
FIELDS = ("subject", "predicate", "object", "sign")


def is_crawled(link):
    return link.get("origin") == "auto_crawled"


# ------------------------------------------------------------------ extractions


def fields_of(rel):
    return {k: rel.get(k) for k in FIELDS}


def correct_extraction(data, corr):
    """Apply one listed correction to an extraction (a dict); returns 'applied', 'done' or 'missing'."""
    rels = data.get("relationships", [])
    same_quote = [r for r in rels if r.get("evidence_quote") == corr["quote"]]
    hit = [r for r in same_quote if fields_of(r) == corr["was"]]
    if not hit:
        if corr["action"] == "drop" or any(fields_of(r) == corr["now"] for r in same_quote):
            return "done"
        return "missing"
    if corr["action"] == "drop":
        data["relationships"] = [r for r in rels if r is not hit[0]]
    else:
        hit[0].update(corr["now"])
        # a renamed endpoint keeps its entity record (type, compartment), so a re-merge types it alike
        entities = data.setdefault("entities", [])
        names = {e.get("name") for e in entities}
        for side in ("subject", "object"):
            old, new = corr["was"][side], corr["now"][side]
            if new != old and new not in names:
                base = next((e for e in entities if e.get("name") == old), {"entity_type": "molecule", "compartment": "other"})
                entities.append({**{k: v for k, v in base.items() if k != "aliases"}, "name": new, "mentions": 1})
                names.add(new)
    return "applied"


def correct_extraction_files(corrections, extractions_dir=EXTRACTIONS_DIR, write=True):
    report = defaultdict(list)
    for corr in corrections:
        path = Path(extractions_dir) / f"{corr['pmid']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        outcome = correct_extraction(data, corr)
        report[outcome].append(corr["pmid"])
        if outcome == "applied" and write:
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return dict(report)


# ------------------------------------------------------------------ graph


class GraphEditor:
    """Moves single papers' evidence between links, removing emptied links at the end."""

    def __init__(self, graph, protect_through=-1):
        self.graph = graph
        self.links = graph["links"]
        self.protect_through = protect_through
        self.dead = set()
        self.log = []

    def holders(self, pmid, quote):
        """Positions of live links holding this paper's evidence (as primary or in the list)."""
        out = []
        for i, l in enumerate(self.links):
            if i in self.dead:
                continue
            prim = is_crawled(l) and str(l.get("source_pmid")) == pmid and l.get("quote") == quote
            if prim or any(str(e.get("pmid")) == pmid and e.get("quote") == quote for e in l.get("crawler_evidence", [])):
                out.append(i)
        return out

    def _take(self, i, pmid, quote):
        """Remove the paper from link i; return its evidence entry and whether the link is now empty."""
        link = self.links[i]
        evidence = link.get("crawler_evidence", [])
        entry = next((e for e in evidence if str(e.get("pmid")) == pmid and e.get("quote") == quote), None)
        if entry is None:
            entry = {"pmid": pmid, "doi": link.get("source_doi", ""), "quote": quote,
                     "predicate": link.get("relation"), "sign": link.get("sign")}
        rest = [e for e in evidence if e is not entry]
        empty = is_crawled(link) and not rest
        if not empty:
            link["crawler_evidence"] = rest
            if is_crawled(link) and str(link.get("source_pmid")) == pmid and link.get("quote") == quote:
                link["source_pmid"], link["quote"] = str(rest[0]["pmid"]), rest[0]["quote"]
                link["source_doi"] = rest[0].get("doi", "")
        return dict(entry), empty

    def _kill(self, i):
        if i <= self.protect_through:
            raise ValueError(f"correction would remove link #{i}, which crawler/conflicts.yaml names")
        self.dead.add(i)

    def _find(self, source, target, sign, skip):
        cands = [i for i, l in enumerate(self.links) if i not in self.dead and i != skip
                 and l["source"] == source and l["target"] == target and l.get("sign", 0) == sign]
        return min(cands, key=lambda i: (is_crawled(self.links[i]), i)) if cands else None

    def drop(self, i, pmid, quote, note):
        _, empty = self._take(i, pmid, quote)
        if empty:
            self._kill(i)
        self.log.append(("drop", i, pmid, note))

    def move(self, i, pmid, quote, source, target, relation, sign, note):
        entry, empty = self._take(i, pmid, quote)
        entry.update({"predicate": relation, "sign": sign, "corrected": note})
        j = self._find(source, target, sign, skip=i)
        if j is not None:
            evidence = self.links[j].setdefault("crawler_evidence", [])
            if str(pmid) not in {str(e.get("pmid")) for e in evidence}:
                evidence.append(entry)
            if empty:
                self._kill(i)
            self.log.append(("join", i, pmid, f"#{j}"))
        elif empty:
            link = self.links[i]
            link.update({"source": source, "target": target, "relation": relation, "sign": sign,
                         "crawler_evidence": [entry]})
            self.log.append(("rewrite", i, pmid, note))
        else:
            now = datetime.now(timezone.utc).isoformat()
            self.links.append({
                "relation": relation, "confidence": "INFERRED", "confidence_score": 0.5, "source_file": None,
                "source_location": None, "weight": None, "source": source, "target": target, "sign": sign,
                "origin": "auto_crawled", "quote": quote, "source_ref": None, "source_pmid": str(pmid),
                "source_doi": entry.get("doi", ""), "validation_status": "UNREVIEWED", "crawled_at": now,
                "crawler_evidence": [entry]})
            self.log.append(("new", i, pmid, f"#{len(self.links) - 1}"))

    def result(self):
        return {**self.graph, "links": [l for i, l in enumerate(self.links) if i not in self.dead]}


def crawled_node(name, entity_type, compartment, pmid):
    """A node as crawler/updater.py:add_node makes it."""
    return {
        "label": name.strip(), "file_type": "crawled", "source_file": None, "source_location": None,
        "source_url": None, "captured_at": datetime.now(timezone.utc).isoformat(), "author": None,
        "contributor": "auto_crawler", "community": -1, "norm_label": normalize_label(name.strip()),
        "id": node_id_from_name(name), "merged_from": [],
        "entity_type": first_match(name.lower(), ENTITY_TYPE_RULES) or entity_type or "concept",
        "compartment": first_match(name.lower(), COMPARTMENT_RULES) or compartment or "other",
        "tier": "peripheral", "source_pmid": str(pmid), "source_doi": "",
    }


def ensure_nodes(graph, corrections):
    """Add the crawled nodes that replacements name in `new_node`, if missing."""
    ids = {n["id"] for n in graph["nodes"]}
    for corr in corrections:
        spec = corr.get("new_node")
        if not spec:
            continue
        node = crawled_node(spec["name"], spec.get("entity_type"), spec.get("compartment"), corr["pmid"])
        if node["id"] not in (corr["graph"]["source"], corr["graph"]["target"]):
            raise ValueError(f"new_node '{spec['name']}' becomes '{node['id']}', which the correction does not use")
        if node["id"] not in ids:
            graph["nodes"].append(node)
            ids.add(node["id"])


def apply_listed(editor, corrections, note):
    for corr in corrections:
        was = corr["was"]
        old = (corr["graph_was"]["source"], corr["graph_was"]["target"], was["sign"])
        for i in editor.holders(corr["pmid"], corr["quote"]):
            link = editor.links[i]
            if (link["source"], link["target"], link.get("sign", 0)) != old:
                continue                                        # another link, or already corrected
            if corr["action"] == "drop":
                editor.drop(i, corr["pmid"], corr["quote"], note)
            else:
                g, now = corr["graph"], corr["now"]
                editor.move(i, corr["pmid"], corr["quote"], g["source"], g["target"],
                            now["predicate"], now["sign"], note)


def sign_rule_fixes(extractions_dir=EXTRACTIONS_DIR):
    """(pmid, quote, old sign, new predicate, new sign) for every extracted relationship whose sign
    contradicted its direction verb. A quote that backs other relationships too is left out: the
    graph link cannot then be told apart without the matcher."""
    out = []
    for path in sorted(Path(extractions_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pmid = str(data.get("pmid") or path.stem)
        rels = data.get("relationships", [])
        per_quote = defaultdict(int)
        for r in rels:
            per_quote[r["evidence_quote"]] += 1
        for r in rels:
            fixed = PREDICATE_SIGN.get(r["predicate"].strip().lower())
            predicate, sign = normalize_sign(r["predicate"], r.get("sign", 0))
            if fixed is not None and sign != fixed and per_quote[r["evidence_quote"]] == 1:
                out.append((pmid, r["evidence_quote"], fixed, predicate, sign))
    return out


def apply_sign_rule(editor, fixes, note):
    for pmid, quote, old_sign, predicate, sign in fixes:
        for i in editor.holders(pmid, quote):
            link = editor.links[i]
            if link.get("sign", 0) == old_sign:
                editor.move(i, pmid, quote, link["source"], link["target"], predicate, sign, note)


def last_conflict_position(path=DEFAULT_CONFLICTS):
    path = Path(path)
    if not path.exists():
        return -1
    data = yaml.safe_load(path.read_text()) or {}
    return max((c.get("edge_index", -1) for c in data.get("conflicts", [])), default=-1)


def correct_graph(graph, corrections, fixes, protect_through=-1,
                  listed_note="crawler/review/extraction_corrections_2026-11.yaml",
                  rule_note="sign contradicted the verb (crawler/extractor.py:normalize_sign)"):
    graph = {**graph, "nodes": list(graph["nodes"]), "links": [json.loads(json.dumps(l)) for l in graph["links"]]}
    ensure_nodes(graph, corrections)
    editor = GraphEditor(graph, protect_through)
    apply_listed(editor, corrections, listed_note)
    apply_sign_rule(editor, fixes, rule_note)
    return editor.result(), editor.log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--corrections", type=Path, default=DEFAULT_CORRECTIONS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    corrections = yaml.safe_load(args.corrections.read_text(encoding="utf-8")) or []
    report = correct_extraction_files(corrections, write=not args.dry_run)
    print("extractions:", {k: len(v) for k, v in report.items()})
    if report.get("missing"):
        print("  not found:", report["missing"])
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    n_nodes = len(graph["nodes"])
    new_graph, log = correct_graph(graph, corrections, sign_rule_fixes(), last_conflict_position())
    if len(new_graph["nodes"]) != n_nodes:
        print(f"graph: {len(new_graph['nodes']) - n_nodes} node(s) added")
        log = log or [("node", -1, "", "added")]
    for action, i, pmid, what in log:
        print(f"  {action:8s} link #{i} PMID {pmid}: {what}")
    print(f"graph: {len(log)} corrections, links {len(graph['links'])} -> {len(new_graph['links'])}")
    if log and not args.dry_run:
        args.graph.write_text(json.dumps(new_graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
