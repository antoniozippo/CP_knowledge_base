# crawler/updater.py - Graph update logic

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex rules ported from build_graph_v2.py
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
# Pydantic models
# ---------------------------------------------------------------------------
class UpdateReport(BaseModel):
    new_nodes: int = 0
    new_edges: int = 0
    updated_edges: int = 0
    conflicts: int = 0
    skipped: int = 0
    details: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers (ported from build_graph_v2.py)
# ---------------------------------------------------------------------------
def _normalize_label(label: str) -> str:
    text = PAREN_RE.sub(" ", label.lower())
    text = NON_WORD_RE.sub(" ", text)
    tokens = [GENE_SYNONYMS.get(t, t) for t in text.split()]
    key = WHITESPACE_RE.sub(" ", " ".join(tokens)).strip()
    for variant, replacement in SPELLING_VARIANTS.items():
        key = key.replace(variant, replacement)
    return ACRONYM_ALIASES.get(key, key)


def _first_match(label_lower: str, rules: list[tuple[str, str]]) -> str | None:
    for value, pattern in rules:
        if re.search(pattern, label_lower):
            return value
    return None


def _node_id_from_name(name: str) -> str:
    """Derive a graph node ID from a human-readable entity name."""
    norm = _normalize_label(name)
    # collapse whitespace to underscores, strip leading/trailing underscores
    raw = re.sub(r"\s+", "_", norm).strip("_")
    # remove consecutive underscores
    raw = re.sub(r"_+", "_", raw)
    return f"CRAWLED_{raw}"


