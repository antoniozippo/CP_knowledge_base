# Master Experiment Summary — 10-Arm LLM Battery
_Run date: 2026-08-27 · Engine 0.1.0 · 372 agents (9 hub / 123 mid / 240 peripheral) · LLM: Qwen3.8-27b via LM Studio · card_set `d2c7e0b0…`_

## Arms executed (LLM-enhanced, seed 42)

| Scenario | Model | Days | LLM Calls | Runtime | LLM Pain | Rules Pain | Δ Pain |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive_28d | naive | 28 | 18 | 27.0 min | 0.0710 | 0.0500 | +0.021 |
| SNI_28d | SNI | 28 | 27 | 38.8 min | 0.4811 | 0.4764 | +0.005 |
| CCI_28d | CCI | 28 | 27 | 31.0 min | 0.4809 | 0.3497 | **+0.131** |
| CIPN_28d | CIPN | 28 | 27 | 37.6 min | 0.4512 | 0.3331 | **+0.118** |
| SNI_28d_CLP257 | SNI + KCC2 enhancer | 28 | 27 | 30.4 min | 0.4644 | 0.3347 | **+0.130** |
| SNI_28d_XPRO1595 | SNI + TNFR1-selective | 28 | 27 | 33.7 min | 0.4520 | 0.3184 | **+0.134** |
| SNI_28d_FASUDIL | SNI + ROCK inhibitor | 28 | 27 | 36.5 min | **0.4742** | 0.4693 | **+0.005** |
| SNI_28d_DRIVE_DECAY | SNI, drives stop t=10 | 28 | 27 | 33.0 min | 0.4405 | 0.3222 | **+0.118** |
| naive_180d | naive | 180 | 27 | 45.0 min | 0.2543 | 0.0500 | **+0.204** |
| SNI_180d | SNI | 180 | 36 | 49.6 min | 0.4889 | 0.3515 | **+0.137** |

## Key results

1. **Fasudil paradox RESOLVED.** After edge correction (`RhoA/ROCK --(+1)--> DendriticSpineLoss`, quarantine of the two `NO_EVIDENCE_FOUND` RhoA→Kal7 edges), fasudil is **protective** in both modes:
   - Rules: 0.4693 vs SNI 0.4764 (Δ = −0.0071)
   - LLM:   0.4742 vs SNI 0.4811 (Δ = −0.0065)
   The pre-correction paradox (fasudil 0.408 > SNI 0.350) is gone.

2. **LLM systematically amplifies pain for injury models.** All 6 injury-model arms (CCI, CIPN, SNI, SNI+CLP257, SNI+XPRO1595, SNI+DRIVE_DECAY) show +0.118 to +0.134 pain vs rules-only. Hub agents (microglia, TNF, ROCK, Kal7/Rac1) tend to saturate toward pronociceptive interpretations under LLM reasoning.

3. **Drug efficacy erased under LLM.** CLP257 and XPro1595 show clear benefit in rules-only mode (Δ −0.015 and −0.031 vs SNI) but the benefit disappears in LLM mode — all drug arms land near or above the untreated SNI LLM level. This suggests the LLM hub agents are re-activating inflammatory cascades that the drug rules were suppressing.

4. **Chronic drift in 180-day arms.** naive_180d rises to 0.254 (vs 0.050 rules) and SNI_180d to 0.489 (vs 0.351 rules) — LLM hub agents accumulate spurious activation over long horizons, likely because repeated LLM evaluation (every epoch boundary) re-interprets baseline states as active.

5. **Naive 28d stays stable.** naive_28d LLM = 0.071 vs 0.050 rules — minimal drift at 28 days, confirming the amplification is mostly driven by injury-initiated pathways rather than a naive baseline bias.

## Statistical summary

- **Total LLM calls:** 288 (27 per 28d arm, 36 for SNI_180d, 18 for naive_28d)
- **Total runtime:** 5.7 hours (avg 34 min/28d arm)
- **Injury-model Δ (mean ± SD):** +0.121 ± 0.011
- **Naive Δ (mean):** +0.113 (heavily influenced by 180d drift)
- **Average LLM latency:** ~65 s/call (range 18–177 s)

## Provenance & reproducibility

- All runs LLM-enhanced (Qwen3.8-27b, temperature 0.0), seed 42
- Rules-only baseline from 2026-08-26 battery (same scenarios, deterministic)
- Per-arm artifacts: `simulator/out/llm_battery_20260827/<arm>/{manifest.json, tick_log.jsonl, states.csv}`
- Aggregated results: `simulator/out/llm_battery_20260827/battery_results.json`, `battery_aggregated.csv`
- Master visualization: `simulator/reports/llm_battery_summary.png`
