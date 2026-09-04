# Automated Literature Crawler & Graph Updater — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a weekly automated pipeline that crawls PubMed/PMC for new publications across the 10 existing themes (plus adjacent topic discovery), extracts entities and relationships via LLM, and updates the knowledge graph (nodes, edges, verdicts) with auto-commit.

**Architecture:** A modular Python pipeline (`crawler/`) that chains: theme registry → PubMed search → abstract + PMC full-text fetch → LLM extraction → fuzzy matching against existing graph → graph update → card rebuild → test → commit. Runs weekly via cron, with adjacent MeSH-term discovery for scope expansion.

**Tech stack:** Python 3.11+, Biopython (Entrez API), NetworkX, Pydantic, rapidfuzz, pytest, LLM via OpenAI-compatible endpoint (LM Studio), PMC OA API.

## Locked design decisions (user-approved)

| Decision | Choice |
|---|---|
| Crawl frequency | Weekly (Sunday night) |
| Content depth | Abstracts + PMC full-text when available |
| Integration mode | Auto-commit with diff review |
| Journal sources | PubMed/PMC only (Biopython Entrez) |
| Discovery scope | Theme-scoped + adjacent MeSH term discovery |

## Guardrails (mandatory)

1. **Deduplication:** every processed PMID tracked in `crawler/processed_pmids.json`; re-runs are idempotent.
2. **Cost control:** LLM extraction budget cap (default 2000 calls/run); cache keyed on PMID + content hash; skip already-extracted papers.
3. **Conflict handling:** new evidence that contradicts existing CONFIRMED edges → flag in `crawler/conflicts.yaml` for human review; never auto-refute a CONFIRMED edge.
4. **Provenance:** every new node/edge carries `source_pmid`, `source_doi`, `crawled_at` timestamp.
5. **Regression safety:** after graph update, rebuild cards → run full test suite (270 tests) → only commit if all pass.

---

## File structure

```
crawler/
├── __init__.py
├── themes.yaml              # Theme definitions: keywords, MeSH terms, date ranges
├── run.py                   # CLI entry point (orchestrates full pipeline)
├── search.py                # PubMed search via Biopython Entrez
├── fetcher.py               # Abstract + PMC full-text fetcher
├── extractor.py             # LLM entity/relationship extraction
├── matcher.py               # Fuzzy match extracted entities vs existing graph
├── updater.py               # Graph update logic (add nodes/edges, update verdicts)
├── discovery.py             # Adjacent MeSH term discovery
├── conflict.py              # Conflict detection and resolution
├── processed_pmids.json     # Dedup tracking (PMID → last_seen_date)
├── discovered_mesh.yaml     # Newly discovered MeSH terms for theme expansion
├── conflicts.yaml           # Conflicting evidence requiring human review
├── cache/                   # LLM extraction cache (PMID → extracted JSON)
├── logs/                    # Per-run logs
└── tests/
    ├── __init__.py
    ├── test_search.py
    ├── test_fetcher.py
    ├── test_matcher.py
    └── test_updater.py
```

---

## Phase 1 — Foundation: Theme Registry & PubMed Search

### Task 1.1: Create theme registry (`crawler/themes.yaml`)
Define search strategy per theme. Each theme entry contains:
- `theme_id`: e.g., `T01`
- `name`: e.g., `spinal_disinhibition_KCC2_PV_SST`
- `keywords`: list of 5-10 search query strings (derived from existing theme sweep queries)
- `mesh_terms`: list of MeSH descriptors for structured search
- `entities`: list of key entity names (for post-search relevance filtering)
- `date_range`: `{"since": "2021-01-01"}` (updates dynamically after each run)

**Source:** Extract queries from existing `analysis/literature/theme_*.md` Search Log tables. Each theme file has 10-15 PubMed queries already documented.

### Task 1.2: Implement PubMed search module (`crawler/search.py`)
- Use `Bio.Entrez` from Biopython
- `search_pubmed(query: str, since: str, max_results: int = 100) -> list[PaperMeta]`
- Returns: PMID, DOI, title, authors, journal, publication_date, MeSH terms, abstract
- Rate limiting: 3 requests/second (NCBI guidelines)
- Query builder: combine keywords + MeSH terms with AND/OR/NOT
- Dedup: skip PMIDs already in `processed_pmids.json`
- Output: `PaperMeta` Pydantic model per result

### Task 1.3: Implement fetcher module (`crawler/fetcher.py`)
- `fetch_abstract(pmid: str) -> str` — via `Bio.Entrez.efetch(db="pubmed", rettype="abstract")`
- `fetch_fulltext_pmc(pmid: str) -> str | None` — via PMC OA API:
  1. Convert PMID → PMCID via `eutils.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/`
  2. Fetch XML from `eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&rettype=xml`
  3. Parse with BeautifulSoup: extract Abstract, Methods, Results, Discussion sections
  4. Return concatenated structured text