# ---------------------------------------------------------------------------
# GraphUpdater
# ---------------------------------------------------------------------------
class GraphUpdater:
    def __init__(self, graph_path: str = "graphify-out/graph_v2.json"):
        self.graph_path = Path(graph_path)
        if not self.graph_path.exists():
            raise FileNotFoundError(f"Graph file not found: {self.graph_path}")
        self.graph: dict = json.loads(self.graph_path.read_text())
        self.nodes: list[dict] = self.graph.get("nodes", [])
        self.links: list[dict] = self.graph.get("links", [])
        self.node_ids: set[str] = {n["id"] for n in self.nodes}
        self.norm_to_id: dict[str, str] = {
            n["norm_label"]: n["id"] for n in self.nodes
        }

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------
    def _classify_entity_type(self, name: str, extracted_type: str = "") -> str:
        """Classify entity type using regex rules from build_graph_v2.py.

        Falls back to the *extracted_type* supplied by the LLM extraction
        step, then to 'concept' if no regex matches.
        """
        match = _first_match(name.lower(), ENTITY_TYPE_RULES)
        return match or extracted_type or "concept"

    def _classify_compartment(self, name: str, extracted_compartment: str = "") -> str:
        """Classify compartment using regex rules from build_graph_v2.py."""
        match = _first_match(name.lower(), COMPARTMENT_RULES)
        return match or extracted_compartment or "other"

    def _assign_tier(self) -> str:
        """Assign tier based on initial degree (0 -> peripheral).

        Newly crawled nodes start with degree 0.
        """
        return "peripheral"

    # ------------------------------------------------------------------
    # Node lookup
    # ------------------------------------------------------------------
    def _find_node_by_label(self, label: str) -> Optional[dict]:
        """Find existing node by label (case-insensitive)."""
        norm = _normalize_label(label)
        # Try exact normalized label match first
        if norm in self.norm_to_id:
            node_id = self.norm_to_id[norm]
            return next((n for n in self.nodes if n["id"] == node_id), None)

        # Fall back to substring / fuzzy containment
        for node in self.nodes:
            if node["norm_label"] == norm or node["label"].lower() == label.lower():
                return node
        return None

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------
    def add_node(
        self,
        name: str,
        entity_type: str,
        compartment: str,
        source_pmid: str,
        source_doi: str = "",
    ) -> dict:
        """Add a new node to the graph.

        Node ID: derived from name (e.g., 'NewProtein' -> 'CRAWLED_NewProtein').
        Returns the new node dict.
        """
        node_id = _node_id_from_name(name)

        # Avoid duplicates
        if node_id in self.node_ids:
            log.debug("Node %s already exists, skipping", node_id)
            return next(n for n in self.nodes if n["id"] == node_id)

        now = datetime.now(timezone.utc).isoformat()
        label = name.strip()
        norm_label = _normalize_label(label)

        node = {
            "label": label,
            "file_type": "crawled",
            "source_file": None,
            "source_location": None,
            "source_url": None,
            "captured_at": now,
            "author": None,
            "contributor": "auto_crawler",
            "community": -1,
            "norm_label": norm_label,
            "id": node_id,
            "merged_from": [],
            "entity_type": self._classify_entity_type(name, entity_type),
            "compartment": self._classify_compartment(name, compartment),
            "tier": self._assign_tier(),
            "source_pmid": source_pmid,
            "source_doi": source_doi,
        }
        self.nodes.append(node)
        self.node_ids.add(node_id)
        self.norm_to_id[norm_label] = node_id
        log.info("Added node %s (type=%s, compartment=%s)", node_id, node["entity_type"], node["compartment"])
        return node

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------
    def add_edge(
        self,
        subject_id: str,
        predicate: str,
        object_id: str,
        sign: int,
        evidence_quote: str,
        source_pmid: str,
        source_doi: str = "",
        confidence: str = "INFERRED",
    ) -> dict:
        """Add a new edge (closure edge) to the graph.

        Uses origin: 'auto_crawled', validation_status: 'UNREVIEWED'.
        Returns the new link dict.
        """
        now = datetime.now(timezone.utc).isoformat()

        link = {
            "relation": predicate,
            "confidence": confidence,
            "confidence_score": 0.5,
            "source_file": None,
            "source_location": None,
            "weight": None,
            "source": subject_id,
            "target": object_id,
            "sign": sign,
            "origin": "auto_crawled",
            "quote": evidence_quote,
            "source_ref": None,
            "source_pmid": source_pmid,
            "source_doi": source_doi,
            "validation_status": "UNREVIEWED",
            "crawled_at": now,
        }
        self.links.append(link)
        log.info(
            "Added edge %s --[%s]--> %s (sign=%d)",
            subject_id, predicate, object_id, sign,
        )
        return link

    def update_edge_validation(
        self,
        edge_index: int,
        new_validation: str,
        evidence_pmid: str,
        rationale: str = "",
    ) -> None:
        """Update validation_status on an existing edge.

        Bump confidence_score by 0.05 for CONFIRMED (cap at 1.0).
        Append rationale.
        """
        if edge_index < 0 or edge_index >= len(self.links):
            log.warning("Edge index %d out of range (len=%d)", edge_index, len(self.links))
            return

        edge = self.links[edge_index]
        old_status = edge.get("validation_status", "UNREVIEWED")
        edge["validation_status"] = new_validation

        if new_validation == "CONFIRMED":
            old_score = edge.get("confidence_score", 0.5)
            edge["confidence_score"] = min(old_score + 0.05, 1.0)

        # Append rationale
        existing_rationale = edge.get("validation_rationale", "")
        stamp = f"[{evidence_pmid}] {rationale}".strip() if rationale else f"[{evidence_pmid}]"
        if existing_rationale:
            edge["validation_rationale"] = f"{existing_rationale}\n{stamp}"
        else:
            edge["validation_rationale"] = stamp

        log.info(
            "Edge %d validation: %s -> %s (score=%.2f)",
            edge_index, old_status, new_validation, edge["confidence_score"],
        )

    def detect_conflict(
        self, edge_index: int, new_sign: int, new_pmid: str
    ) -> Optional[dict]:
        """Check if new evidence contradicts existing edge.

        Returns conflict dict or None.
        """
        if edge_index < 0 or edge_index >= len(self.links):
            return None

        edge = self.links[edge_index]
        existing_sign = edge.get("sign", 0)

        # Only flag as conflict when signs are strictly opposite and both
        # are non-zero (zero means undetermined / neutral).
        if existing_sign != 0 and new_sign != 0 and existing_sign != new_sign:
            conflict = {
                "edge_index": edge_index,
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation": edge.get("relation"),
                "existing_sign": existing_sign,
                "conflicting_sign": new_sign,
                "existing_pmid": edge.get("source_pmid", "unknown"),
                "conflicting_pmid": new_pmid,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
            log.warning(
                "Conflict detected on edge %d: %s sign=%d vs new sign=%d (pmid=%s)",
                edge_index, edge.get("relation"), existing_sign, new_sign, new_pmid,
            )
            return conflict
        return None

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------
    def update(
        self,
        entity_matches: list,
        edge_matches: list,
        extractions: list,
    ) -> UpdateReport:
        """Main update orchestrator.

        Parameters
        ----------
        entity_matches : list of dicts
            Each dict has keys: name, entity_type, compartment,
            match_status ('NO_MATCH' | 'EXACT' | 'FUZZY'),
            matched_node_id (if EXACT/FUZZY), source_pmid, source_doi.
        edge_matches : list of dicts
            Each dict has keys: subject, predicate, object, sign,
            match_status ('NEW' | 'EXISTS'), edge_index (if EXISTS),
            relation_type ('CONFIRMS' | 'EXTENDS' | 'CONTRADICTS'),
            evidence_quote, source_pmid, source_doi, confidence.
        extractions : list of dicts
            Raw LLM extractions (used only for metadata provenance).

        Returns
        -------
        UpdateReport
        """
        report = UpdateReport()

        # --- Phase 1: resolve entities --------------------------------
        resolved_entities: dict[str, dict] = {}  # name -> node dict
        for match in entity_matches:
            name = match["name"]
            status = match.get("match_status", "NO_MATCH")
            pmid = match.get("source_pmid", "")
            doi = match.get("source_doi", "")

            if status == "EXACT":
                node_id = match.get("matched_node_id", "")
                node = next((n for n in self.nodes if n["id"] == node_id), None)
                if node:
                    resolved_entities[name] = node
                    report.details.append(f"EXACT match: {name} -> {node_id}")
                else:
                    # Fallback: try label lookup
                    node = self._find_node_by_label(name)
                    if node:
                        resolved_entities[name] = node
                        report.details.append(f"EXACT (label-fallback): {name} -> {node['id']}")
                    else:
                        node = self.add_node(
                            name, match.get("entity_type", ""),
                            match.get("compartment", ""), pmid, doi,
                        )
                        resolved_entities[name] = node
                        report.new_nodes += 1
                        report.details.append(f"FALLBACK new node: {name}")

            elif status == "FUZZY":
                node_id = match.get("matched_node_id", "")
                node = next((n for n in self.nodes if n["id"] == node_id), None)
                if node:
                    resolved_entities[name] = node
                    report.details.append(f"FUZZY match: {name} -> {node_id}")
                else:
                    node = self._find_node_by_label(name)
                    if node:
                        resolved_entities[name] = node
                    else:
                        node = self.add_node(
                            name, match.get("entity_type", ""),
                            match.get("compartment", ""), pmid, doi,
                        )
                        resolved_entities[name] = node
                        report.new_nodes += 1

            else:  # NO_MATCH
                # Check if it already exists in the graph by label
                existing = self._find_node_by_label(name)
                if existing:
                    resolved_entities[name] = existing
                    report.details.append(f"NO_MATCH but found existing: {name} -> {existing['id']}")
                else:
                    node = self.add_node(
                        name, match.get("entity_type", ""),
                        match.get("compartment", ""), pmid, doi,
                    )
                    resolved_entities[name] = node
                    report.new_nodes += 1
                    report.details.append(f"New node: {name} -> {node['id']}")

        # --- Phase 2: resolve edges -----------------------------------
        for edge_match in edge_matches:
            subj_name = edge_match.get("subject", "")
            obj_name = edge_match.get("object", "")
            status = edge_match.get("match_status", "NEW")
            relation_type = edge_match.get("relation_type", "")
            predicate = edge_match.get("predicate", "interacts_with")
            sign = edge_match.get("sign", 0)
            quote = edge_match.get("evidence_quote", "")
            pmid = edge_match.get("source_pmid", "")
            doi = edge_match.get("source_doi", "")
            confidence = edge_match.get("confidence", "INFERRED")

            # Resolve subject/object to node IDs
            subj_node = resolved_entities.get(subj_name)
            obj_node = resolved_entities.get(obj_name)
            if not subj_node or not obj_node:
                report.skipped += 1
                report.details.append(f"Skipped edge (unresolved): {subj_name} -> {obj_name}")
                continue

            subj_id = subj_node["id"]
            obj_id = obj_node["id"]

            # Self-loop check
            if subj_id == obj_id:
                report.skipped += 1
                report.details.append(f"Skipped self-loop: {subj_id}")
                continue

            if status == "NEW":
                self.add_edge(subj_id, predicate, obj_id, sign, quote, pmid, doi, confidence)
                report.new_edges += 1
                report.details.append(f"New edge: {subj_id} --[{predicate}]--> {obj_id}")

            elif status == "EXISTS":
                edge_idx = edge_match.get("edge_index")
                if edge_idx is None:
                    # Try to find the edge by source+target+relation
                    found_idx = None
                    for i, link in enumerate(self.links):
                        if (link.get("source") == subj_id
                                and link.get("target") == obj_id
                                and link.get("relation") == predicate):
                            found_idx = i
                            break
                    if found_idx is not None:
                        edge_idx = found_idx
                    else:
                        # Edge not found; add as new
                        self.add_edge(subj_id, predicate, obj_id, sign, quote, pmid, doi, confidence)
                        report.new_edges += 1
                        report.details.append(f"EXISTS but not found; added new: {subj_id} --[{predicate}]--> {obj_id}")
                        continue

                if relation_type == "CONTRADICTS":
                    conflict = self.detect_conflict(edge_idx, sign, pmid)
                    if conflict:
                        report.conflicts += 1
                        report.details.append(
                            f"CONFLICT edge {edge_idx}: {conflict['relation']} "
                            f"sign {conflict['existing_sign']} vs {conflict['conflicting_sign']}"
                        )
                    else:
                        # Sign same or undetermined; treat as confirms
                        self.update_edge_validation(edge_idx, "CONFIRMED", pmid, quote)
                        report.updated_edges += 1

                elif relation_type == "CONFIRMS":
                    self.update_edge_validation(edge_idx, "CONFIRMED", pmid, quote)
                    report.updated_edges += 1
                    report.details.append(f"Confirmed edge {edge_idx}")

                elif relation_type == "EXTENDS":
                    self.update_edge_validation(edge_idx, "CONFIRMED", pmid, quote)
                    # Bump confidence score by additional 0.05 (total +0.10)
                    if 0 <= edge_idx < len(self.links):
                        old = self.links[edge_idx].get("confidence_score", 0.5)
                        self.links[edge_idx]["confidence_score"] = min(old + 0.05, 1.0)
                    report.updated_edges += 1
                    report.details.append(f"Extended edge {edge_idx}")

                else:
                    # Unknown relation_type; treat as confirms
                    self.update_edge_validation(edge_idx, "CONFIRMED", pmid, quote)
                    report.updated_edges += 1
                    report.details.append(f"Updated edge {edge_idx} (type={relation_type})")

        log.info(
            "Update complete: +%d nodes, +%d edges, %d updated, %d conflicts, %d skipped",
            report.new_nodes, report.new_edges, report.updated_edges,
            report.conflicts, report.skipped,
        )
        return report

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self) -> None:
        """Save updated graph to graph_v2.json."""
        self.graph["nodes"] = self.nodes
        self.graph["links"] = self.links
        self.graph_path.write_text(
            json.dumps(self.graph, indent=2, ensure_ascii=False)
        )
        log.info(
            "Saved graph: %d nodes, %d links -> %s",
            len(self.nodes), len(self.links), self.graph_path,
        )

    # ------------------------------------------------------------------
    # Conflict reporting
    # ------------------------------------------------------------------
    def get_conflicts(self) -> list[dict]:
        """Get list of edges requiring human review (REFUTED or CONFLICT)."""
        conflicts: list[dict] = []
        for i, link in enumerate(self.links):
            status = link.get("validation_status", "")
            if status in ("REFUTED", "CONFLICT"):
                conflicts.append({
                    "index": i,
                    "source": link.get("source"),
                    "target": link.get("target"),
                    "relation": link.get("relation"),
                    "sign": link.get("sign"),
                    "validation_status": status,
                    "quote": link.get("quote", ""),
                    "source_pmid": link.get("source_pmid", ""),
                })
        return conflicts
