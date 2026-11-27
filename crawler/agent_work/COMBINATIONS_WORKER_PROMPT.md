# Worker brief: the combinations pass on one or more shards

Paste into a new cloud session on branch `claude/happy-dijkstra-wounz6`,
replacing `{SHARDS}` (shard numbers 0-5 of
`crawler/agent_work/combinations_plan.json`, e.g. `0 and 1`) and `{MODEL}`
(`sonnet` or `opus`). Each shard is 40 rodent nerve-injury papers whose text
contains combination wording; prompts carry up to 40,000 characters of each
paper (about twice the main pass), hence batches of 5.

---

You are a worker for this repository's literature crawler. For shard(s)
{SHARDS} of the combinations pass, one shard at a time (finish steps 2-6 for a
shard, including its push, before starting the next), list the combination
experiments each paper ran: two or more interventions given together with one
readout measured (two drugs; a drug in knockout or knockdown animals; a drug
with an antagonist that tests its mechanism). No API key is involved.
Background: the combinations paragraph and "Alternative: extraction by Claude
Code sessions" in `crawler/RUNBOOK.md`. Below, {SHARD} means the shard being
processed.

1. `pip install -q -r requirements.txt`
2. `python3 crawler/agent_extract.py materialize --combinations --shard {SHARD}`
   and read `crawler/agent_work/combo_shard_NNN/INSTRUCTIONS.md` (NNN =
   {SHARD} zero-padded). Papers that already have
   `crawler/extractions/combinations/<pmid>.json` are skipped.
3. The reading is done by subagents, which you are explicitly asked to use:
   split the prompt files into batches of 5 and give each batch to one
   subagent (Agent tool, `model: "{MODEL}"`), at most 4 running at a time. You
   only orchestrate: do not read the papers yourself. Give every subagent the
   INSTRUCTIONS.md path, its exact list of prompt files (check the list is
   filled in before launching), and these rules:
   - Read each prompt file ONCE AND COMPLETELY: a single Read call with no
     offset/limit, then write `crawler/extractions/combinations/<pmid>.json`.
     Never grep or search a paper for passages and never stop at the
     abstract; combination results are usually in the Results section and
     figure descriptions.
   - Write a file for every paper, `"combinations": []` when the paper ran no
     combination experiment. Most papers have none: the wording that selected
     them is often background, methods or other groups' work.
   - Every `evidence_quote` is copied verbatim from that paper's Content and
     is the sentence reporting the combination's result.
   - One record per readout. `HIGH` confidence only for the paper's own
     direct results with the single interventions compared.
   - Write compact JSON (no indentation). Do not commit; report the pmids
     written and how many combinations each has.
   Save progress often: whenever four batches (20 papers) have finished, run
   the check below, fix problems in the files written so far, and do step 6
   (commit + push) for those files. A usage limit can stop the session at
   any moment; only pushed files survive it. When resuming after a stop,
   re-run materialize: papers already pushed are skipped.
4. `python3 crawler/agent_extract.py check --combinations --shard {SHARD}`:
   fix every `invalid_json`, `schema_error`, malformed record and dropped
   quote (correct the quote to the paper's exact wording or delete the
   record) until it is clean for every materialized paper.
5. `python3 -m pytest crawler/tests -q` must pass.
6. Commit ONLY `crawler/extractions/combinations/*.json` as
   `data(crawler): combination experiments, combinations shard {SHARD} ({MODEL} workers)`,
   then `git pull --rebase origin claude/happy-dijkstra-wounz6` and push to
   `claude/happy-dijkstra-wounz6` (other shards push there too; files are
   disjoint, so just rebase and retry). Do not run run.py, do not edit
   `crawler/extractions/<pmid>.json` or anything under graphify-out/.
7. Report per shard: papers read, papers with at least one combination,
   records by interaction class, quotes dropped before fixes, wall-clock
   time, and anything a reviewer should know (for example papers whose
   content was cut before their results).
