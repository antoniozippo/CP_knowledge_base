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
| SNI | sni_28d | SNI @ tick 0 | all seven drivers seeded at 0.92: microglia, TNF-a, ROS, TLR4 (DAMP proxy), MMP-9, BDNF, HIF1a | none |
| CLP257 | sni_28d_clp257 | SNI @ tick 0 | identical to SNI | clp257 -> BDNF_TrkB_KCC2, +0.6 from tick 3 |
| naive | naive_28d | none | none | none |

## Event table (SNI arm)

| entity | agent id | baseline | direction | crossing tick |
|---|---|---|---|---|
| microglia | shared_microglia | 0.50 | up | 1 |
| tnf_alpha | TNF_TNF_alpha | 0.50 | up | 1 |
| bdnf | assaying_molecularly_structural_plasticity_BDNF | 0.50 | up | 1 |
| mmp9 | PNN_ECM_MMP9 | 0.50 | up | 1 |
| kcc2_drop | BDNF_TrkB_KCC2 | 0.50 | down | never |
| pnn_loss | GABA_apoptosis_PNN_loss | 0.50 | up | never |
| pv_dysfunction | PV_interneurons_PV_interneurons | 0.50 | down | never |
| sst_interneurons | SST_somatostatin_interneurons | 0.50 | up | never |
| pain_readout | <readout:pain_score> | 0.05 | up | never |

## Ordering check (tie tolerance +/-1 tick)

| step | earlier tick | later tick | verdict |
|---|---|---|---|
| microglia <= tnf/bdnf | 1 | 1 | PASS |
| tnf/bdnf <= mmp9 | 1 | 1 | PASS |
| mmp9 <= kcc2-drop/pnn | 1 | never | FAIL |
| kcc2-drop/pnn <= pv-dysfunction | never | never | FAIL |
| pv-dysfunction <= pain-rise | never | never | FAIL |

## Drug effect and separation numbers

- mean pain_score ticks 14-28: SNI 0.0416, CLP257 0.0416, naive 0.0500
- mean KCC2 state ticks >= 14: SNI 0.4934, CLP257 0.9012

## Criteria verdicts

| criterion | verdict | detail |
|---|---|---|
| drug_effect_pain_lower | **FAIL** | mean pain_score ticks 14-28: SNI=0.0416 CLP257=0.0416 SNI-CLP257=+0.0000 (required >=0.03) |
| drug_effect_kcc2_higher | **PASS** | mean BDNF_TrkB_KCC2 state ticks >= 14: SNI=0.4934 CLP257=0.9012 margin=+0.4078 |
| naive_separation | **FAIL** | mean pain_score ticks 14-28: SNI=0.0416 naive=0.0500 SNI-naive=-0.0084 (required >=0.05) |
| event_ordering | **FAIL** | microglia <= tnf/bdnf:ok; tnf/bdnf <= mmp9:ok; mmp9 <= kcc2-drop/pnn:FAIL; kcc2-drop/pnn <= pv-dysfunction:FAIL; pv-dysfunction <= pain-rise:FAIL |

Overall: **FAIL**

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

Structural topology facts discovered by this pilot (relevant to any FAIL
verdict above; thresholds were NOT weakened):

- The influence graph is acyclic outside one unrelated 2-cycle
  (ana_12_ANA_12 <-> ana_12_TrkB_T1), so no seed produces a sustained
  elevation: every deviation decays back to baseline within ~10 ticks.
  Windowed means over ticks 14-28 therefore measure near-baseline noise.
- The three symptom-type cards that form pain_score are karilin7_PainRelatedAnxiety
  (reaches pain only via karilin7_Kalirin7), plus shared_mechanical_allodynia and
  strategic_biomarker_rbfox1, both of which have zero inbound edges and stay
  frozen at 0.05.
- BDNF_TrkB_KCC2 has zero outbound receivers: clp257 pressure raises KCC2's
  own state but cannot propagate to any other agent, so the pain difference
  between the SNI and CLP257 arms is exactly 0 regardless of seeds or
  magnitude. Restoring drug sensitivity requires adding downstream edges
  from KCC2 (or from a KCC2-downstream inhibitory interneuron card) into
  the pain pathway in the next card-set revision.
