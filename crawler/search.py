# crawler/search.py - PubMed search via Biopython Entrez

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from Bio import Entrez

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entrez configuration
# ---------------------------------------------------------------------------
Entrez.email = os.environ.get("NCBI_EMAIL", "cp-knowledge-base@example.com")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")
BATCH_SIZE = 100
RATE_LIMIT_NO_KEY = 0.35   # 3 req/s
RATE_LIMIT_WITH_KEY = 0.10  # 10 req/s
_rate_delay = RATE_LIMIT_WITH_KEY if NCBI_API_KEY else RATE_LIMIT_NO_KEY

if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY

CACHE_DIR = Path(__file__).resolve().parent / "cache"
PROCESSED_PMIDS_PATH = Path(__file__).resolve().parent / "processed_pmids.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class PaperMeta:
    pmid: str
    doi: Optional[str]
    title: str
    authors: list[str]
    journal: str
    publication_date: str  # YYYY-MM-DD or YYYY-MM
    mesh_terms: list[str]
    abstract: str
    pmcid: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_processed_pmids() -> set[str]:
    if PROCESSED_PMIDS_PATH.exists():
        return set(json.loads(PROCESSED_PMIDS_PATH.read_text()))
    return set()


def _save_processed_pmids(pmids: set[str]) -> None:
    PROCESSED_PMIDS_PATH.write_text(json.dumps(sorted(pmids), indent=2))


def _cache_path(theme_id: str, since: str) -> Path:
    qhash = hashlib.sha256(since.encode()).hexdigest()[:12]
    return CACHE_DIR / f"pubmed_{theme_id}_{qhash}.json"


def _cache_read(path: Path) -> list[PaperMeta] | None:
    if path.exists():
        data = json.loads(path.read_text())
        return [PaperMeta(**item) for item in data]
    return None


def _cache_write(path: Path, papers: list[PaperMeta]) -> None:
    _ensure_dirs()
    path.write_text(json.dumps([asdict(p) for p in papers], indent=2))


def _parse_article(article: dict) -> PaperMeta:
    """Extract a PaperMeta from an Entrez parsed article record."""
    medline = article.get("MedlineCitation", {})
    article_data = medline.get("Article", {})

    # PMID
    pmid = str(medline.get("PMID", ""))

    # Title
    title = article_data.get("ArticleTitle", "")
    if isinstance(title, list):
        title = " ".join(str(t) for t in title)

    # Authors
    authors: list[str] = []
    author_list = article_data.get("AuthorList", [])
    if not isinstance(author_list, list):
        author_list = [author_list]
    for author in author_list:
        if not isinstance(author, dict):
            continue
        last = author.get("LastName", "")
        fore = author.get("ForeName", "")
        name = f"{last} {fore}".strip()
        if name:
            authors.append(name)

    # Journal
    journal = article_data.get("Journal", {}).get("Title", "")

    # Publication date
    pub_date = article_data.get("Journal", {}).get("JournalIssue", {}).get(
        "PubDate", {}
    )
    year = pub_date.get("Year", "")
    month = pub_date.get("Month", "01")
    day = pub_date.get("Day", "01")
    if year:
        # Month may be a string like "Jan"
        month_map = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        }
        month_str = month_map.get(str(month).lower()[:3], str(month).zfill(2))
        if str(day).isdigit() and str(month).isdigit():
            publication_date = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        elif str(day).isdigit():
            publication_date = f"{year}-{month_str}-{str(day).zfill(2)}"
        else:
            publication_date = f"{year}-{month_str}"
    else:
        publication_date = ""

    # MeSH terms
    mesh_terms: list[str] = []
    mesh_list = medline.get("MeshHeadingList", [])
    if not isinstance(mesh_list, list):
        mesh_list = [mesh_list]
    for mesh in mesh_list:
        heading = mesh if isinstance(mesh, dict) else {}
        descriptor = heading.get("DescriptorName") or heading.get("MeshHeading", {}).get("DescriptorName", "")
        if descriptor:
            mesh_terms.append(str(descriptor))

    # Abstract
    abstract_parts: list[str] = []
    abs_text_list = article_data.get("Abstract", {}).get("AbstractText", [])
    if not isinstance(abs_text_list, list):
        abs_text_list = [abs_text_list]
    for abs_text in abs_text_list:
        if isinstance(abs_text, dict):
            label = abs_text.get("@Label", "")
            text = abs_text.get("#text", "")
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        else:
            abstract_parts.append(str(abs_text))
    abstract = "\n".join(abstract_parts)

    # DOI
    doi: Optional[str] = None
    eids = article_data.get("ELocationID", [])
    if not isinstance(eids, list):
        eids = [eids]
    for eid in eids:
        if isinstance(eid, dict) and eid.get("@EIdType") == "doi":
            doi = eid.get("#text") or str(eid.get("#text", "")) or ""
            if not doi:
                doi = str(eid)
            break
    if not doi:
        for id_obj in article.get("PubmedData", {}).get("ArticleIdList", []):
            if getattr(id_obj, "attributes", {}).get("IdType") == "doi":
                doi = str(id_obj)
                break

    # PMCID
    pmcid: Optional[str] = None
    for id_obj in article.get("PubmedData", {}).get("ArticleIdList", []):
        if getattr(id_obj, "attributes", {}).get("IdType") == "pmc":
            pmcid = str(id_obj)
            break

    return PaperMeta(
        pmid=pmid,
        doi=doi,
        title=title,
        authors=authors,
        journal=journal,
        publication_date=publication_date,
        mesh_terms=mesh_terms,
        abstract=abstract,
        pmcid=pmcid,
    )


