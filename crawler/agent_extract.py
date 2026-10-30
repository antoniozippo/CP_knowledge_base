#!/usr/bin/env python3
# crawler/agent_extract.py - extraction by Claude Code sessions (Claude subscription, no API key)
#
# The extraction step is done by Claude Code worker sessions instead of an
# API call: each worker takes one shard of papers, writes one extraction JSON
# per paper to crawler/extractions/<pmid>.json, checks it, and pushes. The
# merge is the normal pipeline: run.py --cache-only reads those files as
# cache hits (LLMExtractor.extractions_dir), re-verifies every quote against
# the paper text and updates the graph.
#
#   python3 crawler/agent_extract.py plan [--since 2021-01-01] [--shard-size 100]
#   python3 crawler/agent_extract.py materialize --shard 0 [--max 10]
#   python3 crawler/agent_extract.py check --shard 0
#   python3 crawler/agent_extract.py status
#   python3 crawler/run.py --since 2021-01-01 --cache-only --no-commit

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from crawler.extractor import (  # noqa: E402
    MAX_CONTENT_CHARS,
    LLMExtractor,
    _SYSTEM_PROMPT,
    verify_relationships,
)
from crawler.fetcher import fetch_papers  # noqa: E402
from crawler.run import (  # noqa: E402
    EXTRACTIONS_DIR,
    build_extraction_inputs,
    load_themes,
    search_all,
    select_for_extraction,
)
from crawler.search import BATCH_SIZE, _fetch_batch, _load_processed_pmids, _rate_delay  # noqa: E402

log = logging.getLogger(__name__)
CACHE_DIR = Path("crawler/cache")
WORK_DIR = Path("crawler/agent_work")
PLAN_PATH = WORK_DIR / "plan.json"

INSTRUCTIONS = """# Extraction instructions for Claude Code worker sessions

For each `<pmid>.prompt.txt` in this shard directory, read the prompt and
write the answer as JSON to `crawler/extractions/<pmid>.json`. The prompt
contains the paper's content and the exact JSON structure to return.

Rules (the same system prompt the API extractor uses):

{system}

File format: one JSON object with the keys `entities`, `relationships`,
`key_findings`, `novel_terms` as in the prompt, plus `"pmid"` and
`"extracted_by": "claude-code-session"`. No markdown fences.

Quality bar:
- `evidence_quote` must be copied character for character from the Content
  section (case, punctuation and spacing are forgiven, wording is not).
  Relationships that fail this are discarded at merge time.
- Prefer fewer, well-supported relationships over many weak ones; an empty
  `relationships` list is a valid answer for an off-topic paper.
- After writing a batch, run `python3 crawler/agent_extract.py check --shard N`
  and fix anything it reports.
"""


def _shard_dir(shard: int) -> Path:
    return WORK_DIR / f"shard_{shard:03d}"


def _truncate(content: str) -> str:
    """The text a paper's extraction is checked against (as LLMExtractor.extract)."""
    if len(content) > MAX_CONTENT_CHARS:
        return content[:MAX_CONTENT_CHARS] + "\n\n[... truncated for LLM context ...]"
    return content


def cmd_plan(args) -> int:
    themes = load_themes(args.themes_path)
    papers = search_all(themes, args.since, args.max_results)
    contents = fetch_papers(papers, cache_dir=CACHE_DIR)
    processed = _load_processed_pmids()
    inputs = [i for i in build_extraction_inputs(papers, contents) if i["pmid"] not in processed]
    focused = select_for_extraction(inputs, themes)
    pmids = [p["pmid"] for p, _ in focused]
    shards = [pmids[i:i + args.shard_size] for i in range(0, len(pmids), args.shard_size)]
    plan = {
        "created": datetime.now(timezone.utc).isoformat(),
        "since": args.since,
        "max_results": args.max_results,
        "shard_size": args.shard_size,
        "papers": len(pmids),
        "shards": shards,
    }
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(plan) + "\n")
    log.info(f"Planned {len(pmids)} papers in {len(shards)} shards of {args.shard_size} -> {PLAN_PATH}")
    return 0


def _shard_pmids(plan: dict, shard: int, limit: int = 0) -> list[str]:
    pmids = plan["shards"][shard]
    return pmids[:limit] if limit else pmids


