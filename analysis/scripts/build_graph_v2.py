#!/usr/bin/env python3
"""Build enriched knowledge graph v2 from graphify-out/graph.json.

Pipeline: entity deduplication (normalized-label equality with gene-synonym
folding) -> node enrichment (entity_type, compartment, tier) -> edge
normalization (sign derived from relation). Input is never modified; results
are written to graphify-out/graph_v2.json.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ENTITY_TYPE_RULES = [
    ("channel", r"nav1\.\d|nav1\.7|trpv\d|trpa1|trpm\d|trpc\d|cav\d(\.\d)?|p2x\d|ampar|nmdar|cotransporter|transporter|ion channel|chloride channel"),
    ("receptor", r"\breceptors?\b|trkb|trka|trkc|p75ntr|igf-?1r|tlr\d|bradykinin b\d|gar\b"),
    ("cell_type", r"interneuron|microgli[a,e]|astrocyte|oligodendrocyte|\bsst\b|satellite glia|\bt[- ]?cells?\b|treg|neurons?\b|nociceptor|schwann|pericyte|macrophage|monocyte|neutrophil|fibroblast|keratinocyte|keratinocytes|pyramidal"),
    ("symptom", r"allodynia|hyperalgesia|anxiety|depression[- ]like|pain behavior|hypoesthesia|paresthesia|spontaneous pain|hyperexcitabilit|burning|numbness"),
    ("drug", r"clp257|clp290|fasudil|ana-12|xpro1595|ibuprofen|mcc950|rapamycin|minocycline|gabapentin|pregabalin|duloxetine|arn23746|vu0\d+|zoniporide|\binhibitors?\b|\bantagonists?\b|\bblockers?\b|\benhancers?\b|\bmodulators?\b"),
    ("pathway", r"\bpathway\b|\bsignaling\b|\bcascade\b|\baxis\b"),
    ("process", r"(osis|esis|ation|ition|sion|ance|ence)$|sensitization|phosphorylation|transcription|translation"),
    ("structure", r"\bbbb\b|\bbscb\b|blood.brain barrier|blood.spinal|perineuronal nets?\b|\bpnns?\b|synapse|synaptic cleft|dorsal horn|lamina|myelin sheath|node of ranvier|meninges|axon|dendrite|postsynaptic density|peripheral nerve|neuroma"),
    ("molecule", r"\b(bdnf|ngf|gdnf|igf-?1|vegf|cntf|il-?\d+|tnf[ -]?alpha?|tnf\b|cx3cl1|ccl2|cgrp|substance p|atp|mmp-?\d+|kynuren|tryptophan|serotonin|dopamine|noradrenaline|glutamate|gaba\b|endocannabinoid)\b|kinase|phosphatase|\bmrna\b|\brna\b|creb|erk|p38|jnk|nf-?kb|rock|rhoa|cofilin|gephyrin|nkcc1|slc\d+\w*|hdac\d*|sirtuin|parkin|synapsin|kalirin|tiam1|stathmin|crmp2|zfhx2|drgx\b|trkb\b|ion channel protein"),
]

COMPARTMENT_RULES = [
    ("DRG", r"\bdrg\b|dorsal root ganglion|dorsal root ganglia"),
    ("dorsal_horn", r"spinal|dorsal horn|lamina"),
    ("ACC", r"\bacc\b|anterior cingulate|cingulate cortex|prefrontal cortex|cortical"),
    ("barrier", r"\bbbb\b|\bbscb\b|blood.brain|blood.spinal|\bbarrier\b|tight junction|endothelial"),
    ("peripheral", r"peripheral nerve|peripheral nerves|neuroma|nociceptor|\bperiphery\b|sciatic|distal axon"),
    ("systemic", r"circulating|systemic|\bcytokines?\b|il-?\d+|tnf\b|chemokine"),
]

RELATION_SIGN = {
    "activates": 1,
    "causes": 1,
    "drives": 1,
    "drives_transcription_of": 1,
    "induces": 1,
    "upregulates": 1,
    "promotes": 1,
    "rationale_for": 1,
    "inhibits": -1,
    "downregulates": -1,
    "antagonizes": -1,
    "antagonizes_pathway": -1,
    "blocks": -1,
    "suppresses": -1,
    "destabilized_by": -1,
}

GENE_SYNONYMS = {
    "slc12a5": "kcc2",
}

ACRONYM_ALIASES = {
    "brain derived neurotrophic factor": "bdnf",
    "vascular endothelial growth factor a": "vegfa",
}

SPELLING_VARIANTS = {
    "isation": "ization",
}

PAREN_RE = re.compile(r"\([^)]*\)")
NON_WORD_RE = re.compile(r"[^\w\s]+")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_label(label):
    text = PAREN_RE.sub(" ", label.lower())
    text = NON_WORD_RE.sub(" ", text)
    tokens = [GENE_SYNONYMS.get(t, t) for t in text.split()]
    key = WHITESPACE_RE.sub(" ", " ".join(tokens)).strip()
    for variant, replacement in SPELLING_VARIANTS.items():
        key = key.replace(variant, replacement)
    return ACRONYM_ALIASES.get(key, key)


def _first_match(label_lower, rules):
    for value, pattern in rules:
        if re.search(pattern, label_lower):
            return value
    return None


def classify_entity_type(label):
    return _first_match(label.lower(), ENTITY_TYPE_RULES) or "concept"


def classify_compartment(label):
    return _first_match(label.lower(), COMPARTMENT_RULES) or "other"


def assign_tier(degree):
    if degree >= 15:
        return "hub"
    if degree >= 3:
        return "mid"
    return "peripheral"


def build_canonical_map(nodes):
    groups = defaultdict(list)
    for node in nodes:
        key = normalize_label(node["label"])
        if key:
            groups[key].append(node)
    canonical = {}
    for members in groups.values():
        survivor_id = members[0]["id"]
        for node in members:
            canonical[node["id"]] = survivor_id
    return canonical


def merge_nodes(nodes, canonical):
    survivors = []
    absorbed = defaultdict(list)
    seen_survivors = {}
    for node in nodes:
        cid = canonical[node["id"]]
        if cid == node["id"]:
            survivors.append(dict(node))
            seen_survivors[cid] = survivors[-1]
        else:
            absorbed[cid].append(node["id"])
    for cid, merged_ids in absorbed.items():
        seen_survivors[cid]["merged_from"] = merged_ids
    return survivors


def redirect_links(links, canonical):
    redirected = []
    dropped_self_loops = []
    for link in links:
        source = canonical.get(link["source"], link["source"])
        target = canonical.get(link["target"], link["target"])
        if source == target:
            dropped_self_loops.append(link)
            continue
        new_link = dict(link)
        new_link["source"] = source
        new_link["target"] = target
        redirected.append(new_link)
    return redirected, dropped_self_loops


def compute_degrees(nodes, links):
    neighbors = defaultdict(set)
    ids = {n["id"] for n in nodes}
    for link in links:
        s, t = link["source"], link["target"]
        if s in ids and t in ids and s != t:
            neighbors[s].add(t)
            neighbors[t].add(s)
    return {n["id"]: len(neighbors[n["id"]]) for n in nodes}


def sign_edges(links):
    signed = []
    for link in links:
        out = dict(link)
        out["sign"] = RELATION_SIGN.get(link["relation"], 0)
        signed.append(out)
    return signed


def find_near_misses(nodes, threshold=0.6, limit=10):
    token_sets = {
        n["id"]: frozenset(normalize_label(n["label"]).split())
        for n in nodes
        if normalize_label(n["label"])
    }
    items = list(token_sets.items())
    near_misses = []
    for i, (id_a, set_a) in enumerate(items):
        for id_b, set_b in items[i + 1:]:
            if not set_a or not set_b:
                continue
            jaccard = len(set_a & set_b) / len(set_a | set_b)
            if jaccard >= threshold:
                labels = {n["id"]: n["label"] for n in nodes}
                near_misses.append((round(jaccard, 2), labels[id_a], labels[id_b]))
                if len(near_misses) >= limit:
                    return near_misses
    return near_misses


def build_graph(graph_in):
    nodes_before = len(graph_in["nodes"])
    links_before = len(graph_in["links"])

    canonical = build_canonical_map(graph_in["nodes"])
    survivors = merge_nodes(graph_in["nodes"], canonical)
    redirected, dropped = redirect_links(graph_in["links"], canonical)

    enriched = sign_edges(redirected)
    degrees = compute_degrees(survivors, enriched)
    final_nodes = []
    for node in survivors:
        out = dict(node)
        out["entity_type"] = classify_entity_type(node["label"])
        out["compartment"] = classify_compartment(node["label"])
        out["tier"] = assign_tier(degrees[node["id"]])
        final_nodes.append(out)

    graph_out = dict(graph_in)
    graph_out["nodes"] = final_nodes
    graph_out["links"] = enriched
    graph_out.setdefault("hyperedges", [])

    summary = {
        "nodes_before": nodes_before,
        "nodes_after": len(final_nodes),
        "merged_nodes": nodes_before - len(final_nodes),
        "links_before": links_before,
        "links_dropped_self_loop": len(dropped),
        "links_after": len(enriched),
        "entity_types": Counter(n["entity_type"] for n in final_nodes),
        "compartments": Counter(n["compartment"] for n in final_nodes),
        "tiers": Counter(n["tier"] for n in final_nodes),
        "near_misses": find_near_misses(final_nodes),
    }
    return graph_out, summary


def print_summary(summary):
    print(f"Nodes: {summary['nodes_before']} -> {summary['nodes_after']} "
          f"(merged: {summary['merged_nodes']})")
    print(f"Links: {summary['links_before']} -> {summary['links_after']} "
          f"(self-loops dropped: {summary['links_dropped_self_loop']})")
    print("Entity types:", dict(sorted(summary["entity_types"].items())))
    print("Compartments:", dict(sorted(summary["compartments"].items())))
    print("Tiers:", dict(sorted(summary["tiers"].items())))
    if summary["near_misses"]:
        print("Near-miss pairs NOT merged (token overlap but distinct normalized labels):")
        for score, a, b in summary["near_misses"]:
            print(f"  [{score}] {a!r} <-> {b!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build knowledge graph v2")
    parser.add_argument("--input", default="graphify-out/graph.json",
                        help="Input graph JSON path")
    parser.add_argument("--output", default="graphify-out/graph_v2.json",
                        help="Output graph v2 JSON path")
    args = parser.parse_args(argv)

    with open(args.input) as f:
        graph_in = json.load(f)

    graph_out, summary = build_graph(graph_in)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(graph_out, f, indent=2, ensure_ascii=False)

    print_summary(summary)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
