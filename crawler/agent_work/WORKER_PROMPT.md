# Worker brief: extraction of one shard by a Claude Code session

Paste into a new cloud session on branch `claude/happy-dijkstra-wounz6`,
replacing `{SHARD}` (0-37) and `{MODEL}` (`opus` or `sonnet`).

---

You are a worker for this repository's literature crawler. Do the LLM
extraction step yourself for shard {SHARD} (about 100 papers); no API key is
involved. Background: "Alternative: extraction by Claude Code sessions" in
`crawler/RUNBOOK.md`.

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
   - Read each prompt file once, then write `crawler/extractions/<pmid>.json`.
   - Every `evidence_quote` is copied verbatim from that paper's Content.
   - Write compact JSON (no indentation). Omit `aliases` when empty; at most
     2 `key_findings`; `novel_terms` may be `[]`.
   - Prefer fewer, well-supported relationships; `HIGH` confidence only for
     the paper's own direct results, not "suggests"/"may"; keep region or
     cell-type qualifiers in entity names when the finding is specific to
     them (e.g. "VP GABAergic neurons", not "neurons").
   - Do not commit; report pmids written and relationship counts.
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
7. Report: papers, entities, relationships, quotes dropped before fixes,
   wall-clock time, and anything a reviewer should know.
