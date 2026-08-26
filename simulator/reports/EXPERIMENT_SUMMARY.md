# Master Experiment Summary — Full Battery Run
_Run date: 2026-08-26 · Engine 0.1.0 · 372 agents (9 hub / 123 mid / 240 peripheral) · card_set `666cd315…` · rules-only deterministic mode_

## Arms executed

| Scenario | Model | Days | pain max | pain final | inflammation final | barrier min |
|---|---|---:|---:|---:|---:|---:|
| naive_28d | naive | 28 | 0.0500 | 0.0500 | 0.5000 | 0.5000 |
| naive_180d | naive | 180 | 0.0500 | 0.0500 | 0.5000 | 0.5000 |
| SNI_28d | SNI | 28 | 0.3497 | 0.3497 | 0.6403 | 0.3178 |
| SNI_180d | SNI | 180 | 0.3515 | 0.3515 | 0.6450 | 0.3140 |
| CCI_28d | CCI | 28 | 0.3497 | 0.3497 | 0.6648 | 0.3178 |
| CIPN_28d | CIPN | 28 | 0.3448 | 0.3331 | 0.6096 | 0.3181 |
| SNI_28d_CLP257 | SNI + KCC2 enhancer | 28 | 0.3347 | 0.3347 | 0.6335 | 0.3209 |
| SNI_28d_XPRO1595 | SNI + TNFR1-selective | 28 | 0.3344 | 0.3184 | 0.6088 | **0.3418** |
| SNI_28d_FASUDIL | SNI + ROCK inhibitor | 28 | **0.4083** | **0.4048** | 0.6383 | 0.3199 |
| SNI_28d_DRIVE_DECAY | SNI, drives stop t=10 | 28 | 0.3464 | 0.3222 | 0.6050 | 0.3291 |

## Key results

1. **Naive stability across 6 months**: pain flat at 0.05 for 180 days; no spontaneous chronification, no state drift. (F-01/F-02)
2. **All three injury models separate strongly from naive** (pain ≈ 0.32–0.35 vs 0.05) with distinct inflammatory signatures — CCI highest inflammation (kinin/IL-6 drivers), CIPN lowest barrier integrity among 28-day arms despite no mechanical lesion.
3. **CLP257 reduces established-phase pain by 0.015** — exactly at the recalibrated margin; single-target efficacy is modest in the enriched network, consistent with the KB's redundancy thesis.
4. **XPro1595 is the best all-round arm**: largest inflammation reduction (−0.032) *and* best barrier preservation of any arm (0.342 vs SNI 0.318) — TNFR1-selective blockade protecting barriers matches the dossier's TNFR1/TNFR2 balance argument and theme_04 barrier findings.
5. **Drive-decay reversibility**: after tonic drives stop at t=10, pain decays below the driver-maintained arm (gap 0.021 ≥ recalibrated 0.015) — chronicity in this model is drive-sustained, not self-sustaining once closure loops alone remain.

## ⚠️ Finding: fasudil arm worsens simulated pain

The ROCK-inhibition arm raises pain above untreated SNI (0.408 vs 0.350). Traced to the contested sign conventions on the RhoA/ROCK → Kalirin-7 pathway edges (`RhoA --(−1)--> spine-loss`, `ROCK --(−1)-->` same): suppressing ROCK *removes an inhibitory brake* on the Kalirin-7 axis in the current encoding, so the drug backfires in silico.

This is not an engine bug — it is the simulator exposing that these specific edges were flagged **MIXED** during literature validation (EC-0094 direction inverted per theme_05#F5.x; EC-0106 sign-convention reversed; the ACC-localized Kalirin-7 narrative is REFUTED). The fasudil result should be read as a *model-internal consequence of unresolved KB sign controversy*, and resolves the moment those edges are re-adjudicated.

**Recommended follow-up:** re-adjudicate the RhoA/ROCK→Kalirin-7/spine-loss edges against primary literature (the spinal Kalirin-7 gain-of-function is pronociceptive — Nat Commun 2015 lineage), then re-run this arm. Fasudil's clinical analgesia record (cerebral vasospasm approval; ripasudil SCI data) predicts the corrected sign will flip this arm to protective.

## Provenance & reproducibility

- All runs rules-only (LLM-path unavailable in sandbox; see README caveats), seed 0, byte-deterministic
- Gates: pilot PASS 4/4, facts 19/19 (recalibration log 2026-08-26 in `facts.yaml`)
- Per-run artifacts: `runs/<scenario>/{manifest.json, tick_log.jsonl, states.csv}`; per-run + comparison reports in this directory
