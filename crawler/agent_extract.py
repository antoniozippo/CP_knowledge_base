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
#
# A second pass asks only for combination experiments (two or more interventions
# given together, see extractor._COMBINATION_RULES) in papers chosen from the local
# cache, and writes crawler/extractions/combinations/<pmid>.json. Those files are
# not merged into the graph: they are test experiments for the functional model.
#
#   python3 crawler/agent_extract.py plan-combinations [--shard-size 40]
#   python3 crawler/agent_extract.py materialize --combinations --shard 0
#   python3 crawler/agent_extract.py check --combinations --shard 0
#   python3 crawler/agent_extract.py status --combinations

import argparse
import json
import logging
import re
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from crawler.extractor import (  # noqa: E402
    MAX_CONTENT_CHARS,
    ExtractionResult,
    LLMExtractor,
    _COMBINATION_SYSTEM_PROMPT,
    _SYSTEM_PROMPT,
    build_combination_prompt,
    parse_combination,
    verify_relationships,
)
from crawler.fetcher import fetch_papers  # noqa: E402
from crawler.run import (  # noqa: E402
    EXTRACTIONS_DIR,
    _section_rank,
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
COMBO_PLAN_PATH = WORK_DIR / "combinations_plan.json"
COMBINATIONS_DIR = EXTRACTIONS_DIR / "combinations"
# the combination pass reads more of each paper than the main pass (MAX_CONTENT_CHARS,
# 24k): results come first, and only a short list is written back
COMBO_CONTENT_CHARS = 40000
# Claude Code's Read tool cuts lines longer than 2000 characters; prompt files are
# wrapped at spaces below that (the quote check ignores whitespace)
LINE_WIDTH = 1000
# wording that suggests a combination experiment; most hits are background or methods
# mentions, which the worker then lists as nothing
COMBINATION_WORDING = re.compile(
    r"co-?administ\w*|in combination with|combined (?:treatment|administration|application|use)|co-?treat\w*|"
    r"synerg\w*|isobol\w*|"
    r"(?:knock-?out|-/-|deficient|knockdown|null)[^.]{0,80}(?:no effect|failed to|abolished|did not|was not|were not|no longer)|"
    r"(?:abolished|reversed|blocked|prevented|attenuated)(?: the)? (?:\w+ )?(?:effect|analgesi\w*|antinocicepti\w*) of",
    re.I)

INSTRUCTIONS = """# Extraction instructions for Claude Code worker sessions

For each `<pmid>.prompt.txt` in this shard directory, read the prompt and
write the answer as JSON to `crawler/extractions/<pmid>.json`. The prompt
contains the paper's content and the exact JSON structure to return.

Rules (the same system prompt the API extractor uses):

{system}

File format: one JSON object with the keys `entities`, `relationships`,
`combinations`, `key_findings`, `novel_terms` as in the prompt, plus `"pmid"`
and `"extracted_by": "claude-code-session"`. No markdown fences.

Quality bar:
- `evidence_quote` must be copied character for character from the Content
  section (case, punctuation and spacing are forgiven, wording is not).
  Relationships that fail this are discarded at merge time.
- Prefer fewer, well-supported relationships over many weak ones; an empty
  `relationships` list is a valid answer for an off-topic paper.
- `combinations` is empty for most papers. List an experiment only when the
  paper gave two or more interventions together (two drugs, a drug in knockout
  animals, a drug with an antagonist) and reports the readout; its
  `evidence_quote` follows the same verbatim rule.
- After writing a batch, run `python3 crawler/agent_extract.py check --shard N`
  and fix anything it reports.
"""


COMBO_INSTRUCTIONS = """# Combination-experiment instructions for Claude Code worker sessions

For each `<pmid>.prompt.txt` in this shard directory, read the prompt and
write the answer as JSON to `crawler/extractions/combinations/<pmid>.json`.
The prompt contains the paper's content and the exact JSON structure to return.

Rules (the same rules the full extraction uses for "combinations"):

{system}

File format: one JSON object `{{"pmid": "<pmid>", "extracted_by":
"claude-code-session", "pass": "combinations", "combinations": [...]}}`.
No markdown fences. Write the file even when the list is empty: an empty
file records that the paper was read.

Quality bar:
- These papers were chosen because their text contains wording such as
  "co-administered", "synergistic" or "abolished the effect of". Most of
  those mentions are background, methods or other people's work: list only
  experiments this paper ran AND reports a result for.
- `evidence_quote` must be copied character for character from the Content
  section (case, punctuation and spacing are forgiven, wording is not). It is
  the sentence reporting the combination result, not the methods sentence.
- One record per readout: if the paper reports the combination on mechanical
  and thermal pain, or on pain and a marker, write one record for each.
- After writing a batch, run
  `python3 crawler/agent_extract.py check --combinations --shard N`
  and fix anything it reports.
"""


def _shard_dir(shard: int, combinations: bool = False) -> Path:
    return WORK_DIR / (f"combo_shard_{shard:03d}" if combinations else f"shard_{shard:03d}")


def _wrap(content: str, width: int = LINE_WIDTH) -> str:
    """Break lines longer than width at spaces, keeping paragraphs."""
    return "\n".join(
        textwrap.fill(line, width, break_long_words=False, break_on_hyphens=False) if len(line) > width else line
        for line in content.split("\n"))


def _cached_text(paper: dict) -> str:
    """A cached paper's text in run.py's order (abstract, then results and discussion first)."""
    sections = (paper.get("fulltext_sections") or {}).items()
    parts = [paper.get("abstract_text") or ""]
    parts.extend(text for _, text in sorted(sections, key=lambda kv: _section_rank(kv[0])))
    return "\n\n".join(p for p in parts if p)


def combination_candidates(cache_dir: Path = CACHE_DIR) -> list[str]:
    """PMIDs of cached papers that are rodent nerve-injury studies (the functional
    model's context, analysis/perturbation/config.yaml) and contain combination wording."""
    sys.path.insert(0, str(_REPO_ROOT / "analysis" / "scripts"))
    import build_perturbation_cases as bp  # the context rules live with the validation set

    cfg = bp.Config()
    out = []
    for path in sorted(Path(cache_dir).glob("paper_*.json")):
        paper = json.loads(path.read_text())
        text = _cached_text(paper)
        if not text.strip() or not COMBINATION_WORDING.search(text):
            continue
        ctx = bp.paper_context(paper["pmid"], cfg, cache_dir)
        if ctx["models"] and ctx["species"] & cfg.rodent:
            out.append(paper["pmid"])
    return out


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


def cmd_plan_combinations(args) -> int:
    pmids = combination_candidates(Path(args.cache_dir))
    shards = [pmids[i:i + args.shard_size] for i in range(0, len(pmids), args.shard_size)]
    plan = {
        "created": datetime.now(timezone.utc).isoformat(),
        "pass": "combinations",
        "selection": "cached papers with a rodent species and a nerve-injury model in abstract or methods "
                     "(analysis/perturbation/config.yaml) whose text matches agent_extract.COMBINATION_WORDING",
        "content_chars": COMBO_CONTENT_CHARS,
        "shard_size": args.shard_size,
        "papers": len(pmids),
        "shards": shards,
    }
    COMBO_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMBO_PLAN_PATH.write_text(json.dumps(plan) + "\n")
    log.info(f"Planned {len(pmids)} papers in {len(shards)} shards of {args.shard_size} -> {COMBO_PLAN_PATH}")
    return 0


def _plan(combinations: bool) -> dict:
    return json.loads((COMBO_PLAN_PATH if combinations else PLAN_PATH).read_text())


def _done_path(pmid: str, combinations: bool) -> Path:
    return (COMBINATIONS_DIR if combinations else EXTRACTIONS_DIR) / f"{pmid}.json"


def _shard_pmids(plan: dict, shard: int, limit: int = 0) -> list[str]:
    pmids = plan["shards"][shard]
    return pmids[:limit] if limit else pmids


def _fetch_inputs(pmids: list[str]) -> tuple[list, list]:
    metas = []
    for start in range(0, len(pmids), BATCH_SIZE):
        metas.extend(_fetch_batch(pmids[start:start + BATCH_SIZE]))
        time.sleep(_rate_delay)
    return metas, fetch_papers(metas, cache_dir=CACHE_DIR)


def materialize_combinations(shard: int, limit: int = 0) -> int:
    """Write a combinations-only prompt + content file per paper of a combinations shard."""
    pmids = _shard_pmids(_plan(True), shard, limit)
    todo = [p for p in pmids if not _done_path(p, True).exists()]
    metas, contents = _fetch_inputs(todo) if todo else ([], [])
    out = _shard_dir(shard, True)
    out.mkdir(parents=True, exist_ok=True)
    (out / "INSTRUCTIONS.md").write_text(COMBO_INSTRUCTIONS.format(system=_COMBINATION_SYSTEM_PROMPT.strip()))
    written = 0
    for paper in build_extraction_inputs(metas, contents):
        content = paper["content"]
        if len(content) > COMBO_CONTENT_CHARS:
            content = content[:COMBO_CONTENT_CHARS] + "\n\n[... truncated ...]"
        content = _wrap(content)
        (out / f"{paper['pmid']}.content.txt").write_text(content)
        (out / f"{paper['pmid']}.prompt.txt").write_text(build_combination_prompt(content, paper["pmid"], paper["title"]))
        written += 1
    log.info(f"Combinations shard {shard}: {written} prompts in {out} ({len(pmids) - len(todo)} already done); "
             f"read {out / 'INSTRUCTIONS.md'}")
    return 0


def cmd_materialize(args) -> int:
    """Fetch one shard's papers and write a prompt + content file per paper."""
    if args.combinations:
        return materialize_combinations(args.shard, args.max)
    plan = json.loads(PLAN_PATH.read_text())
    pmids = _shard_pmids(plan, args.shard, args.max)
    metas, contents = _fetch_inputs(pmids)
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
    kept_combo = {c.evidence_quote for c in verified.combinations}
    dropped += [c.evidence_quote for c in result.combinations if c.evidence_quote not in kept_combo]
    malformed = len(raw.get("combinations") or []) - len(result.combinations)
    report = {"pmid": pmid, "status": "ok", "entities": len(result.entities),
              "relationships": len(result.relationships), "kept": len(verified.relationships),
              "combinations": len(result.combinations), "combinations_kept": len(verified.combinations),
              "dropped_quotes": dropped}
    if malformed:
        report["combinations_malformed"] = malformed        # fewer than two interventions, no readout or no quote
    return report


def check_combinations(pmid: str, content: str) -> dict:
    """Validate one combinations-pass file against its paper text."""
    path = COMBINATIONS_DIR / f"{pmid}.json"
    if not path.exists():
        return {"pmid": pmid, "status": "missing"}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"pmid": pmid, "status": "invalid_json", "error": str(exc)}
    items = raw.get("combinations") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return {"pmid": pmid, "status": "schema_error", "error": "no combinations list"}
    parsed = [c for c in (parse_combination(x) for x in items) if c]
    result = ExtractionResult(pmid=pmid, title="", entities=[], relationships=[], combinations=parsed,
                              key_findings=[], novel_terms=[])
    verified, _ = verify_relationships(result, content)
    kept = {c.evidence_quote for c in verified.combinations}
    report = {"pmid": pmid, "status": "ok", "combinations": len(parsed), "combinations_kept": len(verified.combinations),
              "dropped_quotes": [c.evidence_quote for c in parsed if c.evidence_quote not in kept]}
    if len(items) - len(parsed):
        report["combinations_malformed"] = len(items) - len(parsed)
    return report


