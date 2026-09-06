# Chronic Pain Knowledge Base & LLM-Agent Simulator

A graph-based chronic pain knowledge base with an LLM-agent simulation engine that models neuroinflammatory dynamics, treatment effects, and acute-to-chronic pain transition across 554 biological entities and 914 regulatory links.

## Project overview

This repository implements two integrated aims:

**Aim 1 — Literature-validated knowledge base:** 262 claim cards extracted from ~100 literature sweeps across 10 themes, validated against PubMed/arXiv/bioRxiv evidence (86 CONFIRMED / 37 EXTENDED / 8 REFUTED / 6 MIXED), parameterized into a signed directed graph with 554 nodes and 914 edges.

**Aim 2 — LLM-agent simulator:** 372 agents (9 hub / 123 mid / 240 peripheral), one per graph node, simulate neuropathic pain dynamics over 0–180 days. Hub agents call a local LLM (Qwen3.8-27b via LM Studio) at epoch boundaries; mid-tier agents use batched LLM calls; peripheral agents use deterministic compiled rules. Runs are byte-reproducible (seed 42, temperature 0).

## Key results

| Scenario | LLM Pain | Rules Pain | Δ |
|---|---|---|---|
| naive_28d | 0.071 | 0.050 | +0.021 |
| SNI_28d | 0.481 | 0.476 | +0.005 |
| CCI_28d | 0.481 | 0.350 | +0.131 |
| CIPN_28d | 0.451 | 0.333 | +0.118 |
| SNI_28d + CLP257 | 0.464 | 0.335 | +0.130 |
| SNI_28d + XPro1595 | 0.452 | 0.318 | +0.134 |
| SNI_28d + Fasudil | 0.474 | 0.469 | +0.005 |
| SNI_28d DRIVE_DECAY | 0.441 | 0.322 | +0.118 |
| naive_180d | 0.254 | 0.050 | +0.204 |
| SNI_180d | 0.489 | 0.352 | +0.137 |

**Fasudil paradox resolved:** after edge correction (quarantined 2 `RhoA/ROCK → Kalirin-7` NO_EVIDENCE edges, added corrected `RhoA_ROCK_ROCK → DendriticSpineLoss (+1)`), fasudil is protective in both rules-only (Δ = −0.007) and LLM modes (Δ = −0.006). This was a key finding — ROCK inhibition acts via dendritic spine preservation, not via direct Kalirin-7 modulation.

**LLM amplification bias:** LLM hub agents systematically amplify pain by +0.12–0.13 for all injury models, likely due to pronociceptive reasoning saturation at hub nodes (microglia, TNF, ROCK, Kalirin-7/Rac1).

**Drug efficacy loss under LLM:** CLP257 and XPro1595 show clear benefit in rules-only mode but lose efficacy under LLM — hub agents re-activate inflammatory cascades that drug rules suppress.

**Chronic drift:** naive_180d rises from 0.05 to 0.25 under LLM, indicating accumulated spurious activation at hub nodes over long horizons.

## Repository structure

```
CP_knowledge_base/
├── graphify-out/
│   └── graph_v2.json          # Authoritative graph (554 nodes / 914 edges)
├── analysis/
│   ├── claims/                 # 262 claim cards + closure_edges.yaml
│   ├── scripts/                # build_graph_v2.py, add_closure_edges.py
│   └── literature/             # 10 thematic dossier sweeps
├── simulator/
│   ├── schemas.py              # Pydantic: AgentCard, WorldState, StateDelta
│   ├── build_cards.py          # Graph → 372 agent YAML cards
│   ├── cards/                  # 372 agent cards (9 hub / 123 mid / 240 peripheral)
│   ├── engine/
│   │   ├── orchestrator.py     # Tick loop, influence packets, delta application
│   │   ├── llm_agent.py        # LocalLLMClient (OpenAI-compatible, LM Studio)
│   │   └── rule_fallback.py    # Deterministic rules for peripheral agents
│   ├── scenarios/              # YAML: naive, SNI, CCI, CIPN, drug arms
│   ├── validation/             # facts.yaml (19 published empirical assertions)
│   ├── tests/                  # pytest suite (270 tests)
│   ├── out/                    # Run outputs (tick_logs, states, manifests)
│   └── reports/                # Results summaries, plots, M&M
└── plans/
    └── 2026-08-25-pain-lit-sim.md  # Implementation plan (all tasks complete)
```

## Agent tiers

| Tier | Count | Execution | LLM calls |
|---|---|---|---|
| Hub | 9 | LLM at epoch boundaries + significant state changes | ~3 per epoch |
| Mid | 123 | Batched community LLM calls | ~1 per epoch boundary |
| Peripheral | 240 | Compiled deterministic rules | 0 |

**Total LLM calls per 28-day run:** 27 (3 hub calls × 9 epochs)

## Graph god nodes

