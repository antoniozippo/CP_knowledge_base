# crawler/updater.py - Graph update logic

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from crawler.classify import (
    COMPARTMENT_RULES,
    ENTITY_TYPE_RULES,
    first_match,
    node_id_from_name,
    normalize_label,
)
from crawler.conflict import ConflictManager
from crawler.records import EdgeMatch, EntityMatch, UpdateReport

log = logging.getLogger(__name__)

MATCHED_ENTITY_STATUSES = ("EXACT", "ALIAS", "FUZZY")
# New evidence never flips these verdicts; it goes to human review instead.
PROTECTED_VALIDATION_STATUSES = ("REFUTED", "MIXED")
# Evidence policy: the crawler never rewrites validation_status (those
# verdicts come from the literature sweeps). Supporting extractions are
# appended to the link's crawler_evidence list, once per PMID, for review.
EVIDENCE_FIELD = "crawler_evidence"

class GraphUpdater:
    def __init__(
        self,
        graph_path: str = "graphify-out/graph_v2.json",
        conflict_manager: Optional[ConflictManager] = None,
    ):
        self.conflict_manager = conflict_manager
        self.graph_path = Path(graph_path)
        if not self.graph_path.exists():
            raise FileNotFoundError(f"Graph file not found: {self.graph_path}")
        self.graph: dict = json.loads(self.graph_path.read_text())
        self.nodes: list[dict] = self.graph.get("nodes", [])
        self.links: list[dict] = self.graph.get("links", [])
        self.node_ids: set[str] = {n["id"] for n in self.nodes}
        self.nodes_by_id: dict[str, dict] = {n["id"]: n for n in self.nodes}
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
        match = first_match(name.lower(), ENTITY_TYPE_RULES)
        return match or extracted_type or "concept"

    def _classify_compartment(self, name: str, extracted_compartment: str = "") -> str:
        """Classify compartment using regex rules from build_graph_v2.py."""
        match = first_match(name.lower(), COMPARTMENT_RULES)
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
        norm = normalize_label(label)
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
        node_id = node_id_from_name(name)

        # Avoid duplicates
        if node_id in self.node_ids:
            log.debug("Node %s already exists, skipping", node_id)
            return next(n for n in self.nodes if n["id"] == node_id)

        now = datetime.now(timezone.utc).isoformat()
        label = name.strip()
        norm_label = normalize_label(label)

        node: dict = {
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
        self.nodes_by_id[node_id] = node
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
        evidence = [{"pmid": source_pmid, "doi": source_doi, "quote": evidence_quote,
                     "predicate": predicate, "sign": sign, "crawled_at": now}]

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
            EVIDENCE_FIELD: evidence,
        }
        self.links.append(link)
        log.info(
            "Added edge %s --[%s]--> %s (sign=%d)",
            subject_id, predicate, object_id, sign,
        )
        return link

    def add_evidence(self, edge_index: int, em: EdgeMatch) -> bool:
        """Append em as supporting evidence on a link; False if that PMID is
        already recorded there (reruns and repeat mentions add nothing).

        validation_status is left alone; confidence_score rises 0.05 per new
        PMID (0.10 when the evidence adds a sign to an unsigned edge).
        """
        edge = self.links[edge_index]
        evidence = edge.setdefault(EVIDENCE_FIELD, [])
        if any(e.get("pmid") == em.source_pmid for e in evidence):
            return False
        evidence.append({
            "pmid": em.source_pmid, "doi": em.source_doi, "quote": em.evidence_quote,
            "predicate": em.predicate, "sign": em.sign,
            "relation_type": em.relation_type or "CONFIRMS",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        })
        bump = 0.10 if em.relation_type == "EXTENDS" else 0.05
        edge["confidence_score"] = min((edge.get("confidence_score") or 0.5) + bump, 1.0)
        return True

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
    def _conflict_reason(self, edge_idx: int, em: EdgeMatch) -> str:
        """Why new evidence must not be applied to this edge, or '' if it can."""
        if em.relation_type == "CONTRADICTS" and self.detect_conflict(
            edge_idx, em.sign, em.source_pmid
        ):
            return "sign contradiction"
        status = self.links[edge_idx].get("validation_status")
        if status in PROTECTED_VALIDATION_STATUSES:
            return f"new evidence on {status} edge"
        return ""

    def _record_conflict(self, edge_idx: int, em: EdgeMatch) -> None:
        """Hand a conflict to the ConflictManager; the edge itself is left unchanged."""
        if self.conflict_manager is None:
            return
        edge = self.links[edge_idx]
        subject = self.nodes_by_id.get(edge.get("source", ""), {})
        target = self.nodes_by_id.get(edge.get("target", ""), {})
        self.conflict_manager.add_conflict(
            edge_index=edge_idx,
            subject_label=subject.get("label", edge.get("source", "")),
            object_label=target.get("label", edge.get("target", "")),
            current_sign=edge.get("sign", 0),
            current_validation=edge.get("validation_status", "UNREVIEWED"),
            new_sign=em.sign,
            new_evidence_quote=em.evidence_quote,
            new_pmid=em.source_pmid,
        )

    def _resolve_entity(self, match: EntityMatch, report: "UpdateReport") -> dict:
        """Return the graph node for a matched entity, creating it if needed."""
        name = match.extracted_name
        if match.status in MATCHED_ENTITY_STATUSES and match.matched_node_id:
            node = self.nodes_by_id.get(match.matched_node_id)
            if node:
                report.details.append(f"{match.status} match: {name} -> {node['id']}")
                return node
        existing = self._find_node_by_label(name)
        if existing:
            report.details.append(f"Found existing by label: {name} -> {existing['id']}")
            return existing
        node = self.add_node(
            name, match.entity_type, match.compartment,
            match.source_pmid, match.source_doi,
        )
        report.new_nodes += 1
        report.details.append(f"New node: {name} -> {node['id']}")
        return node

    def update(
        self,
        entity_matches: list[EntityMatch],
        edge_matches: list[EdgeMatch],
        extractions: list,
    ) -> UpdateReport:
        """Apply matcher output to the graph.

        Parameters
        ----------
        entity_matches : EntityMatch records from EntityMatcher.match_batch.
        edge_matches : EdgeMatch records from EntityMatcher.match_batch;
            endpoints are already graph node ids.
        extractions : raw ExtractionResult objects (unused; kept for provenance
            hooks and call-site compatibility).

        Returns
        -------
        UpdateReport
        """
        report = UpdateReport()
        by_name = {m.extracted_name: m for m in entity_matches}

        # --- Phase 1: matched entities (new ones are created on demand below,
        # only when a relationship links them to the graph) --------------------
        for match in entity_matches:
            if match.status in MATCHED_ENTITY_STATUSES and match.matched_node_id:
                self._resolve_entity(match, report)

        # (source, target, sign) -> index of an auto-crawled link, so the same
        # finding from several papers or reruns becomes one edge with evidence
        crawled = {
            (l["source"], l["target"], l.get("sign", 0)): i
            for i, l in enumerate(self.links) if l.get("origin") == "auto_crawled"
        }
        linked_new: set[str] = set()

        # --- Phase 2: apply edges --------------------------------------
        for em in edge_matches:
            subj_id, obj_id = em.subject_id, em.object_id
            if not subj_id or not obj_id:
                new_name = em.subject_name if not subj_id else em.object_name
                new_match = by_name.get(new_name)
                if new_match is None:
                    report.skipped += 1
                    continue
                node_id = self._resolve_entity(new_match, report)["id"]
                linked_new.add(new_name)
                subj_id, obj_id = (node_id, obj_id) if not subj_id else (subj_id, node_id)
            if subj_id not in self.node_ids or obj_id not in self.node_ids:
                report.skipped += 1
                report.details.append(f"Skipped edge (unknown node): {subj_id} -> {obj_id}")
                continue
            if subj_id == obj_id:
                report.skipped += 1
                report.details.append(f"Skipped self-loop: {subj_id}")
                continue

            edge_idx = em.existing_edge_index if em.status == "EXISTS" else None
            if edge_idx is None:
                key = (subj_id, obj_id, em.sign)
                if key in crawled:
                    if self.add_evidence(crawled[key], em):
                        report.updated_edges += 1
                    continue
                self.add_edge(
                    subj_id, em.predicate, obj_id, em.sign,
                    em.evidence_quote, em.source_pmid, em.source_doi,
                )
                crawled[key] = len(self.links) - 1
                report.new_edges += 1
                report.details.append(f"New edge: {subj_id} --[{em.predicate}]--> {obj_id}")
                continue

            reason = self._conflict_reason(edge_idx, em)
            if reason:
                self._record_conflict(edge_idx, em)
                report.conflicts += 1
                report.details.append(f"CONFLICT edge {edge_idx}: {reason}")
                continue

            if self.add_evidence(edge_idx, em):
                report.updated_edges += 1
                report.details.append(f"Evidence on edge {edge_idx} ({em.relation_type or 'CONFIRMS'})")

        report.unlinked_entities = sum(
            1 for m in entity_matches
            if m.status == "NO_MATCH" and m.extracted_name not in linked_new
        )
        log.info(
            "Update complete: +%d nodes, +%d edges, %d updated, %d conflicts, %d skipped, "
            "%d new entities left out (no link to the graph)",
            report.new_nodes, report.new_edges, report.updated_edges,
            report.conflicts, report.skipped, report.unlinked_entities,
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
            json.dumps(self.graph, indent=2, ensure_ascii=False) + "\n"
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
