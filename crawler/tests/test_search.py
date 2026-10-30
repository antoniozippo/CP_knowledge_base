# crawler/tests/test_search.py

import pytest
from crawler.search import build_pubmed_query, PaperMeta


def test_build_pubmed_query_keywords_only():
    q = build_pubmed_query(
        keywords=["KCC2 neuropathic pain", "BDNF spinal cord"],
        mesh_terms=[],
        since="2021-01-01",
    )
    assert "KCC2 neuropathic pain" in q
    assert "BDNF spinal cord" in q
    assert "2021/01/01:3000[dp]" in q
    assert "OR" in q


def test_build_pubmed_query_mesh_only():
    q = build_pubmed_query(
        keywords=[],
        mesh_terms=["Neuropathic Pain", "Microglia"],
        since="2020-01-01",
    )
    assert "Neuropathic Pain" in q
    assert "Microglia" in q
    assert "2020/01/01:3000[dp]" in q


def test_build_pubmed_query_combined():
    q = build_pubmed_query(
        keywords=["fasudil ROCK"],
        mesh_terms=["Rho-Associated Kinases"],
        since="2023-01-01",
    )
    assert "fasudil ROCK" in q
    assert "Rho-Associated Kinases" in q
    # Should have AND between keyword and mesh groups
    assert " AND " in q


def test_paper_meta_creation():
    p = PaperMeta(
        pmid="12345678",
        doi="10.1000/test",
        title="Test Paper",
        authors=["Author A", "Author B"],
        journal="Nature",
        publication_date="2024-01-15",
        mesh_terms=["Neuropathic Pain"],
        abstract="This is a test abstract.",
    )
    assert p.pmid == "12345678"
    assert len(p.authors) == 2
    assert p.journal == "Nature"


# --- per-theme cache ----------------------------------------------------------

def test_theme_cache_never_shared_between_themes(tmp_path, monkeypatch):
    from crawler import search

    monkeypatch.setattr(search, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(search, "_rate_delay", 0)
    queries = []

    def fake_search_pubmed(q, since=None, max_results=0):
        queries.append(q)
        return []

    monkeypatch.setattr(search, "search_pubmed", fake_search_pubmed)
    # Neither config carries an "id": before the fix both were cached as
    # "unknown" keyed on `since` alone, so the second theme got the first's papers.
    search.search_theme({"keywords": ["KCC2 pain"], "mesh_terms": []}, since="2026-01-01")
    search.search_theme({"keywords": ["NLRP3 pain"], "mesh_terms": []}, since="2026-01-01")

    assert any("NLRP3 pain" in q for q in queries)
    assert len(list(tmp_path.glob("pubmed_*.json"))) == 2


def test_theme_cache_invalidated_when_queries_change():
    from crawler.search import _cache_path

    a = _cache_path({"id": "T01", "keywords": ["KCC2"]}, "2026-01-01", 200)
    b = _cache_path({"id": "T01", "keywords": ["KCC2", "CLP257"]}, "2026-01-01", 200)
    c = _cache_path({"id": "T01", "keywords": ["KCC2"]}, "2026-01-01", 50)
    assert len({a, b, c}) == 3
