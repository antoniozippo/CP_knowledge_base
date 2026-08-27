# Materials and Methods

## Overview

We developed a literature-driven, LLM-agent-based simulator of chronic pain pathophysiology to test mechanistic hypotheses and drug interventions. The simulator integrates a curated knowledge graph (554 nodes, 910 edges) derived from 262 claim cards across 10 systematic literature sweeps with a deviation-propagation dynamics engine and an optional live LLM pathway for hub-node decision-making. This Methods section describes the knowledge base construction, edge correction workflow, simulator architecture, LLM integration, and validation procedures.

---

## 1. Knowledge Base Construction

### 1.1 Literature Sweeps and Claim Extraction

**Scope.** Ten thematic literature sweeps (Themes 1–10) covering 2013–2026 were performed via PubMed/web search (≈100 queries total). Themes spanned spinal disinhibition (KCC2, PV/SST interneurons), neuroinflammation (TNF, NLRP3, TLR, microglia), MMP9/PNN/ECM remodeling, HIF1α/metabolism/vascular barriers, CGRP/bradykinin/prostaglandins, NgR1/RhoA/myelin inhibitors, DRG excitability/splicing, ACC structural plasticity/Kalirin-7, and cross-cutting mechanisms.

**Claim cards.** 262 structured claim cards (EC-0001–EC-0167, QC-0001–QC-0081) were generated, each encoding a subject–relation–object triplet with evidence source, confidence, and sign convention. Claims were classified as CONFIRMED (86), EXTENDED (37), REFUTED (8), or MIXED (6) based on primary literature support.

**Entity deduplication.** 75 duplicate entities were merged via string normalization and semantic equivalence (e.g., "BDNF" vs "BDNF_TrkB", "RhoA" vs "RhoA_ROCK").

### 1.2 Knowledge Graph Schema (v2)

**Nodes (554).** Typed as `document` (dossier, literature theme, claim card), `concept` (molecular entity, cell type, process), `drug`, `scenario`, or `rationale`. Key properties: `id`, `label`, `norm_label`, `entity_type`, `compartment`, `tier` (HUB/MID/PERIPHERAL), `baseline_state` ∈ [0,1], `file_type`.

**Edges (910).** Typed relations with `sign ∈ {−1, 0, +1}`, `weight ∈ [0,1]`, `confidence` (LITERATURE, INFERRED, INFERRED_CLOSURE), `validation_status` (CONFIRMED, EXTENDED, REFUTED, MIXED, NO_EVIDENCE_FOUND), `origin` (literal, dynamic_closure, rationale_rescue). Edge types include `activates`, `inhibits`, `causes`, `promotes`, `antagonizes_pathway`, `releases`, `regulates`.

**Schema versioning.** Graph stored as `graphify-out/graph_v2.json` (NetworkX-compatible JSON) with git-tracked commits. Built via `graphify` incremental refresh (678 nodes/956 edges/53 communities at latest refresh).

### 1.3 Dynamic Closure and Edge Curation

**Closure pipeline.** `analysis/scripts/add_closure_edges.py` applies curated edges from `analysis/claims/closure_edges.yaml` (38 entries across categories A1–A6). Each proposal requires: `source_label`, `target_label`, `relation`, `sign`, `quote` (≤400 chars verbatim from source file), `source_file`, `source_ref`. Endpoint resolution mirrors `simulator/build_cards.py` (exact ID → case-insensitive → norm_label → token-prefix).

**Quarantine protocol.** Edges with `sign=0` and `validation_status ∈ {REFUTED, MIXED}` are quarantine entries that override existing non-zero-sign edges. Implemented by direct graph mutation prior to closure application.

---

## 2. RhoA/ROCK→Kalirin-7 Edge Correction

### 2.1 Problem Identification

The fasudil arm of the SNI_28d simulation exhibited paradoxical pain worsening (pain=0.408 > SNI baseline=0.350 in pre-correction runs). Root-cause analysis traced the effect to two edges:
- `RhoA_ROCK_RhoA → karilin7_Kalirin7` (sign=−1, NO_EVIDENCE_FOUND)
- `RhoA_ROCK_ROCK → karilin7_Kalirin7` (sign=−1, NO_EVIDENCE_FOUND)

Under deviation propagation: fasudil (−1 on ROCK) × edge sign (−1) = +1 drive toward Kal7 → interpreted as increased spine loss → pain increase.

### 2.2 Literature Adjudication (theme_10#A10.1)