def cmd_materialize(args) -> int:
    """Fetch one shard's papers and write a prompt + content file per paper."""
    plan = json.loads(PLAN_PATH.read_text())
    pmids = _shard_pmids(plan, args.shard, args.max)
    metas = []
    for start in range(0, len(pmids), BATCH_SIZE):
        metas.extend(_fetch_batch(pmids[start:start + BATCH_SIZE]))
        time.sleep(_rate_delay)
    contents = fetch_papers(metas, cache_dir=CACHE_DIR)
    builder = LLMExtractor(cache_dir=CACHE_DIR)
    out = _shard_dir(args.shard)
    out.mkdir(parents=True, exist_ok=True)
    (out / "INSTRUCTIONS.md").write_text(INSTRUCTIONS.format(system=_SYSTEM_PROMPT.strip()))
    written = 0
    # focus entities recomputed from the text, exactly as run.py selects them
    themes = load_themes(args.themes_path)
    for paper, focus in select_for_extraction(build_extraction_inputs(metas, contents), themes):
        content = _truncate(paper["content"])
        (out / f"{paper['pmid']}.content.txt").write_text(content)
        (out / f"{paper['pmid']}.prompt.txt").write_text(
            builder._build_prompt(content, paper["pmid"], paper["title"], focus)
        )
        written += 1
    done = sum((EXTRACTIONS_DIR / f"{p}.json").exists() for p in pmids)
    log.info(f"Shard {args.shard}: {written} prompts in {out} ({done} already extracted); "
             f"read {out / 'INSTRUCTIONS.md'}")
    return 0


def check_extraction(pmid: str, content: str) -> dict:
    """Validate one committed extraction against its paper text."""
    path = EXTRACTIONS_DIR / f"{pmid}.json"
    if not path.exists():
        return {"pmid": pmid, "status": "missing"}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"pmid": pmid, "status": "invalid_json", "error": str(exc)}
    raw.setdefault("pmid", pmid)
    raw.setdefault("title", "")
    result = LLMExtractor(cache_dir=CACHE_DIR)._validate_result(raw)
    if result is None:
        return {"pmid": pmid, "status": "schema_error"}
    verified, _ = verify_relationships(result, content)
    kept_quotes = {r.evidence_quote for r in verified.relationships}
    dropped = [r.evidence_quote for r in result.relationships if r.evidence_quote not in kept_quotes]
    return {"pmid": pmid, "status": "ok", "entities": len(result.entities),
            "relationships": len(result.relationships), "kept": len(verified.relationships),
            "dropped_quotes": dropped}


def cmd_check(args) -> int:
    plan = json.loads(PLAN_PATH.read_text())
    out = _shard_dir(args.shard)
    reports = []
    for pmid in _shard_pmids(plan, args.shard):
        content_file = out / f"{pmid}.content.txt"
        if not content_file.exists():
            continue  # not materialized (e.g. --max)
        reports.append(check_extraction(pmid, content_file.read_text()))
    by_status = {}
    for r in reports:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    kept = sum(r.get("kept", 0) for r in reports)
    total = sum(r.get("relationships", 0) for r in reports)
    for r in reports:
        if r["status"] != "ok" or r.get("dropped_quotes"):
            print(json.dumps(r))
    print(f"shard {args.shard}: {by_status}; relationships kept {kept}/{total}")
    return 0 if by_status.get("ok", 0) == len(reports) else 1


def cmd_status(args) -> int:
    plan = json.loads(PLAN_PATH.read_text())
    for i, pmids in enumerate(plan["shards"]):
        done = sum((EXTRACTIONS_DIR / f"{p}.json").exists() for p in pmids)
        print(f"shard {i:3d}: {done:4d}/{len(pmids)}")
    total = sum(len(s) for s in plan["shards"])
    done = sum((EXTRACTIONS_DIR / f"{p}.json").exists() for s in plan["shards"] for p in s)
    print(f"total: {done}/{total}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Extraction by Claude Code worker sessions")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="search + fetch, split on-theme papers into shards")
    plan.add_argument("--themes-path", default="crawler/themes.yaml")
    plan.add_argument("--since", default="2021-01-01")
    plan.add_argument("--max-results", type=int, default=200)
    plan.add_argument("--shard-size", type=int, default=100)
    plan.set_defaults(func=cmd_plan)
    mat = sub.add_parser("materialize", help="fetch one shard and write its prompt files")
    mat.add_argument("--shard", type=int, required=True)
    mat.add_argument("--max", type=int, default=0, help="only the first N papers (pilots)")
    mat.add_argument("--themes-path", default="crawler/themes.yaml")
    mat.set_defaults(func=cmd_materialize)
    chk = sub.add_parser("check", help="validate a shard's extraction files")
    chk.add_argument("--shard", type=int, required=True)
    chk.set_defaults(func=cmd_check)
    st = sub.add_parser("status", help="extraction progress per shard")
    st.set_defaults(func=cmd_status)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