def _fetch_batch(ids: list[str]) -> list[PaperMeta]:
    """Fetch a batch of PubMed articles by PMID list."""
    if not ids:
        return []

    handle = Entrez.efetch(
        db="pubmed",
        id=",".join(ids),
        rettype="xml",
        retmode="xml",
    )
    records = Entrez.read(handle)
    handle.close()

    papers: list[PaperMeta] = []
    for article in records.get("PubmedArticle", []):
        try:
            papers.append(_parse_article(article))
        except Exception:
            log.warning("Failed to parse article record", exc_info=True)
    return papers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _pubmed_date(since: str) -> str:
    """Normalize YYYY-MM-DD or YYYY-MM to PubMed's YYYY/MM/DD format."""
    s = since.strip()
    s = s.replace("-", "/")
    if s.count("/") == 1:
        return f"{s}/01"
    return s


def build_pubmed_query(
    keywords: list[str],
    mesh_terms: list[str],
    since: str = "2021-01-01",
) -> str:
    """Build a PubMed query from keyword list and MeSH terms.

    Strategy: (keyword1 OR keyword2 OR ...) AND (mesh1 OR mesh2 OR ...)
    AND (date filter). Each keyword is a quoted phrase.

    Note: for better recall, `search_theme` runs each keyword and MeSH
    term as its own query and unions the PMIDs. This builder is kept for
    single-query use and tests.
    """
    parts: list[str] = []

    if keywords:
        kw_group = " OR ".join(f'"{kw}"' for kw in keywords)
        parts.append(f"({kw_group})")

    if mesh_terms:
        mesh_group = " OR ".join(
            f"{mt}[MeSH Terms]" for mt in mesh_terms
        )
        parts.append(f"({mesh_group})")

    if since:
        parts.append(f"({_pubmed_date(since)}:3000[dp])")

    query = " AND ".join(parts)
    return query


def _build_single_queries(
    theme_config: dict, since: str
) -> list[tuple[str, str]]:
    """Build one query per keyword and per MeSH term (for unioned recall).

    Returns list of (query_label, query_string).
    """
    keywords = theme_config.get("keywords", [])
    mesh_terms = theme_config.get("mesh_terms", [])
    queries: list[tuple[str, str]] = []
    since_fmt = _pubmed_date(since) if since else ""

    for i, kw in enumerate(keywords):
        q = f"({kw})"
        if since_fmt:
            q += f" AND ({since_fmt}:3000[dp])"
        queries.append((f"kw{i}", q))

    for i, mt in enumerate(mesh_terms):
        q = f"{mt}[MeSH Terms]"
        if since_fmt:
            q += f" AND ({since_fmt}:3000[dp])"
        queries.append((f"mesh{i}", q))

    return queries


