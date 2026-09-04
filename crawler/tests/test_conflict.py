# crawler/tests/test_conflict.py

import pytest
from crawler.conflict import ConflictManager


def test_conflict_manager_init(tmp_path):
    path = tmp_path / "conflicts.yaml"
    mgr = ConflictManager(conflicts_path=str(path))
    assert len(mgr.conflicts) == 0


def test_add_conflict_unreviewed(tmp_path):
    path = tmp_path / "conflicts.yaml"
    mgr = ConflictManager(conflicts_path=str(path))
    c = mgr.add_conflict(
        edge_index=0, subject_label="A", object_label="B",
        current_sign=1, current_validation="UNREVIEWED",
        new_sign=-1, new_evidence_quote="contradicts", new_pmid="123",
    )
    assert c.conflict_id.startswith("CONFLICT-")
    assert c.recommendation == "AUTO_UPDATE"


def test_add_conflict_confirmed(tmp_path):
    path = tmp_path / "conflicts.yaml"
    mgr = ConflictManager(conflicts_path=str(path))
    c = mgr.add_conflict(
        edge_index=0, subject_label="A", object_label="B",
        current_sign=1, current_validation="CONFIRMED",
        new_sign=-1, new_evidence_quote="contradicts", new_pmid="123",
    )
    assert c.recommendation == "HUMAN_REVIEW"


def test_resolve(tmp_path):
    path = tmp_path / "conflicts.yaml"
    mgr = ConflictManager(conflicts_path=str(path))
    c = mgr.add_conflict(
        edge_index=0, subject_label="A", object_label="B",
        current_sign=1, current_validation="UNREVIEWED",
        new_sign=-1, new_evidence_quote="x", new_pmid="123",
    )
    mgr.resolve(c.conflict_id, "KEEP_CURRENT", notes="old evidence stronger")
    pending = mgr.get_pending()
    assert len(pending) == 0


def test_summary(tmp_path):
    path = tmp_path / "conflicts.yaml"
    mgr = ConflictManager(conflicts_path=str(path))
    mgr.add_conflict(0, "A", "B", 1, "UNREVIEWED", -1, "x", "1")
    mgr.add_conflict(1, "C", "D", 1, "CONFIRMED", -1, "y", "2")
    s = mgr.summary()
    assert s["total"] == 2
    assert s["human_review"] == 1
    assert s["auto_update"] == 1
