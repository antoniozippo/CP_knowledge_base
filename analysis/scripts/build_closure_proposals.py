#!/usr/bin/env python3
"""Build analysis/claims/closure_edges.yaml with VERBATIM quotes pulled
directly from repo files, so every quote is byte-exact by construction."""

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "analysis" / "scripts"))
import add_closure_edges as ace  # noqa: E402

GRAPH = REPO / "graphify-out" / "graph_v2.json"
OUT = REPO / "analysis" / "claims" / "closure_edges.yaml"


def _sentence_span(text, i):
    """Contiguous verbatim span covering the sentence around index i."""
    start = max(text.rfind(". ", 0, i), text.rfind(".\n", 0, i),
                text.rfind("*   ", 0, i), text.rfind("\n\n", 0, i)) + 1
    j = i
    while j < len(text) - 1:
        if text[j] == "." and text[j + 1] in " \n":
            break
        j += 1
    return start, min(j + 1, len(text))


def q(fname, marker):
    """Return a verbatim sentence (or exact given span) from repo file."""
    text = (REPO / fname).read_text()
    if marker.startswith("LITERAL:"):
        quote = marker[len("LITERAL:"):]
        assert quote in text, f"literal quote absent from {fname}: {quote[:80]!r}"
        assert len(quote) <= 400
        return quote
    i = text.find(marker)
    assert i >= 0, f"marker not found in {fname}: {marker[:60]!r}"
    start, end = _sentence_span(text, i)
    quote = text[start:end].strip()
    assert len(quote) <= 400, f"quote too long ({len(quote)}) for {fname}: {quote[:80]!r}"
    assert quote in text, f"assembled quote is NOT verbatim in {fname}: {quote[:80]!r}"
    return quote


KCC2_ID = "BDNF_TrkB_KCC2"
ALLO = "shared_mechanical_allodynia"
CS = "shared_central_sensitization"
MGL = "shared_microglia"
TNF = "TNF_TNF_alpha"
BDNF = "assaying_molecularly_structural_plasticity_BDNF"
MMP9 = "PNN_ECM_MMP9"
PNN_LOSS = "GABA_apoptosis_PNN_loss"
PV = "PV_interneurons_PV_interneurons"
SST = "SST_somatostatin_interneurons"
ROS = "GABA_apoptosis_ROS_oxidative_stress"
HIF = "hif1a_HIF1alpha"
VEGF = "vegf_VEGFA"
ANG2 = "AngPt_angiopoietin_2"
BBB = "bbb_bbb"
CA_OVL = "GABA_apoptosis_calcium_overload"

