# crawler/tests/test_fetcher.py

import pytest
from crawler.fetcher import PaperContent


def test_paper_content_creation():
    pc = PaperContent(
        pmid="12345678",
        pmcid="PMC9999999",
        abstract_text="Test abstract.",
        fulltext_xml=None,
        fulltext_sections=None,
        is_fulltext=False,
    )
    assert pc.pmid == "12345678"
    assert pc.is_fulltext is False


def test_paper_content_fulltext():
    pc = PaperContent(
        pmid="12345678",
        pmcid="PMC9999999",
        abstract_text="Test abstract.",
        fulltext_xml="<article><body></body></article>",
        fulltext_sections={"Introduction": "intro text", "Methods": "methods text"},
        is_fulltext=True,
    )
    assert pc.is_fulltext is True
    assert "Introduction" in pc.fulltext_sections


# --- text extraction and request economy --------------------------------------

JATS = """<article><body>
<sec><title>Results</title><p>KCC2 <italic>in vivo</italic> was <bold>reduced</bold> by 40%.</p></sec>
<sec><title>Acknowledgments</title><p>We thank the funders.</p></sec>
<sec><title>Funding</title><p>Grant 123.</p></sec>
<sec><title>Discussion</title><p>Loss of   KCC2 drives allodynia.</p></sec>
</body></article>"""


def test_pmc_text_keeps_spacing_at_inline_tags_and_drops_back_matter(monkeypatch):
    from types import SimpleNamespace
    from crawler import fetcher

    monkeypatch.setattr(fetcher, "_get_with_retry", lambda url, params=None: SimpleNamespace(text=JATS))
    sections = fetcher.fetch_pmc_fulltext("PMC1")
    assert sections == {
        "Results": "KCC2 in vivo was reduced by 40%.",
        "Discussion": "Loss of KCC2 drives allodynia.",
    }


def test_paper_meta_reuses_abstract_and_skips_id_converter(monkeypatch, tmp_path):
    from crawler import fetcher
    from crawler.search import PaperMeta

    calls = []
    monkeypatch.setattr(fetcher, "_fetch_abstract_xml", lambda pmid: calls.append("abstract") or "x")
    monkeypatch.setattr(fetcher, "pmid_to_pmcid", lambda pmid: calls.append("idconv") or None)
    monkeypatch.setattr(fetcher, "fetch_pmc_fulltext", lambda pmcid: calls.append(pmcid) or {"Results": "r"})
    monkeypatch.setattr(fetcher.time, "sleep", lambda s: None)
    metas = [
        PaperMeta(pmid="1", doi=None, title="t", authors=[], journal="j", publication_date="2026",
                  mesh_terms=[], abstract="meta abstract", pmcid=None),
        PaperMeta(pmid="2", doi=None, title="t", authors=[], journal="j", publication_date="2026",
                  mesh_terms=[], abstract="meta abstract 2", pmcid="PMC9"),
    ]
    out = fetcher.fetch_papers(metas, cache_dir=tmp_path)
    assert calls == ["PMC9"]  # no abstract efetch, no ID converter
    assert [p.abstract_text for p in out] == ["meta abstract", "meta abstract 2"]
    assert [p.is_fulltext for p in out] == [False, True]