- `fetch_paper(pmid: str) -> PaperContent` — tries full-text first, falls back to abstract
- Timeout: 30s per request; retry 2x with backoff

---

## Phase 2 — Extraction: LLM Entity/Relationship Mining

### Task 2.1: Implement extraction module (`crawler/extractor.py`)
- `extract_entities_and_edges(content: str, theme_context: list[str]) -> ExtractionResult`
- LLM prompt strategy:
  - System prompt: "Extract biological entities and regulatory relationships from this PubMed paper abstract/full-text. Focus on: [theme entities]. Output structured JSON."
  - User prompt: paper content (truncated to 8000 tokens for abstracts, 30000 for full-text)
  - Output schema (Pydantic-validated):
    ```json
    {
      "entities": [
        {"name": "KCC2", "type": "molecule", "aliases": ["SLC12A5", "KCC2"], "mentions": 3}
      ],
      "relationships": [
        {
          "subject": "BDNF",
          "predicate": "downregulates",
          "object": "KCC2",
          "sign": -1,
          "evidence_quote": "BDNF-TrkB signaling leads to KCC2 internalization",
          "confidence": "HIGH",
          "pmid": "12345678"
        }
      ],
      "key_findings": ["CLP257 restores KCC2 function in neuropathic pain models"],
      "novel_entities": ["NEW_ENTITY_NAME"]
    }
    ```
- Caching: check `cache/{pmid}_{content_hash}.json` before calling LLM
- Budget: track calls in `run_context.llm_calls`; abort extraction at budget cap
- Model: Qwen3.8-27b via LM Studio endpoint (same as simulator)

### Task 2.2: Implement entity matcher (`crawler/matcher.py`)
- `match_entity(extracted_name: str, graph: Graph) -> MatchResult`
  - Match strategy (ordered):
    1. Exact `norm_label` match
    2. Alias match (check `merged_from` lists)
    3. Gene symbol lookup (e.g., "SLC12A5" → "KCC2" via known aliases)
    4. Fuzzy match (rapidfuzz, threshold 85%)
  - Returns: `MatchResult(status="EXACT"|"FUZZY"|"NO_MATCH", node_id, confidence)`
- `match_edge(subject_id, predicate, object_id, graph) -> EdgeMatchResult`
  - Check if edge already exists (exact triple match)
  - Check if inverse edge exists (with opposite sign)
  - Returns: `EdgeMatchResult(status="EXISTS"|"INVERSE"|"NEW", edge_index, confidence)`
- Known alias registry: hand-curated `crawler/aliases.yaml` mapping gene symbols → standard names

### Task 2.3: Implement graph updater (`crawler/updater.py`)
- `update_graph(graph: Graph, extractions: list[ExtractionResult], matches: list[MatchResult]) -> UpdateReport`
- **New entity handling:**
  - If `NO_MATCH`: add as new node with `file_type: "crawled"`, `source_pmid`, `crawled_at`
  - Auto-classify `entity_type` and `compartment` using existing regex rules from `build_graph_v2.py`
  - Assign `tier` based on initial degree (0 → peripheral)
- **New edge handling:**
  - If `NEW`: add as closure edge with `origin: "auto_crawled"`, `confidence: "INFERRED"`, `validation_status: "UNREVIEWED"`
  - Include `source_pmid`, `source_doi`, `evidence_quote`, `crawled_at`
- **Existing edge updates:**
  - If `EXISTS` and new evidence CONFIRMS: bump `confidence_score` by 0.05 (cap at 1.0), set `validation_status: "CONFIRMED"`
  - If `EXISTS` and new evidence EXTENDS: add to `rationale`, bump confidence by 0.02
  - If `EXISTS` and new evidence CONTRADICTS:
    - If current status is UNREVIEWED or INFERRED → set `validation_status: "REFUTED"`, add to conflicts.yaml
    - If current status is CONFIRMED → **do NOT auto-refute**; add to `conflicts.yaml` for human review
- Output: `UpdateReport` with counts of new_nodes, new_edges, updated_edges, conflicts

---

## Phase 3 — Adjacent Discovery

### Task 3.1: Implement discovery module (`crawler/discovery.py`)
- `discover_mesh_terms(papers: list[PaperMeta], existing_mesh: set[str]) -> list[DiscoveredTerm]`
- From each crawled paper's MeSH terms:
  - Count frequency across all papers in the run
  - If MeSH term appears in ≥3 papers AND is not in existing theme registry → propose as discovery
  - Also check if term is adjacent to existing themes (co-occurs with known theme entities in same paper)
