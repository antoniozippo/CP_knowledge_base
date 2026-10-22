# crawler/classify.py - Label normalization and entity classification rules
# (ported from analysis/scripts/build_graph_v2.py so crawled nodes match its output)

import re

# ---------------------------------------------------------------------------
# Regex rules
# ---------------------------------------------------------------------------
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

PAREN_RE = re.compile(r"\([^)]*\)")
NON_WORD_RE = re.compile(r"[^\w\s]+")
WHITESPACE_RE = re.compile(r"\s+")

GENE_SYNONYMS = {"slc12a5": "kcc2"}
ACRONYM_ALIASES = {
    "brain derived neurotrophic factor": "bdnf",
    "vascular endothelial growth factor a": "vegfa",
}
SPELLING_VARIANTS = {"isation": "ization"}
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize_label(label: str) -> str:
    text = PAREN_RE.sub(" ", label.lower())
    text = NON_WORD_RE.sub(" ", text)
    tokens = [GENE_SYNONYMS.get(t, t) for t in text.split()]
    key = WHITESPACE_RE.sub(" ", " ".join(tokens)).strip()
    for variant, replacement in SPELLING_VARIANTS.items():
        key = key.replace(variant, replacement)
    return ACRONYM_ALIASES.get(key, key)


def first_match(label_lower: str, rules: list[tuple[str, str]]) -> str | None:
    for value, pattern in rules:
        if re.search(pattern, label_lower):
            return value
    return None


def node_id_from_name(name: str) -> str:
    """Derive a graph node ID from a human-readable entity name."""
    norm = normalize_label(name)
    # collapse whitespace to underscores, strip leading/trailing underscores
    raw = re.sub(r"\s+", "_", norm).strip("_")
    # remove consecutive underscores
    raw = re.sub(r"_+", "_", raw)
    return f"CRAWLED_{raw}"


# ---------------------------------------------------------------------------
# GraphUpdater
# ---------------------------------------------------------------------------
