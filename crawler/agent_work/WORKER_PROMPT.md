# Worker brief: extraction of one shard by a Claude Code session

Paste into a new cloud session on branch `claude/happy-dijkstra-wounz6`,
replacing `{SHARDS}` (one or more shard numbers 0-37, e.g. `5 and 6`) and
`{MODEL}` (`opus` or `sonnet`). The wave of 2026-10-30 measured, per paper
(API-equivalent): opus $0.14 / ~6 relationships, sonnet $0.05 / ~2.5 but
with skimming of long papers, hence the full-read rule below (with it:
~3.8 relationships/paper). Four parallel sessions exhausted the 5-hour
usage window in ~7 minutes, hence the commit-every-20-papers rule.

---

You are a worker for this repository's literature crawler. Do the LLM
extraction step yourself for shard(s) {SHARDS} (about 100 papers each),
one shard at a time: finish steps 2-6 for a shard (including its push)
before starting the next. No API key is involved. Background: "Alternative:
extraction by Claude Code sessions" in `crawler/RUNBOOK.md`. Below, {SHARD}
means the shard currently being processed.

1. `pip install -q -r requirements.txt`
2. `python3 crawler/agent_extract.py materialize --shard {SHARD}` and read
   `crawler/agent_work/shard_NNN/INSTRUCTIONS.md` (NNN = {SHARD} zero-padded).
   Skip any paper that already has `crawler/extractions/<pmid>.json`.
3. Extraction is done by subagents, which you are explicitly asked to use:
   split the remaining prompt files into batches of 10 and give each batch
   to one subagent (Agent tool, `model: "{MODEL}"`), at most 5 running at a
   time. You only orchestrate: do not read the papers yourself. Give every
   subagent the INSTRUCTIONS.md path, its exact list of prompt files (check
   the list is filled in before launching), and these rules:
   - Read each prompt file ONCE AND COMPLETELY: a single Read call with no
     offset/limit, then write `crawler/extractions/<pmid>.json`. Never grep
     or search a paper for passages and never stop at the abstract or the
     first sections; results and discussion are where most findings are.
   - Every `evidence_quote` is copied verbatim from that paper's Content.
   - Write compact JSON (no indentation). Omit `aliases` when empty; at most
     2 `key_findings`; `novel_terms` may be `[]`.
   - Prefer fewer, well-supported relationships; `HIGH` confidence only for
     the paper's own direct results, not "suggests"/"may"; keep region or
     cell-type qualifiers in entity names when the finding is specific to
     them (e.g. "VP GABAergic neurons", not "neurons").
   - Do not commit; report pmids written and relationship counts.
   Save progress often: whenever two batches (20 papers) have finished,
   run the check below, fix problems in the files written so far, and do
   step 6 (commit + push) for those files. A usage limit can stop the
   session at any moment; only pushed files survive it. When resuming
   after a stop, re-run materialize: papers already pushed are skipped.
4. `python3 crawler/agent_extract.py check --shard {SHARD}`: fix every
   `invalid_json`, `schema_error` and dropped quote (correct the quote to the
   exact wording or delete the relationship) until it is clean for every
   materialized paper.
5. `python3 -m pytest crawler/tests -q` must pass.
6. Commit ONLY `crawler/extractions/*.json` as
   `data(crawler): session extractions, shard {SHARD} ({MODEL} workers)`,
   then `git pull --rebase origin claude/happy-dijkstra-wounz6` and push to
   `claude/happy-dijkstra-wounz6` (other shards push there too; files are
   disjoint, so just rebase and retry). Do not run run.py or touch
   graphify-out/.
7. Report per shard: papers, entities, relationships, quotes dropped before
   fixes, wall-clock time, and anything a reviewer should know.
