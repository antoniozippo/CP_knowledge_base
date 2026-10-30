#!/usr/bin/env python3
# crawler/batch_extract.py - full-corpus extraction through the Claude Message Batches API
#
#   python3 crawler/batch_extract.py submit  [--since 2021-01-01] [--limit N] [--theme T01 ...]
#   python3 crawler/batch_extract.py status  --batch-id msgbatch_...
#   python3 crawler/batch_extract.py collect --batch-id msgbatch_...
#   python3 crawler/run.py --since 2021-01-01 --no-commit     # consumes the cache
#
# submit runs search + fetch (both cached), selects papers exactly as run.py
# does, skips papers already extracted or cached, and submits one batch.
# collect writes each result into the extractor cache, where run.py finds it
# as a free cache hit and applies quote verification, matching and the graph
# update as usual. Requires CRAWLER_ANTHROPIC_API_KEY (see anthropic_backend.py).

import argparse
import json
import logging
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from crawler.anthropic_backend import (  # noqa: E402
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    collect_batch,
    make_client,
    prepare_batch_items,
    submit_batch,
    write_manifest,
)
from crawler.fetcher import fetch_papers  # noqa: E402
from crawler.run import (  # noqa: E402
    build_extraction_inputs,
    load_themes,
    search_all,
    select_for_extraction,
)
from crawler.search import _load_processed_pmids  # noqa: E402

log = logging.getLogger(__name__)
CACHE_DIR = Path("crawler/cache")
MANIFEST_DIR = Path("crawler/logs/batches")


def _manifest_path(batch_id: str) -> Path:
    return MANIFEST_DIR / f"{batch_id}.json"


def cmd_submit(args) -> int:
    themes = load_themes(args.themes_path)
    if args.themes:
        themes = {k: v for k, v in themes.items() if k in args.themes}
    papers = search_all(themes, args.since, args.max_results)
    contents = fetch_papers(papers, cache_dir=CACHE_DIR)
    processed = _load_processed_pmids()
    inputs = [i for i in build_extraction_inputs(papers, contents) if i["pmid"] not in processed]
    focused = select_for_extraction(inputs, themes)
    items = prepare_batch_items(focused, CACHE_DIR)
    log.info(f"{len(papers)} papers, {len(focused)} on-theme and not yet extracted, "
             f"{len(items)} without a cached extraction")
    if args.limit:
        items = items[: args.limit]
    if not items:
        log.info("Nothing to submit")
        return 0
    if args.dry_run:
        chars = sum(len(i["prompt"]) for i in items)
        log.info(f"DRY RUN: would submit {len(items)} requests (~{chars // 4:,} input tokens "
                 f"by the 4-chars-per-token rule of thumb) to {args.model} at effort {args.effort}")
        return 0
    batch = submit_batch(items, model=args.model, effort=args.effort)
    write_manifest(_manifest_path(batch.id), batch.id, items, args.model, args.effort)
    log.info(f"Submitted {len(items)} requests as {batch.id} ({batch.processing_status}); "
             f"manifest {_manifest_path(batch.id)}")
    print(batch.id)
    return 0


def cmd_status(args) -> int:
    batch = make_client().messages.batches.retrieve(args.batch_id)
    print(f"{batch.id} {batch.processing_status} {batch.request_counts}")
    return 0


def cmd_collect(args) -> int:
    client = make_client()
    manifest = json.loads(_manifest_path(args.batch_id).read_text())
    while args.wait:
        batch = client.messages.batches.retrieve(args.batch_id)
        if batch.processing_status == "ended":
            break
        log.info(f"{batch.processing_status}: {batch.request_counts}")
        time.sleep(60)
    counts = collect_batch(args.batch_id, manifest["requests"], CACHE_DIR, client=client)
    log.info(f"Collected {args.batch_id}: {counts}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description=__doc__ or "Batch extraction via the Claude API")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="search, fetch and submit uncached papers as one batch")
    submit.add_argument("--theme", action="append", dest="themes")
    submit.add_argument("--themes-path", default="crawler/themes.yaml")
    submit.add_argument("--since", default="2021-01-01")
    submit.add_argument("--max-results", type=int, default=200)
    submit.add_argument("--limit", type=int, default=2000,
                        help="max requests in this batch (default 2000, as run.py's budget)")
    submit.add_argument("--model", default=DEFAULT_MODEL)
    submit.add_argument("--effort", default=DEFAULT_EFFORT,
                        choices=["low", "medium", "high", "xhigh", "max"])
    submit.add_argument("--dry-run", action="store_true", help="count requests, submit nothing")
    submit.set_defaults(func=cmd_submit)

    status = sub.add_parser("status")
    status.add_argument("--batch-id", required=True)
    status.set_defaults(func=cmd_status)

    collect = sub.add_parser("collect", help="write a batch's results into the extractor cache")
    collect.add_argument("--batch-id", required=True)
    collect.add_argument("--wait", action="store_true", help="poll until the batch has ended")
    collect.set_defaults(func=cmd_collect)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
