#!/usr/bin/env python3
"""Build enriched knowledge graph v2 from graphify-out/graph.json.

Pipeline: entity deduplication (normalized-label equality with gene-synonym
folding) -> node enrichment (entity_type, compartment, tier) -> edge
normalization (sign derived from relation). Input is never modified; results
are written to graphify-out/graph_v2.json.

Sign convention: `sign` is read along the stored source->target direction of
each edge. +1 means the source increases/promotes the target, -1 means it
decreases/inhibits it, 0 means neutral/reference or undetermined. Passive-voice
relations ("*_by" patterns) invert that reading ("A destabilized_by B" means B
acts -1 on A); rather than silently flipping endpoints we map them to sign 0
and report them to stdout for later claim-card review.
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
    "specifies_development_of": 1,
    "inhibits": -1,
    "downregulates": -1,
    "antagonizes": -1,
    "antagonizes_pathway": -1,
    "blocks": -1,
    "suppresses": -1,
    "genetic_deletion": -1,
}

POSITIVE_RELATION_STEMS = (
    "activ", "caus", "driv", "induc", "upregul", "promot", "increas",
    "enhanc", "potenti", "stabiliz", "elevat", "sensitiz",
    "stimulat", "mediat", "transcrib", "preserv", "rescu", "restor",
    "enabl", "initiat", "normaliz", "amplifi", "contribut",
)

NEGATIVE_RELATION_STEMS = (
    "inhibit", "downregul", "suppress", "block", "disrupt", "repress",
    "decreas", "destabiliz", "knock", "antagon", "impair", "prevent",
    "attenuat", "negat",
    "damag", "cleav", "sequest", "neutraliz", "terminat", "degrad",
    "depolymeriz", "protect",
)

PASSIVE_RELATION_PATTERN = re.compile(r"(^|_)by(_|$)")

AMBIGUOUS_SIGN_RELATIONS = {
    # neutral/reference (spec baseline)
    "references",
    "conceptually_related_to",
    "semantically_similar_to",
    "same_protein",
    "interacts_with",
    "binds",
    "participates_in",
    "expressed_in",
    "regulates",
    "implements",
    "related",
    # symmetric interactions / similarities
    "interacts_with_pathway",
    "binds_to",
    "cross_talks_with_at_igf1r",
    "cooperates_with_for_ltp",
    "shares_p75ntr_with",
    "co_receptor_of",
    "same_pathway",
    "mechanistically_parallels",
    "mimics",
    "complementary_pathway_in_ACC",
    "autoregulates",
    "expression_differs_by_sex",
    # meta / proposal / annotation / dependency
    "cites",
    "proposes",
    "proposes_combination_with_comp_ang1",
    "performs",
    "gates_using",
    "depends_on",
    "requires",
    "contains",
    "targets",
    "targets_mRNA",
    "regulates_trafficking",
    "indirectly_modulates_via_nav17",
    "targeted_downstream",
    "provides_resolution_via",
    "phosphorylates",
    # passive voice: direction-inverting, pending claim-card review
    "destabilized_by",
    "stabilized_by",
    "maintained_by",
    "activated_by",
    "regulated_by_phosphorylation",
    "targeted_by",
    "encoded_by",
    "is_mediated_by",
    "is_promoted_by",
    "is_activated_by",
    "is_induced_by_indirectly",
    "is_disrupted_by",
    "is_cleaved_by",
    "converted_to_by_mmp9",
    "is_upregulated_by_hypoxia_via",
}

HUB_TIER_THRESHOLD = 15
MID_TIER_THRESHOLD = 3

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


def assign_tier(degree, hub_threshold=HUB_TIER_THRESHOLD, mid_threshold=MID_TIER_THRESHOLD):
    if degree >= hub_threshold:
        return "hub"
    if degree >= mid_threshold:
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
    dropped_duplicates = 0
    seen_triples = set()
    for link in links:
        source = canonical.get(link["source"], link["source"])
        target = canonical.get(link["target"], link["target"])
        if source == target:
            dropped_self_loops.append(link)
            continue
        triple = (source, target, link["relation"])
        if triple in seen_triples:
            dropped_duplicates += 1
            continue
        seen_triples.add(triple)
        new_link = dict(link)
        new_link["source"] = source
        new_link["target"] = target
        redirected.append(new_link)
    return redirected, dropped_self_loops, dropped_duplicates


def compute_degrees(nodes, links):
    neighbors = defaultdict(set)
    ids = {n["id"] for n in nodes}
    for link in links:
        s, t = link["source"], link["target"]
        if s in ids and t in ids and s != t:
            neighbors[s].add(t)
            neighbors[t].add(s)
    return {n["id"]: len(neighbors[n["id"]]) for n in nodes}


def relation_sign(relation):
    if relation in RELATION_SIGN:
        return RELATION_SIGN[relation]
    if PASSIVE_RELATION_PATTERN.search(relation):
        return None
    negative = any(stem in relation for stem in NEGATIVE_RELATION_STEMS)
    positive = any(stem in relation for stem in POSITIVE_RELATION_STEMS)
    if negative:
        return -1
    if positive:
        return 1
    return 0


def sign_edges(links):
    signed = []
    flagged_passives = set()
    for link in links:
        out = dict(link)
        sign = relation_sign(link["relation"])
        if sign is None:
            sign = 0
            flagged_passives.add(link["relation"])
        out["sign"] = sign
        signed.append(out)
    return signed, flagged_passives


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


def build_graph(graph_in, hub_threshold=HUB_TIER_THRESHOLD, mid_threshold=MID_TIER_THRESHOLD):
    nodes_before = len(graph_in["nodes"])
    links_before = len(graph_in["links"])

    canonical = build_canonical_map(graph_in["nodes"])
    survivors = merge_nodes(graph_in["nodes"], canonical)
    redirected, dropped_loops, dropped_dups = redirect_links(graph_in["links"], canonical)

    signed, flagged_passives = sign_edges(redirected)
    degrees = compute_degrees(survivors, signed)
    final_nodes = []
    for node in survivors:
        out = dict(node)
        out["entity_type"] = classify_entity_type(node["label"])
        out["compartment"] = classify_compartment(node["label"])
        out["tier"] = assign_tier(degrees[node["id"]], hub_threshold, mid_threshold)
        final_nodes.append(out)

    graph_out = dict(graph_in)
    graph_out["nodes"] = final_nodes
    graph_out["links"] = signed
    graph_out.setdefault("hyperedges", [])

    summary = {
        "nodes_before": nodes_before,
        "nodes_after": len(final_nodes),
        "merged_nodes": nodes_before - len(final_nodes),
        "links_before": links_before,
        "links_dropped_self_loop": len(dropped_loops),
        "links_dropped_duplicate": dropped_dups,
        "links_after": len(signed),
        "flagged_passive_relations": flagged_passives,
        "signs": Counter(l["sign"] for l in signed),
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
          f"(self-loops dropped: {summary['links_dropped_self_loop']}, "
          f"duplicate parallels dropped: {summary['links_dropped_duplicate']})")
    print("Signs:", dict(sorted(summary["signs"].items())))
    print("Entity types:", dict(sorted(summary["entity_types"].items())))
    print("Compartments:", dict(sorted(summary["compartments"].items())))
    print("Tiers:", dict(sorted(summary["tiers"].items())))
    if summary["flagged_passive_relations"]:
        print("WARNING passive-voice relations mapped to sign 0 "
              "(direction-inverting; queued for claim-card review):")
        for rel in sorted(summary["flagged_passive_relations"]):
            print(f"  {rel}")
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
    parser.add_argument("--hub-threshold", type=int, default=HUB_TIER_THRESHOLD,
                        help=f"Min degree for tier=hub (default {HUB_TIER_THRESHOLD}; "
                             "simulator plan targets ~30 hub agents)")
    parser.add_argument("--mid-threshold", type=int, default=MID_TIER_THRESHOLD,
                        help=f"Min degree for tier=mid (default {MID_TIER_THRESHOLD}; "
                             "simulator plan targets ~265 mid / ~300 peripheral agents)")
    args = parser.parse_args(argv)

    with open(args.input) as f:
        graph_in = json.load(f)

    graph_out, summary = build_graph(graph_in, args.hub_threshold, args.mid_threshold)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(graph_out, f, indent=2, ensure_ascii=False)

    print_summary(summary)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