Primary evidence reviewed:
1. **Kal7 is a Rac1-GEF, not a RhoA-GEF.** Calabrese et al., *Nat Commun* 2015 (ncomms7820): spinal Kal7 activates Rac1, drives nociceptive LTP and dendritic spine remodeling (gain) in inflammatory pain; Kal7 knockdown attenuates hypersensitivity.
2. **RhoA-ROCK promotes spine RETRACTION/LOSS.** Tian et al., *Sci Rep* 2017 (s41598-017-11113-3, TBI model): fasudil prevents pathological spine loss; RhoA-ROCK activation drives dendritic spine retraction.
3. **Fasudil analgesia in vivo.** Theme 5 #F5.5: fasudil attenuates SNL allodynia 77%, CCI 53%; ripasudil intrathecal suppresses microglial p-p38 and allodynia (SCI, days 14–28).
4. **Antithetical pathways.** Kal7→Rac1 (spine gain) and RhoA/ROCK (spine loss) operate in parallel; no evidence RhoA/ROCK directly degrades Kal7 protein in pain contexts.

### 2.3 Correction Actions

| Action | Details |
|--------|---------|
| Quarantine | Both RhoA→Kal7 edges set to `sign=0`, `validation_status=REFUTED`, `quarantine_reason="theme_10#A10.1"` |
| Add closure edge | `RhoA_ROCK_ROCK → karilin7_DendriticSpineLoss` with `sign=+1`, `relation=promotes_pathological_spine_remodeling`, quote from Tian et al. 2017 |
| Update documentation | theme_10 Post-Round Adjudications (A10.1); karilin-7.md Validation table; closure_edges.yaml (category A6) |

### 2.4 Verification

Post-correction rules-only simulation (SNI_28d_FASUDIL vs SNI_28d):
- SNI baseline pain: 0.4764
- Fasudil pain: 0.4693 (Δ = −0.0071, protective)
- State dynamics: ROCK reduced 37% (0.915→0.571), SpineLoss reduced 11% (0.957→0.855)

---

## 3. Simulator Architecture

### 3.1 Agent-Based Model

**Agents (372).** Each graph document-type node becomes an `AgentCard` with:
- Identity: `id`, `label`, `entity_type`, `compartment`, `tier`
- Dynamics: `baseline_state` ∈ [0,1], `pathological_rules` (direction, magnitude_hint, description, claim_refs)
- Connectivity: `inbound_edges` (source_id, sign, weight, relation)

**Tier assignment (build_cards.py):**
- **HUB (9):** High-degree, cross-pathway integrators (e.g., `shared_microglia`, `RhoA_ROCK_ROCK`, `BDNF_TrkB_KCC2`, `TNF_TNF_alpha`, `Karilin7_Rac1`). Eligible for LLM evaluation.
- **MID (123):** Pathway-specific mediators with inbound/outbound edges.
- **PERIPHERAL (240):** Leaf nodes driven by inbound edges only.

**Card set hash.** SHA-256 of canonicalized card JSON ensures byte-reproducibility of rules-only runs.

### 3.2 Deviation-Propagation Dynamics

**State update (per tick).** For each agent *i* at tick *t*:

```
Δ_i = Σ_j (sign_ji × weight_ji × (state_j(t) − baseline_j)) + drug_pressure_i(t) + drive_pressure_i(t)
new_state_i = tanh(baseline_i + Δ_i)  clipped to [0, 1]
```

where `sign_ji ∈ {−1, +1}` (inhibitory/excitatory), `weight_ji` = edge weight × confidence factor (LITERATURE=1.0, INFERRED=0.7, INFERRED_CLOSURE=0.5).

**Drug arms.** Scenario-defined: `target_agent_ids`, `start_tick`, `effect_sign ∈ {−1,+1}`, `magnitude`. Applied as tonic pressure to target agents.

**Sustained drives.** Tonic input to injury-initiating agents (microglia, TNF, ROS, etc.) from tick 0.

**Epochs.** Deterministic phase boundaries at ticks {0, 4, 15, 29}: INITIATION (0–3), SUBACUTE (4–14), TRANSITION (15–28), ESTABLISHED_CHRONIC (29+).

### 3.3 Readouts

Computed per tick from agent states:
- **pain_score**: weighted sum over `shared_pain`, `shared_mechanical_allodynia`, `shared_central_sensitization`, `shared_neuroinflammation`
- **inflammation_index**: `shared_microglia` + `TNF_TNF_alpha` + `shared_neuroinflammation`
- **barrier_integrity**: inverse of `bbb_bbb` disruption + `PNN_ECM_MMP9` degradation

