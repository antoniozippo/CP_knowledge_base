# crawler/conflict.py - Conflict detection and resolution

import json
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class Conflict(BaseModel):
    conflict_id: str
    edge_index: int
    subject_label: str
    object_label: str
    current_sign: int
    current_validation: str
    new_sign: int
    new_evidence_quote: str
    new_pmid: str
    recommendation: str  # HUMAN_REVIEW or AUTO_UPDATE
    detected_at: str = ""
    resolved: bool = False
    resolution: Optional[str] = None  # ACCEPT_NEW, KEEP_CURRENT, DISCARD
    resolved_at: Optional[str] = None
    reviewer_notes: Optional[str] = None


class ConflictManager:
    def __init__(self, conflicts_path: str = "crawler/conflicts.yaml"):
        self.conflicts_path = Path(conflicts_path)
        self.conflicts: list[Conflict] = []
        self._load()

    def _load(self):
        if self.conflicts_path.exists():
            data = yaml.safe_load(self.conflicts_path.read_text()) or {}
            raw = data.get("conflicts", [])
            self.conflicts = [Conflict(**c) for c in raw]
        else:
            self.conflicts = []

    def _save(self):
        data = {
            "conflicts": [c.model_dump() for c in self.conflicts],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self.conflicts_path.parent.mkdir(parents=True, exist_ok=True)
        self.conflicts_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def add_conflict(self, edge_index: int, subject_label: str, object_label: str,
                     current_sign: int, current_validation: str, new_sign: int,
                     new_evidence_quote: str, new_pmid: str) -> Conflict:
        """Record a new conflict. Never auto-refute CONFIRMED edges."""
        existing_ids = {c.conflict_id for c in self.conflicts}
        idx = len(self.conflicts) + 1
        cid = f"CONFLICT-{idx:04d}"
        while cid in existing_ids:
            idx += 1
            cid = f"CONFLICT-{idx:04d}"

        # CONFIRMED edges always require human review
        if current_validation in ("CONFIRMED", "EXTENDED"):
            recommendation = "HUMAN_REVIEW"
        else:
            recommendation = "AUTO_UPDATE"

        conflict = Conflict(
            conflict_id=cid,
            edge_index=edge_index,
            subject_label=subject_label,
            object_label=object_label,
            current_sign=current_sign,
            current_validation=current_validation,
            new_sign=new_sign,
            new_evidence_quote=new_evidence_quote,
            new_pmid=new_pmid,
            recommendation=recommendation,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )
        self.conflicts.append(conflict)
        self._save()
        return conflict

    def detect_sign_conflict(self, edge: dict, new_sign: int, new_pmid: str) -> Optional[Conflict]:
        """Check if new evidence contradicts an existing edge's sign.
        Returns Conflict if sign mismatch, None otherwise.
        """
        current_sign = edge.get("sign", 0)
        if current_sign == 0 or new_sign == 0:
            return None
        if current_sign != new_sign:
            return self.add_conflict(
                edge_index=-1,  # caller should set
                subject_label=edge.get("source", ""),
                object_label=edge.get("target", ""),
                current_sign=current_sign,
                current_validation=edge.get("validation_status", "UNREVIEWED"),
                new_sign=new_sign,
                new_evidence_quote="",
                new_pmid=new_pmid,
            )
        return None

    def get_pending(self) -> list[Conflict]:
        """Get all unresolved conflicts."""
        return [c for c in self.conflicts if not c.resolved]

    def get_human_review(self) -> list[Conflict]:
        """Get conflicts requiring human review."""
        return [c for c in self.get_pending() if c.recommendation == "HUMAN_REVIEW"]

    def resolve(self, conflict_id: str, decision: str, notes: str = ""):
        """Resolve a conflict.
        decision: ACCEPT_NEW, KEEP_CURRENT, DISCARD
        """
        for c in self.conflicts:
            if c.conflict_id == conflict_id:
                c.resolved = True
                c.resolution = decision
                c.resolved_at = datetime.now(timezone.utc).isoformat()
                c.reviewer_notes = notes
                break
        self._save()

    def summary(self) -> dict:
        """Return conflict summary stats."""
        pending = self.get_pending()
        return {
            "total": len(self.conflicts),
            "pending": len(pending),
            "human_review": len([c for c in pending if c.recommendation == "HUMAN_REVIEW"]),
            "auto_update": len([c for c in pending if c.recommendation == "AUTO_UPDATE"]),
            "resolved": len(self.conflicts) - len(pending),
        }
