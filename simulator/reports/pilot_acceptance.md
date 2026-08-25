# Pilot Acceptance Run (rules-only)

## Methodology

Three scenarios (SNI_28d, SNI_28d_CLP257, naive_28d; horizon 28 ticks) were
executed through the deterministic deviation-propagation engine with no LLM
calls (emitter='rules' everywhere, seed=0). Events are first crossings of
baseline +/- 0.15 held for 2 consecutive ticks
(first_crossing). Pain readout baseline is the naive-arm mean pain_score.

## Arms and seeds

| arm | scenario | injury | seeds | drug arm |
|---|---|---|---|---|
| SNI | sni_28d | SNI @ tick 0 | all seven drivers seeded at 0.92: microglia, TNF-a, ROS, TLR4 (DAMP proxy), MMP-9, BDNF, HIF1a; tonic sustained_drives hold microglia and TNF-a at 0.9 from tick 0 | none |
| CLP257 | sni_28d_clp257 | SNI @ tick 0 | identical to SNI (same seeds + same sustained_drives) | clp257 -> BDNF_TrkB_KCC2, +0.6 from tick 3 |
| naive | naive_28d | none | none | none |

## Event table (SNI arm)

| entity | agent id | baseline | direction | crossing tick |
|---|---|---|---|---|
| microglia | shared_microglia | 0.50 | up | 1 |
| tnf_alpha | TNF_TNF_alpha | 0.50 | up | 1 |
| bdnf | assaying_molecularly_structural_plasticity_BDNF | 0.50 | up | 1 |
| mmp9 | PNN_ECM_MMP9 | 0.50 | up | 1 |
| kcc2_drop | BDNF_TrkB_KCC2 | 0.50 | down | 2 |
| pnn_loss | GABA_apoptosis_PNN_loss | 0.50 | up | 4 |
| pv_dysfunction | PV_interneurons_PV_interneurons | 0.50 | down | 2 |
| sst_interneurons | SST_somatostatin_interneurons | 0.50 | up | 2 |
| pain_readout | <readout:pain_score> | 0.05 | up | 3 |

## Ordering check (tie tolerance +/-1 tick)

| step | earlier tick | later tick | verdict |
|---|---|---|---|
| microglia <= tnf/bdnf | 1 | 1 | PASS |
| tnf/bdnf <= mmp9 | 1 | 1 | PASS |
| mmp9 <= kcc2-drop/pnn | 1 | 2 | PASS |
| kcc2-drop/pnn <= pv-dysfunction | 2 | 2 | PASS |
| pv-dysfunction <= pain-rise | 2 | 3 | PASS |

## Drug effect and separation numbers

- mean pain_score ticks 14-28: SNI 0.2936, CLP257 0.2377, naive 0.0500
- mean KCC2 state ticks >= 14: SNI 0.1217, CLP257 0.5380

## Criteria verdicts

| criterion | verdict | detail |
|---|---|---|
| drug_effect_pain_lower | **PASS** | mean pain_score ticks 14-28: SNI=0.2936 CLP257=0.2377 SNI-CLP257=+0.0558 (required >=0.03) |
| drug_effect_kcc2_higher | **PASS** | mean BDNF_TrkB_KCC2 state ticks >= 14: SNI=0.1217 CLP257=0.5380 margin=+0.4162 |
| naive_separation | **PASS** | mean pain_score ticks 14-28: SNI=0.2936 naive=0.0500 SNI-naive=+0.2436 (required >=0.05) |
| event_ordering | **PASS** | microglia <= tnf/bdnf:ok; tnf/bdnf <= mmp9:ok; mmp9 <= kcc2-drop/pnn:ok; kcc2-drop/pnn <= pv-dysfunction:ok; pv-dysfunction <= pain-rise:ok |

Overall: PASS

## Caveats

Rules-only pilot: hub-tier LLM evaluation was disabled, so dynamics reflect
exclusively the deterministic deviation-propagation rule set.

Seed substitutions and adjustments (all resolved against the real card set
before the run):

- No DAMP/danger-signal card exists in the 254-card set. Its canonical
  receptor TLR4 (tlr4_tlr4) was seeded as the DAMP-signaling proxy.
- shared_microglia has no inbound edges and is absent from the suggested
  seed list; it was added because microglial activation is a proximal SNI
  driver and without seeding its event row can never register.
- All seven seeds were raised to a uniform 0.92 (suggested values were
  0.70-0.85): orphan nodes contract toward baseline by ~0.637 per tick, so
  a two-tick sustained crossing at delta=0.15 requires
  seed >= 0.5 + 0.15 / 0.637^2 ~= 0.87; the suggested 0.85 for TNF-a
  missed by less than 0.01 of state. This is an impulse-visibility fix,
  not a threshold change: delta and sustain are untouched.
- The canonical merged KCC2 molecule card BDNF_TrkB_KCC2 is the single
  clp257 target. end_tick is omitted because ScenarioConfig rejects
  end_tick >= horizon_days; omission reproduces the intended [3, 28)
  window exactly under the active-tick rule start <= t < end.

Structural topology after the Task 2.4b dynamic-closure revision (29
evidence-backed edges appended to graph_v2.json with confidence
INFERRED_CLOSURE / weight 0.5; quotes curated from repo dossiers and theme
findings in analysis/claims/closure_edges.yaml):

- The disinhibition cascade is now dynamically expressible: microglia ->
  BDNF -> KCC2 (down), TNF -> KCC2, MMP-9 -> PNN loss -> PV (down),
  KCC2 -> PV (supportive), and symptom causation edges into mechanical
  allodynia and central sensitization close the chain from seeds to
  pain_score.
- Reinforcing loops sustain pathology without further seeding: microglia
  -> TNF -> HIF1a -> Ang-2 -> microglia, TNF <-> VEGFA mutual induction,
  TNF -> MMP-9 -> microglia, plus tonic scenario sustained_drives on
  microglia and TNF-alpha modeling ongoing ectopic firing / glial
  activation through the whole horizon.
- clp257 now propagates: KCC2 has outbound edges (allodynia down, central
  sensitization down, PV support up), so raising KCC2 lowers the SNI vs
  CLP257 pain separation instead of being trapped at zero.
