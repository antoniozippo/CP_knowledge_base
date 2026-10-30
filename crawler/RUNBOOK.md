# Crawler full-run runbook (Claude API, Message Batches)

A full run searches all ten themes, fetches abstracts and PMC full text,
extracts relationships with Claude through the Message Batches API, and
merges verified findings into `graphify-out/graph_v2.json`.

## Prerequisites

- `CRAWLER_ANTHROPIC_API_KEY` set as an environment secret (not
  `ANTHROPIC_API_KEY`; see `anthropic_backend.py` for why).
- Optional `NCBI_API_KEY` (10 req/s instead of 3) and `NCBI_EMAIL`.
- `pip install -r requirements.txt`

## Steps

1. **Smoke test, one paper, synchronous** (checks the key, the schema and the
   whole update path; a few cents):

   ```bash
   python3 crawler/run.py --theme T01 --since 2026-06-01 --max-results 5 --budget 1 --llm-provider anthropic --no-commit
   ```

   Expect `Extracted from 1 papers (1 LLM calls)` and a run log under
   `crawler/logs/`. Then discard its graph change and its processed mark, so
   the full run below merges that paper normally (its cached extraction is
   reused for free):

   ```bash
   git checkout graphify-out/graph_v2.json crawler/conflicts.yaml 2>/dev/null; rm -f crawler/processed_pmids.json
   ```

2. **Estimate**: `python3 crawler/batch_extract.py submit --dry-run`
   prints the request count and an input-token estimate. Search and fetch run
   here the first time (about an hour at NCBI's keyless rate); later runs are
   cached.

3. **Submit**: `python3 crawler/batch_extract.py submit` prints a
   `msgbatch_...` id and writes `crawler/logs/batches/<id>.json`. `--limit`
   caps the batch (default 2000, matching run.py's budget).

4. **Collect**: `python3 crawler/batch_extract.py collect --batch-id <id> --wait`
   polls until the batch ends (most finish within an hour, at most 24 h) and
   writes results into `crawler/cache/`. Errored/expired requests are not
   cached, so re-running `submit` retries exactly those.

5. **Merge**: `python3 crawler/run.py --since 2021-01-01 --cache-only --no-commit`
   (`--cache-only` makes no LLM calls: collected papers are cache hits, the
   rest are deferred; note `--budget 0` means *unlimited*). Read the
   summary line: papers extracted, relationships dropped for unverifiable
   quotes, nodes/edges added, evidence appended, conflicts.

6. **Review and commit**: inspect `crawler/conflicts.yaml` and the new
   `auto_crawled` links, run
   `python3 -m pytest crawler/tests analysis/tests simulator/tests -q`, then
   commit `graphify-out/graph_v2.json`, `crawler/conflicts.yaml`,
   `crawler/discovered_mesh.yaml` and the run log.

New links are `UNREVIEWED` and stay out of the simulator's agent cards
(`simulator/build_cards.py: simulation_eligible`) until a reviewer sets a
`validation_status`; evidence on existing links is in `crawler_evidence`.

## Alternative: extraction by Claude Code sessions (Claude subscription, no API key)

`crawler/agent_extract.py` replaces steps 3-4: Claude Code cloud sessions do
the extraction themselves, on the subscription, and commit one JSON file per
paper to `crawler/extractions/`. The merge (step 5) is unchanged:
`run.py --cache-only` reads those files, re-verifies every quote against the
paper text and updates the graph.

1. `python3 crawler/agent_extract.py plan` (once; writes
   `crawler/agent_work/plan.json`, 100 papers per shard, committed).
2. Per worker session, shard N:
   `python3 crawler/agent_extract.py materialize --shard N`, then follow
   `crawler/agent_work/shard_NNN/INSTRUCTIONS.md`, then
   `python3 crawler/agent_extract.py check --shard N` until clean, then commit
   `crawler/extractions/*.json` and push (`git pull --rebase` first: shards
   touch disjoint files).
3. `python3 crawler/agent_extract.py status` shows progress per shard.
4. Merge as in step 5 above.