- Output: `DiscoveredTerm` objects with `term`, `frequency`, `adjacent_themes`, `example_pmids`
- Write to `crawler/discovered_mesh.yaml` for review
- User can promote discovered terms to theme registry via `crawler/promote_mesh.py` (manual step)

---

## Phase 4 — Conflict Resolution

### Task 4.1: Implement conflict module (`crawler/conflict.py`)
- `detect_conflicts(graph: Graph, extractions: list[ExtractionResult]) -> list[Conflict]`
- Conflict types:
  1. **Sign conflict:** new evidence says X activates Y, but graph has X inhibits Y
  2. **Existence conflict:** new evidence says edge doesn't exist, but graph has it
  3. **Magnitude conflict:** new evidence reports different quantitative values
- For each conflict:
  - Log to `crawler/conflicts.yaml` with: edge_id, current_status, new_evidence, pmid, recommendation
  - If current status is CONFIRMED → recommendation: "HUMAN_REVIEW"
  - If current status is INFERRED/UNREVIEWED → recommendation: "AUTO_UPDATE"
- `resolve_conflict(conflict_id, decision: str)` — manual resolution via CLI

---

## Phase 5 — Pipeline Orchestration

### Task 5.1: Implement CLI entry point (`crawler/run.py`)
```
python3 crawler/run.py                    # Full pipeline, all themes
python3 crawler/run.py --theme T01        # Single theme
python3 crawler/run.py --dry-run          # Report only, no graph changes
python3 crawler/run.py --since 2026-01-01 # Override date range
python3 crawler/run.py --budget 500       # Override LLM call budget
```
Pipeline steps:
1. Load theme registry
2. For each theme: search PubMed → fetch papers → extract entities/edges → match → update
3. Run adjacent discovery
4. Detect conflicts
5. Rebuild graph_v2.json (re-run build_graph_v2.py enrichment)
6. Rebuild simulator cards (re-run build_cards.py)
7. Run test suite (pytest)
8. If all pass: auto-commit with descriptive message
9. Generate run report (`crawler/logs/run_{date}.json`)

### Task 5.2: Set up weekly cron job
```bash
# crontab entry (Sunday 02:00)
0 2 * * 0 cd /path/to/CP_knowledge_base && python3 crawler/run.py >> crawler/logs/cron.log 2>&1
```
- Output: `crawler/logs/run_{YYYY-MM-DD}.json` with full run metrics
- Conflicts: logged to `crawler/conflicts.yaml` for Monday morning review

---

## Phase 6 — Testing & Validation

### Task 6.1: Unit tests
- `test_search.py`: PubMed query building, dedup logic, rate limiting
- `test_fetcher.py`: Abstract fetch, PMC full-text fetch, fallback logic
- `test_matcher.py`: Exact match, fuzzy match, alias resolution, no-match
- `test_updater.py`: New node creation, new edge creation, verdict update, conflict detection

### Task 6.2: Integration test
- Seed with 5 known papers (manually curated ground truth)
- Run full pipeline on these 5 papers
- Assert: correct entities extracted, correct edges added/updated, no false conflicts
- Assert: graph_v2.json updated correctly, tests pass

### Task 6.3: Dry-run validation
- `python3 crawler/run.py --dry-run` on all 10 themes
- Review proposed changes before first live run
- Verify: no unintended deletions, no duplicate nodes, conflict detection works

---

## Implementation order

| Phase | Tasks | Dependencies | Est. effort |
|---|---|---|---|
| 1 | Theme registry + search + fetcher | None | 1 session |
| 2 | Extractor + matcher + updater | Phase 1 | 2 sessions |
| 3 | Adjacent discovery | Phase 1 | 0.5 session |
| 4 | Conflict resolution | Phase 2 | 0.5 session |
| 5 | CLI orchestrator + cron | Phases 1-4 | 1 session |
| 6 | Testing + validation | All phases | 1 session |
| **Total** | | | **~6 sessions** |

## First-run deliverables

After implementation, the first live run will:
1. Search all 10 themes for papers since 2021-01-01
2. Fetch abstracts + PMC full-text for new papers
3. Extract entities and relationships via LLM
4. Add new nodes/edges to graph_v2.json
5. Update verdicts on existing edges
6. Discover adjacent MeSH terms
7. Log conflicts
8. Rebuild cards, run tests, auto-commit
9. Generate `crawler/logs/run_{date}.json` with full metrics

## Post-implementation: ongoing maintenance

- **Weekly:** Review `crawler/conflicts.yaml` for human-resolution items
- **Monthly:** Review `crawler/discovered_mesh.yaml` for theme expansion candidates
- **Quarterly:** Re-run full literature sweeps (manual) to catch papers missed by automated crawl
- **As needed:** Update `crawler/themes.yaml` with new keywords/entities as the KB evolves