def cmd_check(args) -> int:
    plan = _plan(args.combinations)
    out = _shard_dir(args.shard, args.combinations)
    check = check_combinations if args.combinations else check_extraction
    reports = []
    for pmid in _shard_pmids(plan, args.shard):
        content_file = out / f"{pmid}.content.txt"
        if not content_file.exists():
            continue  # not materialized (--max, or done in an earlier session)
        reports.append(check(pmid, content_file.read_text()))
    by_status = {}
    for r in reports:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    kept = sum(r.get("kept", 0) for r in reports)
    total = sum(r.get("relationships", 0) for r in reports)
    ckept = sum(r.get("combinations_kept", 0) for r in reports)
    ctotal = sum(r.get("combinations", 0) for r in reports)
    for r in reports:
        if r["status"] != "ok" or r.get("dropped_quotes") or r.get("combinations_malformed"):
            print(json.dumps(r))
    if args.combinations:
        print(f"combinations shard {args.shard}: {by_status}; combinations kept {ckept}/{ctotal}")
    else:
        print(f"shard {args.shard}: {by_status}; relationships kept {kept}/{total}; combinations kept {ckept}/{ctotal}")
    return 0 if by_status.get("ok", 0) == len(reports) else 1


def cmd_status(args) -> int:
    plan = _plan(args.combinations)
    for i, pmids in enumerate(plan["shards"]):
        done = sum(_done_path(p, args.combinations).exists() for p in pmids)
        print(f"shard {i:3d}: {done:4d}/{len(pmids)}")
    total = sum(len(s) for s in plan["shards"])
    done = sum(_done_path(p, args.combinations).exists() for s in plan["shards"] for p in s)
    print(f"total: {done}/{total}")
    if args.combinations:
        found = 0
        for s in plan["shards"]:
            for p in s:
                if _done_path(p, True).exists():
                    try:
                        found += len(json.loads(_done_path(p, True).read_text()).get("combinations") or [])
                    except (json.JSONDecodeError, AttributeError):
                        pass
        print(f"combination experiments listed: {found}")
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
    cplan = sub.add_parser("plan-combinations", help="choose cached nerve-injury papers with combination wording")
    cplan.add_argument("--shard-size", type=int, default=40)
    cplan.add_argument("--cache-dir", default=str(CACHE_DIR))
    cplan.set_defaults(func=cmd_plan_combinations)
    mat = sub.add_parser("materialize", help="fetch one shard and write its prompt files")
    mat.add_argument("--shard", type=int, required=True)
    mat.add_argument("--max", type=int, default=0, help="only the first N papers (pilots)")
    mat.add_argument("--themes-path", default="crawler/themes.yaml")
    mat.add_argument("--combinations", action="store_true", help="a shard of the combinations pass")
    mat.set_defaults(func=cmd_materialize)
    chk = sub.add_parser("check", help="validate a shard's extraction files")
    chk.add_argument("--shard", type=int, required=True)
    chk.add_argument("--combinations", action="store_true", help="a shard of the combinations pass")
    chk.set_defaults(func=cmd_check)
    st = sub.add_parser("status", help="extraction progress per shard")
    st.add_argument("--combinations", action="store_true", help="the combinations pass")
    st.set_defaults(func=cmd_status)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