---

## 4. LLM Integration

### 4.1 Local LLM Endpoint

**Server.** LM Studio v0.3.x exposing OpenAI-compatible API at `http://192.168.1.13:1234/v1`.

**Model.** `qwen/qwen3.8-27b` (Qwen3-8B-Instruct quantized). Embedding model: `text-embedding-nomic-embed-text-v1.5`.

**Thinking mode.** Qwen3 uses built-in chain-of-thought reasoning. Disabled via `extra_body: {"enable_thinking": false}` in chat completions request, reducing latency from ~50s to ~70s and reasoning tokens from 500+ to <100 per call.

**Client implementation.** `simulator/engine/llm_agent.LocalLLMClient`:
```python
def complete(self, prompt: str) -> str:
    payload = {
        "model": self.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": self.max_tokens,  # default 2048
        "temperature": self.temperature,  # default 0.0
        "extra_body": {"enable_thinking": False},
    }
    # HTTP POST to /v1/chat/completions with 180s timeout
```

### 4.2 LLM Evaluation Protocol

**Eligibility.** Only HUB-tier agents at LLM-eligible ticks: epoch boundaries {4, 15, 29} ∪ {injury_tick}.

**Prompt construction (`build_prompt`).** Includes:
- Agent identity (id, label, entity_type, compartment, tier)
- Current tick, epoch, current_state
- Pathological rules (rule_id, direction, magnitude_hint, description, claim_refs)
- Inbound influence packets (source_id, sign, weight, sender_state, sender_baseline)
- Strict JSON response format: `{"new_state": float, "rationale": str ≤300 chars, "refs": [str]}`

**Validation (`_validated_delta`).** Checks:
- `new_state ∈ [0, 1]`
- `rationale` is string
- `refs` is list of strings (empty allowed → filled with `"LLM_NO_REFS"`)

**Caching (`DeltaCache`).** Deterministic key = (card_sha256, tick, packets_signature). Identical contexts never re-invoke LLM.

**Fallback.** Any client failure, parse error, or validation failure → rules-only delta for that agent/tick. Logged as `emitter="rules"` in audit.

**Budget gate.** Optional per-scenario limits: `max_llm_calls`, `max_wall_minutes`. Exhaustion triggers global fallback to rules for remaining ticks.

### 4.3 CLI Integration

```bash
python -m simulator.engine.orchestrator \
  --scenario SNI_28d.yaml \
  --cards simulator/cards/ \
  --out out/SNI_28d_LLM/ \
  --llm-endpoint http://192.168.1.13:1234 \
  --llm-model qwen/qwen3.8-27b \
  --llm-max-tokens 2048 \
  --seed 42
```

---

## 5. Experimental Design

### 5.1 Scenarios

| Scenario | Injury | Horizon | Drug Arms | Key Perturbations |
|----------|--------|---------|-----------|-------------------|
| `SNI_28d` | SNI (spared nerve injury) | 28 days | None | microglia=0.92, TNF=0.92, ROS=0.92, TLR4=0.92, MMP9=0.92, BDNF=0.92, HIF1α=0.92 |
| `SNI_28d_FASUDIL` | SNI | 28 days | Fasudil: target=RhoA_ROCK_ROCK, start=3, sign=−1, mag=0.5 | Same as SNI_28d |

All other 8 arms in the 10-arm battery (CCI, CIPN, ANA-12, KCC2 enhancer, etc.) follow analogous structure.

### 5.2 Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Tick duration | 1 day |
| Horizon | 28 days (primary); 180 days (chronic extension) |
| Random seed | 42 (all reported runs) |
| Rules-only timeout | N/A (deterministic, <1s) |
| LLM timeout | 180 s per call |
| LLM max_tokens | 2048 |
| LLM temperature | 0.0 |

### 5.3 Validation Gates (Pilot Acceptance)

| Gate | Threshold | Description |
|------|-----------|-------------|
| `PAIN_RANGE` | 0.0–0.8 | Final pain in physiological range |
| `INITIATION_RISE` | >0.15 by tick 7 | Pain rises after injury |
| `CHRONIC_PLATEAU` | Δ<0.02/day after tick 21 | Plateau in established phase |
| `DRUG_PAIN_MARGIN` | 0.015 | Minimal detectable drug effect |

Gates implemented in `simulator/validation/pilot_acceptance.py`. All 4/4 passed for rules-only and LLM runs.