# (category, source, target, relation, sign, source_file, quote_marker)
EDGES = [
    # --- A1: symptom causation ---
    ("A1", KCC2_ID, ALLO, "causes", -1, "KCC2.md",
     "collapses the chloride gradient"),
    ("A1", KCC2_ID, CS, "causes", -1, "KCC2.md",
     "core mechanism underlying mechanical allodynia"),
    ("A1", PV, ALLO, "gates_touch_evoked_pain", -1, "PV+_interneurons.md",
     "now activates nociceptive projection neurons due to disinhibition"),
    ("A1", SST, ALLO, "drives", 1, "SST.md",
     "directly driving mechanical allodynia"),
    ("A1", TNF, ALLO, "promotes", 1,
     "analysis/literature/theme_03_neuroinflammation_TNF_NLRP3_TLR_microglia.md",
     "reduced mechanical hypersensitivity in a mouse sciatic PNI model"),
    ("A1", MMP9, ALLO, "gates_early_phase", 1,
     "analysis/literature/theme_02_MMP9_PNN_ECM.md",
     "LITERAL:MMP-9 rapid/transient DRG-neuron upregulation gates early-phase allodynia (TIMP-1, siRNA, KO, inhibitor-I all effective early; exogenous i.t. MMP-9 sufficient)"),
    ("A1", PNN_LOSS, ALLO, "emergence_of", 1, "PNN_ECM.md",
     "sufficient to induce mechanical allodynia"),
    # --- A2: cascade completion ---
    ("A2", MGL, BDNF, "releases", 1, "KCC2.md",
     "Activated microglia release BDNF"),
    ("A2", BDNF, KCC2_ID, "downregulates", -1, "KCC2.md",
     "driven primarily by microglial"),
    ("A2", TNF, KCC2_ID, "downregulates_via_tnfr1_nfkb_pkc", -1, "KCC2.md",
     "induces KCC2 downregulation via TNFR1"),
    ("A2", MMP9, PNN_LOSS, "degrades_pnn_lattice", 1, "PNN_ECM.md",
     "dismantling the PNN lattice"),
    ("A2", PNN_LOSS, PV, "impairs_fast_spiking_of", -1, "PNN_ECM.md",
     "directly reducing the fast"),
    ("A2", KCC2_ID, PV, "supports_inhibitory_output_of", 1, "PV+_interneurons.md",
     "depends on a low intracellular chloride concentration maintained by KCC2"),
    ("A2", ROS, HIF, "stabilizes", 1, "hif1a.md",
     "inhibit PHDs or directly stabilize HIF1"),
    ("A2", TNF, HIF, "stabilizes_via_nfkb_phd_inhibition", 1, "hif1a.md",
     "LITERAL:It is itself stabilized by **TNF‑α** and **ROS**, creating a positive‑feedback loop."),
    ("A2", HIF, VEGF, "transcribes", 1, "hif1a.md",
     "principal transcriptional driver of VEGFA"),
    ("A2", HIF, ANG2, "transcribes", 1, "hif1a.md",
     "inducing VEGFA and angiopoietin"),
    ("A2", HIF, MMP9, "activates", 1, "hif1a.md",
     "activates MMP"),
    ("A2", TNF, CA_OVL, "stimulates_mitochondrial_ca_overload", 1, "GABA_apoptosis.md",
     "directly stimulate mitochondrial Ca"),
    ("A2", TNF, SST, "enhances_excitability_of", 1, "SST.md",
     "enhance SST neuron excitability"),
    # --- A3: reinforcing / self-sustaining loops ---
    ("A3", MGL, TNF, "releases", 1, "TNF.md",
     "released after nerve injury by activated immune and glial cells"),
    ("A3", ANG2, MGL, "recruits_and_activates", 1, "AngPt.md",
     "promotes the inflammatory activation of macrophages"),
    ("A3", ANG2, TNF, "drives_cytokine_release_from_macrophages", 1, "AngPt.md",
     "contribute to the release of pro-inflammatory cytokines"),
    ("A3", TNF, VEGF, "mutually_upregulates", 1, "vegf.md",
     "mutually upregulate each other"),
    ("A3", VEGF, TNF, "mutually_upregulates", 1, "vegf.md",
     "mutually upregulate each other"),
    ("A3", VEGF, BBB, "disrupts", 1, "vegf.md",
     "compromise the blood"),
    ("A3", ANG2, BBB, "disrupts", 1, "AngPt.md",
     "elevated Ang-2 compromises these barriers"),
    ("A3", TNF, MMP9, "induces_expression_of", 1, "PNN_ECM.md",
     "cytokines induce MMP"),
    ("A3", MMP9, MGL, "activates_via_p38", 1,
     "analysis/literature/theme_02_MMP9_PNN_ECM.md",
     "LITERAL:rapid upregulation in injured DRG neurons, IL-1β cleavage, microglial activation via p38, BSCB/BBB opening"),
]

proposals = []
seen_pairs = set()

# Optional mapping caveats appended to a link's source_ref at apply time.
SOURCE_REF_NOTES = {
    ("AngPt_angiopoietin_2", "shared_microglia"):
        "macrophage≈CNS-resident-macrophage/microglia mapping per dossier context",
}

for cat, src, dst, rel, sign, fname, marker in EDGES:
    quote = q(fname, marker)
    pair = (src, dst)
    assert pair not in seen_pairs, f"intra-file duplicate pair {pair}"
    seen_pairs.add(pair)
    entry = {
        "category": cat,
        "source_label": src,
        "target_label": dst,
        "relation": rel,
        "sign": sign,
        "quote": quote,
        "source_file": fname,
        "confidence": "INFERRED_CLOSURE",
    }
    note = SOURCE_REF_NOTES.get(pair)
    if note:
        entry["source_ref_note"] = note
    proposals.append(entry)

# verify endpoints resolve against document nodes of the real graph
import json

graph = json.loads(GRAPH.read_text())
for p in proposals:
    r = ace.resolve_proposal_endpoints(p, graph["nodes"])
    assert r["source"] and r["target"], f"unresolved: {p['source_label']} -> {p['target_label']}"
    print(f"{p['category']} {r['source']} -> {r['target']}  [{p['sign']:+d}] {p['relation']}")

header = (
    "# Dynamic-closure edge proposals (Task 2.4b Part A).\n"
    "# Curated from repo dossiers + analysis/literature theme findings.\n"
    "# Every quote is a verbatim sentence of `source_file`; confidence\n"
    "# INFERRED_CLOSURE maps to weight 0.5 in simulator/build_cards.py.\n"
    "# Categories: A1 symptom causation, A2 cascade completion,\n"
    "# A3 reinforcing/self-sustaining loops. A4 drug coverage holds because\n"
    "# CLP257 raises KCC2, which now reaches PV/allodynia/central-sensitization.\n"
)
body = yaml.safe_dump(proposals, sort_keys=False, allow_unicode=True, width=100)
OUT.write_text(header + body)
print(f"\nwrote {len(proposals)} proposals -> {OUT}")
