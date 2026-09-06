#!/usr/bin/env python3
# crawler/run.py - CLI orchestrator for the automated literature crawler

import argparse
import json
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

# Allow direct execution: `python3 crawler/run.py`
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

from crawler.search import search_theme, PaperMeta, _load_processed_pmids, _save_processed_pmids
from crawler.fetcher import fetch_papers, PaperContent
from crawler.extractor import LLMExtractor, extract_batch, ExtractionResult
from crawler.matcher import EntityMatcher
from crawler.updater import GraphUpdater
from crawler.discovery import MeshDiscovery
from crawler.conflict import ConflictManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawler/logs/crawler.log"),
    ],
)
log = logging.getLogger(__name__)


def load_themes(themes_path: str = "crawler/themes.yaml") -> dict:
    return yaml.safe_load(Path(themes_path).read_text()) or {}


def run_pipeline(args, themes=None):
    """Execute the full crawl-extract-update pipeline."""
    start = time.time()
    if themes is None:
        themes = load_themes(args.themes_path)

    log.info(f"Crawler starting — {len(themes)} themes, budget={args.budget}, dry_run={args.dry_run}")

    # --- Phase 1: Search ---
    log.info("=== Phase 1: PubMed Search ===")
    all_papers: list[PaperMeta] = []
    for theme_id, theme_config in themes.items():
        log.info(f"  Searching {theme_id}: {theme_config['name']}")
        papers = search_theme(theme_config, since=args.since, max_results=args.max_results)
        all_papers.extend(papers)
        log.info(f"    Found {len(papers)} papers")

    # Deduplicate across themes by PMID
    seen_pmids = set()
    unique_papers = []
    for p in all_papers:
        if p.pmid not in seen_pmids:
            seen_pmids.add(p.pmid)
            unique_papers.append(p)
    log.info(f"  Total unique papers: {len(unique_papers)}")

    # --- Phase 2: Fetch ---
    log.info("=== Phase 2: Fetch Abstracts + Full-text ===")
    contents = fetch_papers(unique_papers, cache_dir=Path("crawler/cache"))
    fulltext_count = sum(1 for c in contents if c.is_fulltext)
    log.info(f"  Fetched {len(contents)} papers ({fulltext_count} with full-text)")

    # --- Phase 3: Extract ---
    log.info("=== Phase 3: LLM Entity/Relationship Extraction ===")
    if args.dry_run:
        log.info("  DRY RUN — skipping LLM extraction")
        extractions = []
    else:
        # Skip papers already successfully extracted in previous runs
        processed = _load_processed_pmids()
        to_extract = [c for c in contents if c.pmid not in processed]
        log.info(f"  {len(contents)} papers fetched, {len(to_extract)} not yet extracted")
        extractor = LLMExtractor(
            endpoint=args.llm_endpoint,
            model=args.llm_model,
            max_tokens=args.llm_max_tokens,
            cache_dir=Path("crawler/cache"),
        )
        all_extractions = []
        for theme_id, theme_config in themes.items():
            theme_entities = theme_config.get("entities", [])
            theme_papers = [c for c in to_extract if any(
                t in c.abstract.lower() for t in [e.lower() for e in theme_entities]
            )]
            log.info(f"  Extracting from {len(theme_papers)} papers for {theme_id}")
            extracted = extract_batch(
                theme_papers, theme_config, args.llm_endpoint, args.llm_model,
                budget=args.budget - extractor.call_count,
                cache_dir=Path("crawler/cache"),
            )
            all_extractions.extend(extracted)
        extractions = all_extractions
        log.info(f"  Extracted from {len(extractions)} papers ({extractor.call_count} LLM calls)")

        # Mark successfully extracted PMIDs as processed (dedupe for future runs)
        processed.update({e.pmid for e in extractions})
        _save_processed_pmids(processed)

    # --- Phase 4: Match ---
    log.info("=== Phase 4: Match Against Existing Graph ===")
    matcher = EntityMatcher(graph_path="graphify-out/graph_v2.json")
    entity_matches, edge_matches = matcher.match_batch(extractions)
    new_entities = sum(1 for m in entity_matches if m.status == "NO_MATCH")
    new_edges = sum(1 for m in edge_matches if m.status == "NEW")
    log.info(f"  New entities: {new_entities}, New edges: {new_edges}")

    # --- Phase 5: Update Graph ---
    log.info("=== Phase 5: Update Graph ===")
    if args.dry_run:
        log.info("  DRY RUN — skipping graph update")
        report = {"new_nodes": new_entities, "new_edges": new_edges, "skipped": len(entity_matches)}
    else:
        updater = GraphUpdater(graph_path="graphify-out/graph_v2.json")
        report = updater.update(entity_matches, edge_matches, extractions)
        updater.save()
        log.info(f"  Update: +{report.new_nodes} nodes, +{report.new_edges} edges, "
                 f"~{report.updated_edges} updated, {report.conflicts} conflicts")

    # --- Phase 6: Conflict Detection ---
    log.info("=== Phase 6: Conflict Detection ===")
    conflict_mgr = ConflictManager(conflicts_path="crawler/conflicts.yaml")
    conflict_summary = conflict_mgr.summary()
    log.info(f"  Conflicts: {conflict_summary['pending']} pending, "
             f"{conflict_summary['human_review']} need review")

    # --- Phase 7: Adjacent Discovery ---
    log.info("=== Phase 7: MeSH Discovery ===")
    discovery = MeshDiscovery(themes_path="crawler/themes.yaml")
    discoveries = discovery.discover(unique_papers, min_frequency=args.min_mesh_freq)
    if discoveries and not args.dry_run:
        discovery.save_discoveries(discoveries, output_path="crawler/discovered_mesh.yaml")
    log.info(f"  Discovered {len(discoveries)} new MeSH terms")

    # --- Phase 8: Run Tests ---
    log.info("=== Phase 8: Run Tests ===")
    if not args.dry_run:
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "pytest", "simulator/tests/", "-x", "-q"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            log.error(f"  Tests FAILED:\n{result.stdout}\n{result.stderr}")
            log.error("  Aborting commit — fix tests first")
            return 1
        log.info("  All tests pass")

    # --- Phase 9: Commit ---
    elapsed = time.time() - start
    run_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "themes_searched": list(themes.keys()),
        "papers_found": len(unique_papers),
        "papers_fetched": len(contents),
        "fulltext_count": fulltext_count,
        "extractions": len(extractions),
        "new_entities": new_entities,
        "new_edges": new_edges,
        "conflicts": conflict_summary,
        "discoveries": len(discoveries),
        "elapsed_sec": round(elapsed, 1),
        "dry_run": args.dry_run,
    }

    # Save run log
    log_dir = Path("crawler/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = log_dir / f"run_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json"
    run_log_path.write_text(json.dumps(run_log, indent=2))
    log.info(f"  Run log: {run_log_path}")

    if not args.dry_run:
        import subprocess
        # Stage and commit
        subprocess.run(["git", "add", "graphify-out/graph_v2.json"], check=True)
        subprocess.run(["git", "add", "crawler/conflicts.yaml", "crawler/discovered_mesh.yaml",
                        "crawler/processed_pmids.json"], check=True)
        subprocess.run(["git", "add", str(run_log_path)], check=True)

        commit_msg = (f"feat(crawler): auto-update graph — "
                      f"{len(extractions)} papers, +{new_entities} nodes, +{new_edges} edges")
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        log.info(f"  Committed: {commit_msg}")

    log.info(f"Pipeline complete in {elapsed:.1f}s")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Automated PubMed/PMC literature crawler and graph updater",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 crawler/run.py                          # Full pipeline, all themes
  python3 crawler/run.py --theme T01              # Single theme
  python3 crawler/run.py --dry-run                # Report only, no changes
  python3 crawler/run.py --since 2026-01-01       # Override date range
  python3 crawler/run.py --budget 500             # Override LLM budget
  python3 crawler/run.py --min-mesh-freq 5        # Higher discovery threshold
        """,
    )
    parser.add_argument("--theme", action="append", dest="themes",
                        help="Theme ID(s) to search (default: all)")
    parser.add_argument("--themes-path", default="crawler/themes.yaml",
                        help="Path to themes.yaml (default: crawler/themes.yaml)")
    parser.add_argument("--since", default="2021-01-01",
                        help="Start date for PubMed search (default: 2021-01-01)")
    parser.add_argument("--max-results", type=int, default=200,
                        help="Max results per theme query (default: 200)")
    parser.add_argument("--budget", type=int, default=2000,
                        help="LLM call budget per run (default: 2000)")
    parser.add_argument("--llm-endpoint", default="http://192.168.1.13:1234",
                        help="LLM API endpoint (default: http://192.168.1.13:1234)")
    parser.add_argument("--llm-model", default="qwen/qwen3.8-27b",
                        help="LLM model name (default: qwen/qwen3.8-27b)")
    parser.add_argument("--llm-max-tokens", type=int, default=4096,
                        help="Max tokens for LLM extraction (default: 4096)")
    parser.add_argument("--min-mesh-freq", type=int, default=3,
                        help="Min frequency for MeSH discovery (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only, no graph changes or commits")
    args = parser.parse_args()

    # Filter themes if specified
    if args.themes:
        all_themes = load_themes(args.themes_path)
        filtered = {k: v for k, v in all_themes.items() if k in args.themes}
        if not filtered:
            print(f"Error: no valid themes in {args.themes}", file=sys.stderr)
            sys.exit(1)
        sys.exit(run_pipeline(args, themes=filtered))
    else:
        sys.exit(run_pipeline(args))


if __name__ == "__main__":
    main()
