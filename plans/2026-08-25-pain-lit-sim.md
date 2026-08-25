# Pain Knowledge Expansion + LLM-Agent Physiology Simulator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand and harden the chronic-pain knowledge base via literature-driven validation (Aim 1), then build an LLM-agent simulation engine with one agent per graph node that reproduces known physiological and pathological dynamics (Aim 2).

**Architecture:** Aim 1 produces validated, parameterized knowledge (claim cards with evidence verdicts); Aim 2 consumes it. Each of the 595 graph nodes gets an agent whose persona card is generated from its dossier note + validated edges. A deterministic orchestrator runs discrete ticks (1 tick = 1 day, horizon ≤180 days); LLM agents reason about state transitions under strict JSON-schema constraints with tiered execution for cost control.

**Tech stack:** Python 3.11+, NetworkX, Pydantic, YAML scenarios, pytest, opencode CLI (`opencode run`) as the LLM backend for agents, websearch/Zotero tooling for literature.

## Locked design decisions (user-approved)

| Decision | Choice |
|---|---|
| Simulator formalism | LLM-agent simulation (one agent per node) |
| Scope | All 595 nodes from Phase 2 scale-out |
| Literature scope | Last 5 years + landmark classics |
| Artifact location | New subfolders in this repo: `analysis/`, `simulator/` |
| Agent LLM backend | opencode's model via `opencode run` subprocess |
| Time model | 1 tick = 1 day; horizon up to 180 days; epochs: Initiation (0–3d), Subacute (4–14d), Transition (15–28d), Established chronic (29–180d) |
| Vault write-back | Simulation outputs stay in `simulator/reports/`; only Aim 1 writes vault notes |

## Guardrails (mandatory)

1. **Grounding:** agent cards contain only KB dossier text + validated claim cards; every StateDelta must cite claim IDs or rule IDs.
2. **Determinism:** authoritative numeric world-state ledger outside LLMs; agents emit schema-validated JSON deltas; temperature 0; full prompt/response audit log per run.
3. **Cost:** tiered agents (~30 hub = LLM at epoch boundaries/significant changes; ~265 mid = community-batched LLM calls; ~300 peripheral = compiled rules); response cache keyed on (card hash, influence packet hash); budget cap per run.
4. **Validation:** regression harness asserting published dynamics; naive baseline must remain stable across 180 days (no saturation/oscillation artifacts).

---

## Phase 0 — Foundation

### Task 0.1: Repo hygiene
- [x] Commit pending vault files (`DRGX.md`, `ZFHX2.md`, `karilin-7.md`)
- [x] `.gitignore` additions: `graph_backup*.json`, `graph_processed.json`, `graph_merged.json`, `cache/`, `cost.json`, `.claude/logs/`

### Task 0.2: Graph schema v2 + entity deduplication
**Files:** Create `analysis/scripts/build_graph_v2.py` → `graphify-out/graph_v2.json`
- [ ] Merge duplicate entities (KCC2 ×2; scan all norm_labels for near-collisions)
- [ ] Add per-node fields: `entity_type` ∈ {molecule, receptor, channel, cell_type, pathway, process, structure, drug, symptom, concept}; `compartment` ∈ {DRG, dorsal_horn, ACC, barrier, peripheral, systemic, other}; `tier` ∈ {hub, mid, peripheral}
- [ ] Normalize edges onto signed semantics: `sign` ∈ {+1, −1, 0} derived from relation; keep original `relation` string; carry `confidence`
- [ ] Tests: no duplicate norm_labels; every causal edge has non-zero sign; counts preserved (595→N_merged nodes documented)

---

## Phase 1 — Aim 1: Literature search & knowledge validation

### Task 1.1: Claim-card inventory
**Files:** Create `analysis/scripts/extract_claims.py` → `analysis/claims/*.json`
- [ ] Extract every signed/causal edge + quantitative statements from dossiers into claim cards: `{id, subject, predicate, object, direction, source_note, quote, citation_status: UNVERIFIED}`
- [ ] Priority flags: causal edges first; the 17 INFERRED Kalirin-7 edges; AMBIGUOUS NrCAM↔NgR1 edge

### Task 1.2: Thematic literature sweeps (10 themes)
Per theme produce `analysis/literature/theme_{n}_{name}.md`: WebSearch PubMed/arXiv/bioRxiv 2021–2026 + landmark classics; screen; extract findings as new candidate claims; Zotero collection `Research-ChronicPain-{theme}-2026`.
Themes:
1. spinal disinhibition / KCC2 / PV-SST circuits
2. MMP-9 / PNN / ECM
3. neuroinflammation TNF/NLRP3/TLR/microglia
4. HIF1α / metabolism / vascular-BBB-BSCB
5. NgR1 / RhoA / myelin inhibitors
6. DRG excitability Nav/TRPV1/Rbfox1/DRGX/ZFHX2
7. CGRP / bradykinin / prostaglandins
8. resolution SPM/HO-1/PPARγ/CB2
9. epigenetics HDAC/lactylation/JAK-STAT
10. Kalirin-7 / ACC structural plasticity / pain comorbidity

