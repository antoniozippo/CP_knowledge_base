# Chronic Pain Simulator — Results Summary

## Executive Summary

**Fasudil paradox resolved** through literature-driven edge correction + validated with live LLM simulation.

| Metric | SNI Rules | SNI LLM | Fasudil LLM | Effect |
|--------|-----------|---------|-------------|--------|
| Pain (Day 28) | 0.4764 | 0.4807 | 0.4744 | **−0.0063 PROTECTIVE** |

---

## Visualizations

### 1. Pain Trajectories & Treatment Effect
![Pain Trajectories](results_summary.png)

**Key observations:**
- LLM adds slight upward bias (+0.004 to +0.044) vs rules-only
- Fasudil effect emerges after day 14 (TRANSITION epoch)
- Both simulation modes show **protective** fasudil effect
- Epoch boundaries (days 0, 4, 15) marked where LLM evaluates hub agents

### 2. Corrected Signaling Network
![Network Diagram](network_corrected_edges.png)

**Edge correction:**
- ❌ **Quarantined:** `RhoA/ROCK --(−1)--> Kalirin-7` (sign=0, REFUTED)
- ✅ **Added:** `ROCK → DendriticSpineLoss (+1)` from Tian et al. 2017
- **Mechanism:** Fasudil inhibits ROCK → reduces spine loss → preserves Kal7/Rac1 spine gain → analgesia

### 3. LLM Integration Architecture
![Architecture](llm_architecture.png)

**Architecture highlights:**
- 9 HUB agents use live LLM (Qwen3.8-27b via LM Studio)
- 123 MID + 240 PERIPHERAL agents use deterministic rules
- LLM called at epoch boundaries (ticks 0, 4, 15) + injury tick
- Average latency: 69.9s/call (27 calls total)
- Full 28-day run: ~72 minutes

---

## Key Results

### Simulation Outputs

| Run | Directory | LLM Calls | Runtime | Pain (D28) |
|-----|-----------|-----------|---------|------------|
| SNI Rules-only | `simulator/out/sni_baseline/` | 0 | <1s | 0.4764 |
| SNI LLM | `simulator/out/SNI_28d_LLM/` | 27 | 72 min | 0.4807 |
| Fasudil Rules | `simulator/out/fasudil_check/` | 0 | <1s | 0.4693 |
| Fasudil LLM | `simulator/out/FASUDIL_LLM/` | 27 | 72 min | 0.4744 |

### Edge Correction Evidence

| Edge | Old Sign | New Sign | Status | Evidence |
|------|----------|----------|--------|----------|
| RhoA → Kal7 | −1 | 0 (quarantined) | REFUTED | No evidence; contradicted by fasudil analgesia |
| ROCK → Kal7 | −1 | 0 (quarantined) | REFUTED | No evidence; contradicted by fasudil analgesia |
| ROCK → SpineLoss | — | +1 | ADDED | Tian et al. Sci Rep 2017: fasudil prevents TBI spine loss |

### Literature Adjudication (theme_10#A10.1)

1. **Kal7 = Rac1-GEF** (not RhoA-GEF) — Nat Commun 2015 (ncomms7820)
2. **RhoA-ROCK → spine RETRACTION** — Sci Rep 2017 (s41598-017-11113-3)
3. **Antithetical pathways**: Kal7/Rac1 (spine gain) vs RhoA/ROCK (spine loss)
4. **Fasudil analgesia**: 77% SNL allodynia reduction in vivo

---

## Commits

| Commit | Message |
|--------|---------|
| `d9cb64a` | fix: quarantine RhoA/ROCK→Kal7 edges, resolve fasudil paradox |
| `e674141` | feat: add LocalLLMClient for OpenAI-compatible endpoints |
| `d62c0d7` | feat: LLM simulation complete + fasudil paradox resolved |

All pushed to: `https://github.com/antoniozippo/CP_knowledge_base`

---

## Files

```
simulator/reports/
├── results_summary.png          # Pain trajectories + treatment effect + latency
├── network_corrected_edges.png  # Signaling network with corrected edges
├── llm_architecture.png         # LLM-agent simulator architecture
└── RESULTS_SUMMARY.md           # This file
```

---

## Next Steps

1. **Run full 10-arm battery** with LLM-enhanced simulation
2. **Integrate Zotero→Obsidian** for continuous literature updates
3. **Add uncertainty quantification** via LLM ensemble or temperature sampling
4. **Validate against experimental datasets** (behavioral time-courses)
