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
