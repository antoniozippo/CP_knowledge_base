"""Tests for analysis/scripts/evaluate_combinations.py: interaction classes and the grounding map."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_combinations as ec  # noqa: E402


def test_interaction_class_from_effects():
    assert ec.interaction_class({"a": -0.1, "b": -0.1, "ab": -0.2}) == "additive"
    assert ec.interaction_class({"a": -0.1, "b": -0.1, "ab": -0.4}) == "synergy"
    assert ec.interaction_class({"a": -0.1, "b": -0.1, "ab": -0.1}) == "less than additive"
    assert ec.interaction_class({"a": 0.0, "b": 0.0, "ab": 0.0}) is None


def test_observed_classes_collapse_the_four_non_additive_labels():
    assert {ec.classes_of(x) for x in ("occlusion", "antagonism", "no_added_effect", "sub_additive")} == {"less than additive"}
    assert ec.classes_of("synergy") == "synergy" and ec.classes_of("additive") == "additive" and ec.classes_of("unclear") is None


def test_threshold_readouts_are_recognised():
    assert ec.THRESHOLD.search("paw withdrawal mechanical threshold") and not ec.THRESHOLD.search("mechanical allodynia")
