# crawler/fetcher.py - Abstract + PMC full-text fetcher

import hashlib
import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import requests
from Bio import Entrez
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

Entrez.email = os.environ.get("NCBI_EMAIL", "cp-knowledge-base@example.com")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

CACHE_DIR = Path(__file__).resolve().parent / "cache"
RATE_LIMIT_DELAY = 0.10 if NCBI_API_KEY else 0.35
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_BACKOFF = 5

ID_CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
PMC_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class PaperContent:
    pmid: str
    pmcid: Optional[str]
    abstract_text: str
    fulltext_xml: Optional[str]  # Raw XML from PMC if available
    fulltext_sections: Optional[dict[str, str]] = None  # {section_name: text}
    is_fulltext: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(pmid: str) -> Path:
    _ensure_dirs()
    return CACHE_DIR / f"paper_{pmid}.json"


def _cache_read(pmid: str) -> PaperContent | None:
    path = _cache_path(pmid)
    if path.exists():
        data = json.loads(path.read_text())
        return PaperContent(**data)
    return None


def _cache_write(paper: PaperContent) -> None:
    _ensure_dirs()
    path = _cache_path(paper.pmid)
    path.write_text(json.dumps(asdict(paper), indent=2))


def _get_with_retry(url: str, params: dict | None = None) -> requests.Response | None:
    """GET with retry logic and backoff."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = RETRY_BACKOFF * (attempt + 1)
                log.warning("Rate limited (429), waiting %ds", wait)
                time.sleep(wait)
                continue
            log.warning(
                "HTTP %d for %s (attempt %d/%d)",
                resp.status_code, url, attempt + 1, MAX_RETRIES + 1,
            )
        except requests.RequestException as exc:
            log.warning(
                "Request error for %s (attempt %d/%d): %s",
                url, attempt + 1, MAX_RETRIES + 1, exc,
            )
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def pmid_to_pmcid(pmid: str) -> Optional[str]:
    """Convert PMID to PMCID using NCBI ID Converter API.

    Returns PMCID (e.g. "PMC1234567") or None if not in PMC.
    """
    if not pmid:
        return None

    resp = _get_with_retry(
        ID_CONVERTER_URL,
        params={"ids": pmid, "format": "json"},
    )
    if resp is None:
        return None

    try:
        data = resp.json()
        records = data.get("records", [])
        if records:
            pmcid = records[0].get("pmcid")
            if pmcid:
                return pmcid
    except (json.JSONDecodeError, KeyError, IndexError):
        log.warning("Failed to parse ID converter response for PMID %s", pmid)

    return None


def fetch_abstract(pmid: str) -> str:
    """Fetch abstract text from PubMed.

    Uses Bio.Entrez.efetch with rettype="abstract".
    """
    if not pmid:
        return ""

    try:
        handle = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="abstract",
            retmode="text",
        )
        text = handle.read()
        handle.close()
        return text.strip()
    except Exception:
        log.warning("Failed to fetch abstract for PMID %s", pmid, exc_info=True)
        return ""


def _fetch_abstract_xml(pmid: str) -> str:
    """Fetch abstract via XML to get structured text. Falls back to text."""
    try:
        handle = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="xml",
            retmode="xml",
        )
        raw_xml = handle.read()
        handle.close()

        root = ET.fromstring(raw_xml)
        abstract_parts: list[str] = []

        for abs_elem in root.iter("AbstractText"):
            label = abs_elem.get("Label", "")
            text = "".join(abs_elem.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)

        if abstract_parts:
            return "\n".join(abstract_parts)
    except Exception:
        log.debug("XML abstract fetch failed for PMID %s, falling back", pmid)

    return fetch_abstract(pmid)


def fetch_pmc_fulltext(pmcid: str) -> Optional[dict[str, str]]:
    """Fetch full-text XML from PMC OA API.

    Parse JATS XML to extract sections:
    Abstract, Introduction, Methods, Results, Discussion, Conclusion.

    Uses BeautifulSoup for JATS XML parsing.
    Section tags: <sec>, <title>, <p>
    """
    if not pmcid:
        return None

    # Strip "PMC" prefix if present for the fetch URL
    numeric_id = pmcid.replace("PMC", "")

    resp = _get_with_retry(
        PMC_EFETCH_URL,
        params={"db": "pmc", "rettype": "xml", "id": numeric_id},
    )
    if resp is None:
        return None

    raw_xml = resp.text
    if not raw_xml.strip():
        return None

    try:
        soup = BeautifulSoup(raw_xml, "xml")
    except Exception:
        # Fallback to html.parser if lxml not available
        try:
            soup = BeautifulSoup(raw_xml, "html.parser")
        except Exception:
            log.warning("Failed to parse PMC XML for %s", pmcid)
            return None

    body = soup.find("body")
    if not body:
        return None

    # Section name normalization
    section_aliases: dict[str, str] = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "background": "Introduction",
        "methods": "Methods",
        "materials and methods": "Methods",
        "material and methods": "Methods",
        "experimental procedures": "Methods",
        "methodology": "Methods",
        "results": "Results",
        "results and discussion": "Results and Discussion",
        "discussion": "Discussion",
        "conclusions": "Conclusion",
        "conclusion": "Conclusion",
        "summary": "Conclusion",
        "supplementary material": "Supplementary Material",
        "supplementary materials": "Supplementary Material",
        "acknowledgments": "Acknowledgments",
        "acknowledgements": "Acknowledgments",
        "funding": "Funding",
    }

    sections: dict[str, str] = {}
    section_counter: dict[str, int] = {}

    def _extract_section_text(sec_element) -> str:
        """Extract all paragraph text from a <sec> element."""
        paragraphs: list[str] = []
        for p in sec_element.find_all("p", recursive=False):
            text = " ".join(p.get_text(strip=True).split())
            if text:
                paragraphs.append(text)
        # Also handle nested sections
        for nested in sec_element.find_all("sec", recursive=False):
            paragraphs.append(_extract_section_text(nested))
        return "\n".join(paragraphs)

    def _normalize_section_name(title_text: str) -> str:
        """Map raw section title to canonical name."""
        lower = title_text.strip().lower()
        for alias, canonical in section_aliases.items():
            if alias in lower:
                return canonical
        return title_text.strip()

    # Process top-level sections
    for sec in body.find_all("sec", recursive=False):
        title_elem = sec.find("title", recursive=False)
        if title_elem:
            raw_name = title_elem.get_text(strip=True)
            section_name = _normalize_section_name(raw_name)
        else:
            section_name = "Unnamed Section"

        # Deduplicate section names
        if section_name in section_counter:
            section_counter[section_name] += 1
            section_name = f"{section_name} ({section_counter[section_name]})"
        else:
            section_counter[section_name] = 1

        text = _extract_section_text(sec)
        if text:
            sections[section_name] = text

    # If no <sec> elements, try flat <p> extraction
    if not sections:
        all_paragraphs: list[str] = []
        for p in body.find_all("p", recursive=False):
            text = " ".join(p.get_text(strip=True).split())
            if text:
                all_paragraphs.append(text)
        if all_paragraphs:
            sections["Body"] = "\n".join(all_paragraphs)

    return sections if sections else None


def fetch_paper(pmid: str, use_cache: bool = True) -> PaperContent:
    """Fetch paper content: abstract always, full-text if available in PMC.

    Try full-text first; fall back to abstract-only.
    Cache results to avoid re-fetching.
    """
    if use_cache:
        cached = _cache_read(pmid)
        if cached is not None:
            log.debug("Cache hit for PMID %s", pmid)
            return cached

    # Fetch abstract
    abstract = _fetch_abstract_xml(pmid)

    # Try PMC full-text
    pmcid: Optional[str] = None
    fulltext_xml: Optional[str] = None
    fulltext_sections: Optional[dict[str, str]] = None
    is_fulltext = False

    # Check if PMID already has a PMCID (from search results)
    # If not, try to convert
    pmcid = pmid_to_pmcid(pmid)
    time.sleep(RATE_LIMIT_DELAY)

    if pmcid:
        sections = fetch_pmc_fulltext(pmcid)
        time.sleep(RATE_LIMIT_DELAY)

        if sections:
            fulltext_sections = sections
            # Reconstruct raw-ish XML from sections for storage
            fulltext_xml = json.dumps(sections)
            is_fulltext = True

    paper = PaperContent(
        pmid=pmid,
        pmcid=pmcid,
        abstract_text=abstract,
        fulltext_xml=fulltext_xml,
        fulltext_sections=fulltext_sections,
        is_fulltext=is_fulltext,
    )

    if use_cache:
        _cache_write(paper)

    return paper


def fetch_papers(
    papers: list,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> list[PaperContent]:
    """Batch fetch papers with dedup and caching.

    Skips already-cached PMIDs.
    Accepts list of PaperMeta (or any object with a .pmid attribute)
    or a list of dicts with a "pmid" key.
    Returns list of PaperContent.
    """
    if cache_dir is not None:
        global CACHE_DIR
        CACHE_DIR = cache_dir
        _ensure_dirs()

    results: list[PaperContent] = []
    seen_pmids: set[str] = set()

    for item in papers:
        # Handle both dataclass and dict inputs
        if isinstance(item, dict):
            pmid = item.get("pmid", "")
        else:
            pmid = getattr(item, "pmid", "")

        if not pmid or pmid in seen_pmids:
            continue
        seen_pmids.add(pmid)

        # Skip if already cached
        if use_cache:
            cached = _cache_read(pmid)
            if cached is not None:
                results.append(cached)
                continue

        paper = fetch_paper(pmid, use_cache=use_cache)
        results.append(paper)

        status = "fulltext" if paper.is_fulltext else "abstract-only"
        log.info("Fetched PMID %s [%s]", pmid, status)

    total = len(results)
    fulltext_count = sum(1 for p in results if p.is_fulltext)
    log.info(
        "Batch fetch complete: %d papers, %d with full-text (%.0f%%)",
        total,
        fulltext_count,
        (fulltext_count / total * 100) if total else 0,
    )

    return results
