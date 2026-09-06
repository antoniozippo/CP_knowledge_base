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