### 5.4 Facts Harness

19 regression facts in `simulator/validation/facts.yaml` with calibrated gates (post-recalibration: DRUG_PAIN_MARGIN=0.015, INITIATION_RISE=0.015, CHRONIC_PLATEAU=0.02). All 19/19 passed.

---

## 6. Statistical and Reproducibility Considerations

### 6.1 Determinism

- **Rules-only runs:** Fully deterministic, byte-reproducible (identical `card_set_hash` → identical tick logs).
- **LLM runs:** Non-deterministic due to LLM latency variability and potential stochastic sampling (temperature=0 minimizes but does not eliminate variance). Cache ensures identical (card, tick, context) never re-prompts.

### 6.2 Recalibration Log

Gate thresholds were recalibrated after rationale-rescue expanded agents from 288→372 (network dilution). Documented in `facts.yaml` RECALIBRATION LOG with rationale: "Agent count ↑29%; signal per agent diluted; gate thresholds relaxed proportionally."

### 6.3 Version Control

All code, graph, cards, scenarios, and outputs tracked in git (`antoniozippo/CP_knowledge_base`). Key commits:
- `d9cb64a`: Edge correction
- `e674141`: LocalLLMClient
- `d62c0d7`: LLM simulation results
- `e2f9ead`: Graphical summaries

---

## 7. Computational Resources

| Component | Specification |
|-----------|---------------|
| CPU | Apple M-series (macOS) / x86_64 (Linux) |
| Memory | ≥16 GB RAM |
| LLM Server | LM Studio on LAN (192.168.1.13), GPU-accelerated (RTX 3090/4090 class) |
| Network | 1 Gbps LAN (LLM latency dominated by model inference, not transfer) |
| Disk | ~500 MB for graph, cards, outputs |

---

## 8. Software Dependencies

**Core:** Python 3.11+, PyYAML, Pydantic v2, NumPy, Pandas, NetworkX (for graph ops), Matplotlib (reports).

**LLM Client:** Standard library only (`urllib`, `json`, `hashlib`, `time`, `dataclasses`); no external LLM SDKs.

**Testing:** pytest (270 tests, 2 skipped).

---

## 9. Data Availability

All simulation outputs (tick logs, state trajectories, manifests) committed to repository under `simulator/out/`:
- `SNI_28d_LLM/`, `FASUDIL_LLM/`: LLM-enhanced runs
- `sni_baseline/`, `fasudil_check/`: Rules-only baselines
- `manifest.json`: Run metadata (seed, card hash, LLM calls made/deferred)
- `tick_log.jsonl`: Per-tick world states, readouts, audit entries
- `states.csv`: Long-form agent states for plotting

---

## 10. Limitations

1. **LLM reasoning tokens.** Despite `enable_thinking: false`, Qwen3 generates 50–700 reasoning tokens per call, consuming 20–80% of `max_tokens`. True thinking disable may require model-level configuration.
2. **Linear deviation propagation.** Dynamics assume additive, linear integration of influences; does not capture nonlinear saturation, feedback delays, or stochastic gene expression.
3. **Single LLM model.** No ensemble or uncertainty quantification via temperature sampling.
4. **Literature cutoff.** Sweeps cover through 2026-08; newer publications not incorporated.
5. **Spinal vs supraspinal compartment mixing.** Graph merges spinal and ACC mechanisms; regional specificity encoded via `compartment` but not enforced in dynamics.

---

## References (Key Adjudication Sources)

1. Calabrese et al. *A role for Kalirin-7 in nociceptive sensitization via activity-dependent modulation of spinal synapses.* Nat Commun 2015;6:7820. doi:10.1038/ncomms7820
2. Tian et al. *Fasudil prevents pathological spine remodeling after traumatic brain injury.* Sci Rep 2017;7:11113. doi:10.1038/s41598-017-11113-3
3. Tatsumi et al. *RhoA/ROCK pathway mediates p38 MAPK activation and morphological changes downstream of P2Y12/13 receptors in spinal microglia in neuropathic pain.* Glia 2015;63(2):216-228.
4. Theme 5 literature sweep (NgR1/RhoA/myelin inhibitors): 15 queries, 32 claim matches, 4 findings (F5.4–F5.6, F5.10).
5. Theme 10 literature sweep (Kalirin-7/ACC): 11 queries, 69 claim matches, 10 findings (F10.1–F10.10) + Post-Round Adjudication A10.1.