def search_pubmed(
    query: str,
    since: str = "2021-01-01",
    max_results: int = 200,
) -> list[PaperMeta]:
    """Search PubMed and return paper metadata including abstracts.

    Uses Entrez.esearch + Entrez.efetch in batches of 100.
    Rate limit: 0.35s between requests (3 req/s without API key).
    Returns list of PaperMeta.
    """
    if not query.strip():
        return []

    log.info("Executing PubMed search (max_results=%d)", max_results)

    # Step 1: search to get PMIDs and total count
    search_handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        usehistory="y",
        sort="relevance",
    )
    search_results = Entrez.read(search_handle)
    search_handle.close()

    total = int(search_results.get("Count", 0))
    id_list = search_results.get("IdList", [])
    web_env = search_results.get("WebEnv", "")
    query_key = search_results.get("QueryKey", "")

    log.info("PubMed search returned %d results (fetching up to %d)", total, max_results)

    if not id_list:
        return []

    # Step 2: fetch in batches using WebEnv for large result sets
    all_papers: list[PaperMeta] = []
    for start in range(0, len(id_list), BATCH_SIZE):
        batch_ids = id_list[start : start + BATCH_SIZE]
        try:
            batch = _fetch_batch(batch_ids)
            all_papers.extend(batch)
        except Exception:
            log.warning("Failed to fetch batch starting at %d", start, exc_info=True)
        time.sleep(_rate_delay)

    log.info("Fetched %d papers total", len(all_papers))
    return all_papers


def search_theme(
    theme_config: dict,
    since: str | None = None,
    max_results: int = 200,
    cache: bool = True,
) -> list[PaperMeta]:
    """Search for a single theme using its keywords and MeSH terms.

    Runs one query per keyword and per MeSH term, then unions by PMID.
    This maximizes recall compared to AND-combining all terms.
    Optionally caches results per theme.
    """
    theme_id = theme_config.get("id", "unknown")
    effective_since = since or "2021-01-01"

    if cache:
        _ensure_dirs()
        cp = _cache_path(theme_id, effective_since)
        cached = _cache_read(cp)
        if cached is not None:
            log.info("Cache hit for theme %s (%d papers)", theme_id, len(cached))
            return cached

    query_specs = _build_single_queries(theme_config, effective_since)
    if not query_specs:
        log.info("No keywords or MeSH terms for theme %s", theme_id)
        return []

    # Union of PMIDs across all per-term queries
    pmid_order: list[str] = []
    for label, q in query_specs:
        try:
            papers = search_pubmed(q, since=effective_since, max_results=max_results)
            for p in papers:
                if p.pmid not in pmid_order:
                    pmid_order.append(p.pmid)
            log.info("  %s: %d papers (%d unique so far)", label, len(papers), len(pmid_order))
        except Exception as exc:
            log.warning("Query %s failed: %s", label, exc)
        time.sleep(_rate_delay)

    # Fetch all unique PMIDs in one batch via efetch
    all_papers: list[PaperMeta] = []
    for start in range(0, len(pmid_order), BATCH_SIZE):
        batch_ids = pmid_order[start : start + BATCH_SIZE]
        try:
            all_papers.extend(_fetch_batch(batch_ids))
        except Exception as exc:
            log.warning("Failed to fetch batch starting at %d: %s", start, exc)

    # Sort by recency (publication date desc)
    all_papers.sort(key=lambda p: p.publication_date, reverse=True)

    if cache:
        cp = _cache_path(theme_id, effective_since)
        _cache_write(cp, all_papers)
        log.info("Cached %d papers for theme %s", len(all_papers), theme_id)

    return all_papers


def search_themes(
    themes: dict,
    since: str | None = None,
    max_results: int = 200,
    cache: bool = True,
) -> dict[str, list[PaperMeta]]:
    """Search across all themes defined in themes.yaml.

    Returns dict mapping theme_id -> list[PaperMeta].
    Deduplicates by PMID within each theme.
    """
    results: dict[str, list[PaperMeta]] = {}

    for theme_id, theme_data in themes.items():
        log.info("Searching theme: %s (%s)", theme_id, theme_data.get("name", ""))
        theme_config = {**theme_data, "id": theme_id}
        papers = search_theme(
            theme_config,
            since=since,
            max_results=max_results,
            cache=cache,
        )

        # Deduplicate within theme by PMID
        seen_pmids: set[str] = set()
        deduped: list[PaperMeta] = []
        for p in papers:
            if p.pmid not in seen_pmids:
                seen_pmids.add(p.pmid)
                deduped.append(p)

        results[theme_id] = deduped
        log.info(
            "Theme %s: %d unique papers", theme_id, len(deduped)
        )

    return results