| Entity | Edges | Role |
|---|---|---|
| Kalirin-7 | 45 | GEF for Rac1/RhoG, dendritic spine dynamics |
| KCC2 | 50 (combined) | Chloride cotransporter, disinhibition gate |
| BDNF | 22 | Dual pro/anti-nociceptive neurotrophin |
| HIF1α | 16 | Metabolic switch, pain gene battery |
| NLRP3 | 15 | Inflammasome master hub |
| RAGE | 15 | DAMP receptor, NF-κB amplifier |
| TRPV1 | 15 | Vanilloid nociceptor channel |
| ZFHX2 | 14 | Pain transcription factor |

## Running simulations

### Rules-only (deterministic, fast)

```bash
python3 simulator/engine/orchestrator.py \
  --scenario simulator/scenarios/SNI_28d.yaml \
  --output-dir simulator/out/SNI_28d_rules \
  --ticks 28 --seed 42
```

### LLM-enhanced (requires local LM Studio endpoint)

```bash
python3 simulator/engine/orchestrator.py \
  --scenario simulator/scenarios/SNI_28d.yaml \
  --output-dir simulator/out/SNI_28d_LLM \
  --ticks 28 --seed 42 \
  --llm-endpoint http://192.168.1.13:1234 \
  --llm-model qwen/qwen3.8-27b \
  --llm-max-tokens 4096
```

### Full 10-arm battery

```bash
python3 run_remaining_battery.py
```

Runs all scenarios sequentially (~5.7h for LLM mode).

## Automated literature crawler

The crawler pulls new PubMed/PMC papers, extracts entities and relationships via LLM, and merges them into the graph — keeping the KB current without manual sweeps.

### Quick start

```bash
# Dry-run (no API calls, no graph writes)
python3 crawler/run.py --dry-run

# Crawl one theme since 2025-01-01
python3 crawler/run.py --theme kcc2_gating --since 2025-01-01

# Full crawl with LLM budget cap
python3 crawler/run.py --since 2026-01-01 --budget 2000

# List available themes
python3 crawler/run.py --list-themes
```

### Pipeline stages

1. **Search** — PubMed queries from `themes.yaml` (87 queries across 10 themes)
2. **Fetch** — abstracts + PMC full-text (JATS XML), cached
3. **Extract** — LLM extracts entities, relationships, key findings
4. **Match** — fuzzy match against existing graph (rapidfuzz ≥85%)
5. **Update** — add new nodes/edges, update verdicts, detect conflicts
6. **Discover** — adjacent MeSH terms for theme expansion
7. **Commit** — auto-commit if tests pass

### Safety guardrails

- Dedup via `processed_pmids.json` (never re-process)
- LLM budget cap (default 2000 calls/run)
- Never auto-refute CONFIRMED edges (flag for human review)
- Conflict detection: sign contradictions → `HUMAN_REVIEW`
- Full provenance on every new node/edge
- Test gate before commit

### Cron setup (weekly)

```bash
# Every Sunday at 02:00
0 2 * * 0 cd /path/to/CP_knowledge_base && python3 crawler/run.py --since 7d --budget 2000 >> crawler/logs/cron.log 2>&1
```

### Architecture

```
crawler/
├── themes.yaml          # 10 themes, keywords, MeSH, entities
├── aliases.yaml         # 61 gene symbol mappings
├── search.py            # PubMed via Biopython Entrez
├── fetcher.py           # abstract + PMC full-text
├── extractor.py         # LLM entity/relationship extraction
├── matcher.py           # fuzzy match (rapidfuzz)
├── updater.py           # graph update + conflict detection
├── discovery.py         # adjacent MeSH term discovery
├── conflict.py          # contradiction resolution
├── run.py               # CLI orchestrator
└── tests/               # 26 tests, all passing
```

## Validation

The simulator passes a 19-fact regression harness asserting published dynamics:

- SNI baseline pain ≥ 0.35 (expect ~0.48)
- CLP257 reduces pain by ≥ 0.015 vs SNI
- XPro1595 reduces pain by ≥ 0.015 vs SNI
- Fasudil reduces pain vs SNI (after edge correction)
- naive baseline remains < 0.10 at 28 days
- All arm failure modes (LLM, rules) covered

```bash
cd simulator && python3 -m pytest tests/ -v  # 270 tests
```

## Tech stack

- **Graph:** NetworkX, Pydantic, YAML
- **LLM:** OpenAI-compatible API (LM Studio, Qwen3.8-27b)
- **Simulation:** Custom orchestrator, deviation-propagation dynamics
- **Testing:** pytest
- **Visualization:** Matplotlib

## Data sources

- Literature: PubMed, arXiv, bioRxiv, Semantic Scholar (2021–2026 + landmark classics)
- Reference databases: UniProt, KEGG, ChEMBL, Reactome
- Dossier extraction: ~105 scientific documents, 205,000 words

## How to cite

```
@software{chronic_pain_kb_2026,
  title = {Chronic Pain Knowledge Base & LLM-Agent Simulator},
  year = {2026},
  url = {https://github.com/antoniozippo/CP_knowledge_base},
  note = {554 nodes, 914 edges, 372 agents, 10-arm LLM battery}
}
```

## License

This is a research knowledge base. The graph structure, claim cards, and simulation outputs are derived from published literature and are provided for research purposes. Individual claims are attributed to their source publications in the dossier files.
