"""Promote misclassified rationale-typed entities to document nodes.

The original graphify extraction typed several canonical biology entities
(CGRP, Cav3.2, P2X7, Substance P, HDACs, ...) as file_type="rationale",
excluding them from the simulator card pool. This script flips genuinely
entity-like rationale nodes to file_type="document" behind three guards:

1. meta-label filter   - labels containing Rationale/Mind Map/Skill/etc stay.
2. entity-type filter  - classify_entity_type(label) must land in PROMOTABLE.
3. duplicate guard     - normalized label must not collide with an existing
                         document node (catches case-duplicate pairs such as
                         tnf_tnfr1 vs TNF_TNFR1).
plus a small curated skip-set for semantic aliases the normalizer cannot
catch (e.g. shared_tnfa vs TNF_TNF_alpha).

Promoted nodes keep their existing edges and get tier recomputed.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_graph_v2 import assign_tier, classify_entity_type, normalize_label

PROMOTABLE = {"molecule", "receptor", "channel", "cell_type", "drug", "symptom", "structure"}

META_MARKERS = (
    "rationale", "mind map", "skill", "design principle", "cross-pathway",
    "strategic", "framework",
)

# Semantic aliases of existing document entities that normalize_label cannot
# unify (hand-curated; each entry documented).
CURATED_SKIP = {
    # short gene-symbol aliases of existing long-labeled document nodes
    "shared_tnfa": "duplicate of TNF_TNF_alpha",
    "tlr2_myd88": "duplicate of tlr4_myd88",
    "tnf_tnfr1": "short alias of TNF_TNFR1",
    "tnf_tnfr2": "short alias of TNF_TNFR2",
    "pnn_ecm_mmp9": "short alias of PNN_ECM_MMP9",
    "angpt_tie2": "short alias of AngPt_Tie2",
    "nogoa_ngr1_ngr1": "short alias of NogoA_NgR1_NgR1",
    "csf1_il34": "short alias of CSF1-CSF1R_IL34",
    "trpv1_trpv1": "short alias of NogoA_NgR1_TRPV1",
    # granular framings already covered by true-new synced nodes
    "bradykinin_b1r": "covered by Bradykinin_B1Receptor (Inducible)",
    "bradykinin_b2r": "covered by Bradykinin_B2Receptor (Constitutive)",
    # pathway-arm / mechanism / role-concept residuals
    "cx3cl1_cx3cr1_tgfb_smad": "TGF-beta/Smad pathway arm, not an entity",
    "ana12_mechanism": "binding-mechanism note, not an entity",
    "sst_interneuron_excitatory_role": "role framing of existing SST entities",
    # CLP257 already covered by document drug card BDNF_TrkB_CLP257
    "kcc2_clp257": "duplicate of BDNF_TrkB_CLP257",
    "insights_kcc2_clp257": "duplicate of BDNF_TrkB_CLP257",
}

PROCESS_MARKERS = (
    "pyroptosis", "lactylation", "dimorphism", "switching", "sensitisation",
    "sensitization", "feed-forward", "feedforward", "feedback", "cascade",
    "paradigm", "auto-amplificatory", "crosstalk", "spillover",
    "priming", "amplification", "stabilization", "neurogenic inflammation",
    "co-release", "excitotoxicity", "disinhibition cascade", "axis",
    "signaling", "signalling", "regeneration", "silencing", "blockade",
    "inhibition (", "preservation", "inhibition /",
    "apoptosis", "release from", "glycosylation", "protection of",
    "sex-specific", "sex differences", "splicing", "neuroma", "mrna stability",
    "mechanism", "phenotype", "defects", "glycolytic shift", "role",
)


def is_meta_label(label):
    low = label.lower()
    return any(m in low for m in META_MARKERS)


def is_process_like(label):
    low = label.lower()
    return any(m in low for m in PROCESS_MARKERS)


def select_promotions(nodes, doc_norm_labels):
    """Return (promote_ids, skipped) given all v2 nodes."""
    promote, skipped = [], []
    for n in nodes:
        if n.get("file_type") != "rationale":
            continue
        rid, label = n["id"], n["label"]
        norm = normalize_label(label)
        entry_id = None
        if rid in CURATED_SKIP:
            skipped.append({"id": rid, "reason": f"curated: {CURATED_SKIP[rid]}"})
        elif is_meta_label(label):
            skipped.append({"id": rid, "reason": "meta label"})
        elif classify_entity_type(label) not in PROMOTABLE:
            skipped.append({"id": rid, "reason": "non-entity classification"})
        elif is_process_like(label):
            skipped.append({"id": rid, "reason": "process-like label"})
        elif norm in doc_norm_labels:
            skipped.append({"id": rid, "reason": "normalized-label duplicate of existing document"})
        else:
            promote.append(rid)
            doc_norm_labels.add(norm)
    return promote, skipped


def rescue(graph_v2_path):
    graph = json.loads(Path(graph_v2_path).read_text())
    doc_norm_labels = {
        normalize_label(n["label"]) for n in graph["nodes"]
        if n.get("file_type") == "document"
    }
    promote_ids, skipped = select_promotions(graph["nodes"], doc_norm_labels)
    promote_set = set(promote_ids)

    degree = {}
    for l in graph["links"]:
        degree[l.get("source")] = degree.get(l.get("source"), 0) + 1
        degree[l.get("target")] = degree.get(l.get("target"), 0) + 1

    changed = []
    for n in graph["nodes"]:
        if n["id"] in promote_set:
            n["file_type"] = "document"
            n["tier"] = assign_tier(degree.get(n["id"], 0))
            changed.append(n["id"])

    summary = {
        "promoted": len(changed),
        "promoted_ids": changed,
        "skipped": len(skipped),
        "nodes_total": len(graph["nodes"]),
        "links_total": len(graph["links"]),
    }
    Path(graph_v2_path).write_text(json.dumps(graph, indent=2, ensure_ascii=False))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-v2", default="graphify-out/graph_v2.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run:
        graph = json.loads(Path(args.graph_v2).read_text())
        doc_norms = {normalize_label(n["label"]) for n in graph["nodes"]
                     if n.get("file_type") == "document"}
        promote, skipped = select_promotions(graph["nodes"], doc_norms)
        print(json.dumps({"would_promote": len(promote), "ids": promote,
                          "skipped": len(skipped)}, indent=1))
        return 0
    summary = rescue(args.graph_v2)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
