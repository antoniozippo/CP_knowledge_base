# crawler/records.py - Match records shared by matcher.py and updater.py

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

ENTITY_STATUSES = ("EXACT", "ALIAS", "FUZZY", "NO_MATCH")
EDGE_STATUSES = ("EXISTS", "INVERSE", "NEW")


@dataclass
class EntityMatch:
    """An extracted entity resolved against the graph, with its provenance."""

    extracted_name: str
    status: str  # one of ENTITY_STATUSES
    matched_node_id: Optional[str] = None
    matched_label: Optional[str] = None
    confidence: float = 0.0
    entity_type: str = ""
    compartment: str = ""
    source_pmid: str = ""
    source_doi: str = ""


@dataclass
class EdgeMatch:
    """An extracted relationship resolved to graph node ids, with its evidence."""

    subject_id: str
    predicate: str
    object_id: str
    status: str  # one of EDGE_STATUSES
    existing_edge_index: Optional[int] = None
    confidence: float = 0.0
    sign: int = 0
    evidence_quote: str = ""
    source_pmid: str = ""
    source_doi: str = ""
    # CONFIRMS | EXTENDS | CONTRADICTS; empty until derived from sign comparison.
    relation_type: str = ""
    # LLM-reported confidence (HIGH | MEDIUM | LOW).
    extraction_confidence: str = ""


class UpdateReport(BaseModel):
    """Counts and a human-readable trail from one GraphUpdater.update() call."""

    new_nodes: int = 0
    new_edges: int = 0
    updated_edges: int = 0
    conflicts: int = 0
    skipped: int = 0
    details: list[str] = Field(default_factory=list)