### Task 1.3: Validation verdicts
- [ ] Verdict per claim card ∈ {CONFIRMED, REFUTED, MIXED, NO_EVIDENCE_FOUND} + citations
- [ ] Update dossier notes with "Validation (2026)" section; bump/demote graph edge confidence
- [ ] Deliverable: `analysis/validation_report.md`

### Task 1.4: Insight inference
- [ ] Link prediction (Adamic–Adar/Jaccard) restricted to cross-community pairs; triad closure on signed subgraph
- [ ] Ranked hypothesis cards → `analysis/hypotheses.md`; top hypotheses become vault notes `insights_x_{topic}.md`
- [ ] Re-run graphify to refresh communities/god-nodes

**Checkpoint: human reviews verdicts + hypotheses before Phase 2 parameterization.**

---

## Phase 2 — Aim 2: LLM-agent simulator

### File structure
```
simulator/
  schemas.py             # Pydantic models: AgentCard, WorldState, StateDelta, TickLog, Scenario
  build_cards.py         # generates agent_cards/*.yaml from graph_v2 + dossiers (+opencode)
  agent_cards/*.yaml     # 595 cards
  engine/
    orchestrator.py      # tick loop, influence packets, delta application, audit log
    llm_agent.py         # opencode-run client, batching, caching, retries
    rule_fallback.py     # compiled heuristics for peripheral tier
  readouts.py            # pain_score, barrier_integrity, inflammation_index
  scenarios/*.yaml       # naive_baseline, SNI, CCI, CIPN, drug arms (CLP257, fasudil, XPro1595)
  validation/facts.yaml  # published empirical facts as assertions
  tests/                 # pytest suite
  reports/               # run traces, plots, comparison tables (NO vault writes)
```

### Task 2.1: Schemas (`schemas.py`) — TDD
- [ ] Failing tests → implement Pydantic models: `AgentCard{id, label, entity_type, compartment, tier, baseline_state, dynamics_rules[], inbound_edges[]}`, `InfluencePacket{source_id, sign, weight, sender_state}`, `StateDelta{agent_id, tick, new_state, rationale, refs[]}`, `WorldState{tick, states{}, epoch}`, `ScenarioConfig`, `TickLog`

### Task 2.2: Card generator (`build_cards.py`)
- [ ] Per node: dossier excerpts + validated edges → LLM-distilled persona card citing claim IDs
- [ ] Human-review diff output for the 30 hub cards

### Task 2.3: Engine core — TDD
- [ ] Orchestrator: init scenario → per tick deliver inbound influence packets → agents emit deltas (LLM or rules) → validate schema+refs → apply atomically → compute readouts → append tick log
- [ ] Rule fallback: saturating linear response `Δ = clamp(Σ w_i·sign_i·s_i − decay)` with weights from edge confidence
- [ ] Epoch boundaries trigger hub-tier reasoning events

### Task 2.4: Pilot run — 30-hub disinhibition subgraph
- [ ] SNI 28-day acceptance: microglial activation → ↑BDNF/TNF/MMP-9 → ↓KCC2/PNN degradation → PV dysfunction → pain_score rise (correct causal ordering)
- [ ] CLP257 arm partially restores pain_score vs SNI

### Task 2.5: Scale-out + tiering + cost controls
- [ ] All 595 agents active; cache; budget cap; peripheral distillation script

### Task 2.6: Validation harness
- [ ] `facts.yaml`: ≥15 assertions mapped to scenario+readout windows, e.g. BDNF-TrkB blockade before day 3 prevents KCC2 loss; TNFR1-selective blockade better than pan-TNF; MMP-9 KO reduces but does not abolish allodynia; naive baseline stable 180d

### Task 2.7: Experiment reports
- [ ] Auto-generated `reports/{scenario}.md`: readout time courses, emergent cross-community events, deviations flagged; surprises feed back into Aim 1 hypothesis list

---

## Deviations from plan (post-execution record)

1. **Agent count**: "All 595 nodes" resolved to **254 agents** — one per document-type entity in the deduplicated graph. Rationale nodes (~266) are provenance annotations, not biological entities.
2. **Dynamic closure**: pilot proved the original signed subgraph acyclic and orphaned from symptom nodes; 31 evidence-backed edges (verbatim dossier quotes) + sustained-drive mechanism were added to make chronicification expressible. Provenance: `analysis/claims/closure_edges.yaml`.
3. **Peripheral distillation script** superseded by the compiled rule fallback (all non-hub agents are rules-driven by design).
4. **CCI/CIPN scenarios** deferred beyond this plan iteration.
5. **Zotero import** skipped (no MCP server available); reference lists live inside each theme file.

---

## Execution order
0.1 → 0.2 → 1.1 → 1.2/1.3 → **checkpoint: review verdicts** → 1.4 → **checkpoint: hypotheses** → 2.1 → 2.2 → 2.3 → 2.4 **checkpoint: pilot acceptance** → 2.5 → 2.6 → 2.7
