# CP Simulator Experiment Report



## 1. Run Overview

- run_dir: simulator/reports/runs/CIPN_28d
- scenario: cipn_28d
- injury_model: CIPN
- injury_tick: 0
- horizon_days: 28
- seed: 0
- engine_version: 0.1.0
- started_at_utc: 2026-08-26T13:26:40Z
- generated_at: 2026-08-26T13:29:36Z
- llm_calls_made: 0
- llm_calls_deferred: 0
- notes: Chemotherapy-induced peripheral neuropathy (paclitaxel-type). Mechanistically distinct from traumatic models: NO mechanical nerve lesion; axonal mitochondrial dysfunction and oxidative stress are the primary drivers, with TLR4-dependent glial activation. Seeds emphasize the axonal-mitotoxic axis (mitochondrial dysfunction, ROS) plus TLR4/TNF/IL-6 neuroinflammation; BDNF and MMP-9 seeded lower than SNI/CCI reflecting their secondary role. Sustained drives model a fractional dosing schedule: tonic ROS/mitochondrial/ TNF elevation during the treatment window only (ticks 0-11), so the post-treatment trajectory probes partial reversibility versus persistence, the clinically decisive question for CIPN.

## 2. Readout Trajectories

![readout trajectories](plots/CIPN_28d_readouts.png)

| day | pain_score | inflammation_index | barrier_integrity |
|---|---|---|---|
| 2 | 0.1382 | 0.5858 | 0.4596 |
| 4 | 0.2101 | 0.5917 | 0.4270 |
| 6 | 0.2484 | 0.6011 | 0.3905 |
| 8 | 0.2809 | 0.6114 | 0.3620 |
| 10 | 0.3071 | 0.6197 | 0.3431 |
| 12 | 0.3256 | 0.6263 | 0.3312 |
| 14 | 0.3374 | 0.6229 | 0.3235 |
| 16 | 0.3430 | 0.6185 | 0.3193 |
| 18 | 0.3448 | 0.6163 | 0.3181 |
| 20 | 0.3440 | 0.6152 | 0.3193 |
| 22 | 0.3419 | 0.6142 | 0.3220 |
| 24 | 0.3393 | 0.6129 | 0.3267 |
| 26 | 0.3362 | 0.6113 | 0.3321 |
| 28 | 0.3331 | 0.6096 | 0.3372 |

## 3. Key Entity Traces

### CSF1-CSF1R_SpinalMicroglia — Spinal Microglia (Activated) (key: microglia)

state ▅▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.7378 vs baseline 0.5000 -> delta +0.2378

### GABA_apoptosis_TNF_alpha — TNF-α (Pro-Inflammatory Cytokine) (key: TNF)

state ▆▆▆▆▆▆▆▆▇▇▇▇▇▇▇▇▇▇▇▇▆▆▆▆▆▆▆▆
final 0.7784 vs baseline 0.5000 -> delta +0.2784

### BDNF_TrkB_proBDNF — proBDNF (key: BDNF)

state ▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅
final 0.5000 vs baseline 0.5000 -> delta +0.0000

### BBB_CypA_MMP9_pathway — CypA-MMP-9 Pathway (key: MMP-9)

state ▅▅▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.7146 vs baseline 0.5000 -> delta +0.2146

### BDNF_TrkB_CLP257 — CLP257 (KCC2 Enhancer) (key: KCC2)

state ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
final 0.0000 vs baseline 0.0000 -> delta +0.0000

### GABA_apoptosis_PNN_loss — Perineuronal Net (PNN) Loss and GABAergic Hyperactivity (key: perineuronal)

state ▅▅▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.6990 vs baseline 0.5000 -> delta +0.1990

### PV_interneurons_PV_interneurons — Parvalbumin (PV) Interneurons (key: parvalbumin)

state ▄▄▃▃▃▃▂▂▂▂▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
final 0.0271 vs baseline 0.5000 -> delta -0.4729

### shared_mechanical_allodynia — Mechanical Allodynia (key: allodynia)

state ▂▂▃▃▄▄▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.6634 vs baseline 0.0500 -> delta +0.6134


## 4. Emergent Events

Top single-tick state changes (pre-tick 0 reconstructed from card baselines and scenario initial_perturbations):

| rank | day | agent | label | delta | direction | propagation |
|---|---|---|---|---|---|---|
| 1 | 1 | GABA_apoptosis_TNF_alpha | TNF-α (Pro-Inflammatory Cytokine) | +0.1597 | up |  |
| 2 | 1 | GABA_apoptosis_HIF1alpha | HIF1α (Hypoxia-Inducible Factor 1 Alpha) | +0.1510 | up | cross-community |
| 3 | 1 | tlr4_tlr4 | TLR4 (Toll-like Receptor 4) | -0.1480 | down |  |
| 4 | 1 | assaying_molecularly_structural_plasticity_BDNF | Brain-Derived Neurotrophic Factor (BDNF) | -0.1110 | down | cross-community |
| 5 | 1 | il6_il6 | IL-6 (Interleukin-6) | -0.1110 | down |  |
| 6 | 1 | GABA_apoptosis_RhoA_ROCK | RhoA/ROCK Signalling Pathway | +0.1011 | up |  |
| 7 | 1 | GABA_apoptosis_caspase_cascade | Caspase Apoptotic Cascade (Caspase-3, -9, -12) | +0.1011 | up |  |
| 8 | 1 | GABA_apoptosis_PINK1_Parkin_mitophagy | PINK1/Parkin Mitophagy Pathway | -0.1011 | down |  |
| 9 | 1 | RhoA_ROCK_ROCK | ROCK (ROCK1/ROCK2) | +0.1003 | up | cross-community |
| 10 | 1 | hif1a_HIF1alpha | Hypoxia-Inducible Factor 1 Alpha (HIF1α) | +0.1003 | up | cross-community |

## 5. Perturbation & Drug Accounting

### initial_perturbations (7)

- GABA_apoptosis_ROS_oxidative_stress -> value 0.9000
- GABA_apoptosis_mitochondrial_dysfunction -> value 0.9200
- PNN_ECM_MMP9 -> value 0.7500
- TNF_TNF_alpha -> value 0.8500
- assaying_molecularly_structural_plasticity_BDNF -> value 0.8000
- il6_il6 -> value 0.8000
- tlr4_tlr4 -> value 0.9000

### sustained_drives (3)
- GABA_apoptosis_ROS_oxidative_stress: value 0.8500, window [0, 12)
- observed effect @ GABA_apoptosis_ROS_oxidative_stress: mean-in 0.9341 vs mean-out 0.6474 (delta +0.2868)
- GABA_apoptosis_mitochondrial_dysfunction: value 0.8800, window [0, 12)
- observed effect @ GABA_apoptosis_mitochondrial_dysfunction: mean-in 0.8450 vs mean-out 0.6475 (delta +0.1976)
- TNF_TNF_alpha: value 0.8000, window [0, 12)
- observed effect @ TNF_TNF_alpha: mean-in 0.8960 vs mean-out 0.8885 (delta +0.0075)

### drug_arms (0)
- none

## 6. Anomaly Flags

Rule-based flags:

- PINNED: Fumagillin (Ang-2 Inhibitor) (AngPt_fumagillin) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: CLP257 (KCC2 Enhancer) (BDNF_TrkB_CLP257) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Rapamycin (mTOR Inhibitor / Autophagy Enhancer) (GABA_apoptosis_Rapamycin) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: 846-861PE (NgR1 Antagonist Peptide) (NogoA_NgR1_846_861PE) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: SB-3CT (MMP Inhibitor) (PNN_ECM_SB3CT) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: TIMP-1 (Endogenous MMP Inhibitor) (PNN_ECM_TIMP1) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: C3 Exoenzyme (RhoA Inhibitor) (RhoA_ROCK_C3_exoenzyme) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Y-27632 (ROCK Inhibitor) (RhoA_ROCK_Y27632) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Fasudil (ROCK Inhibitor) (RhoA_ROCK_fasudil) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Simvastatin (RhoA Inhibitor) (RhoA_ROCK_simvastatin) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: XPro1595 (solTNF/TNFR1 Blocker) (TNF_XPro1595) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Bcl-xL (Dual-Functional Apoptosis/Autophagy Inhibitor) (autophagy-apoptosis_inhibition_Bcl_xL) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Ethosuximide (T-type channel blocker, repurposing) (cav32_ethosuximide) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Z944 (selective T-type blocker, Phase II) (cav32_z944) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: AMG487 (CXCR3 antagonist) (ccl21_amg487) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: TAT-Gap19 (Cx43 hemichannel blocker) (connexin43_tat_gap19) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: CX3CR1 Antagonists (analgesics) (cx3cl1_cx3cr1_amd3100_analog) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: AMD3100 / Plerixafor (CXCR4 antagonist, FDA-approved) (cxcl12_cxcr4_amd3100) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Atrasentan / ABT-627 (ETA-selective antagonist) (endothelin_atrasentan) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Bosentan (dual ETA/ETB antagonist, PAH-approved) (endothelin_bosentan) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: ACY-1083 / Tubastatin A (HDAC6 inhibitors) (hdac_acy1083) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: RGFP966 (HDAC3-selective inhibitor) (hdac_rgfp966) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Vorinostat/SAHA (pan-HDAC inhibitor) (hdac_vorinostat) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: PX-478 (HIF1α Inhibitor) (hif1a_PX478) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: YC-1 (HIF1α Inhibitor) (hif1a_YC1) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: 1400W (selective iNOS inhibitor) (inos_1400w) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: MCC950 (NLRP3 Inhibitor) (insights_nlrp3_mcc950) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Baricitinib (JAK1/2 Inhibitor, RA-Approved) (jakstat_baricitinib) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Ruxolitinib (JAK1/2 Inhibitor, FDA-Approved) (jakstat_ruxolitinib) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Cofilin-Modulating Peptides (Slingshot Phosphatase Inhibitor) (karilin7_CofilinModulatingPeptides) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: LIMK Inhibitors (Therapeutic Strategy) (karilin7_LIMK_Inhibitors) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: ARN23746 (next-gen KCC2 activator) (kcc2enhancers_arn23746) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Urolithin A (Mitophagy Enhancer for Pain) (microbio_urolithin_a) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: MCC950 / CRID3 (NLRP3 inhibitor) (nlrp3_mcc950) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: DAPT (γ-secretase inhibitor) (notch_dapt) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Rapamycin / Sirolimus (mTORC1 inhibitor) (pi3k_akt_mtor_rapamycin) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Selective PPARγ Modulators (SPPARγMs) (ppary_spppargms) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: KCC2 Enhancement Pillar (CLP257/AAV-KCC2) (proposal_chronic_pain_treatment_Kcc2Enhancement) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: ROCK Inhibition Pillar (Fasudil/AS1892802) (proposal_chronic_pain_treatment_RockInhibition) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: TNFR1-Selective TNF Blockade Pillar (XPro1595) (proposal_chronic_pain_treatment_Tnfr1SelectiveBlockade) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Azeliragon (TTP488, oral RAGE antagonist) (rage_azeliragon) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: FPS-ZM1 (brain-penetrant RAGE antagonist) (rage_fps_zm1) at 0.0000 for 100.00% of ticks (> 20%)
- PINNED: Aprepitant (NK1 antagonist, clinical failures) (substance_p_nk1_aprepitant) at 0.0000 for 100.00% of ticks (> 20%)

Unresolved key-label warnings:
- none

## 7. Reproducibility

- manifest.json sha256 (A): 131bb3d692f7519649a696e3fdfc88f7d161a05d1b4f358e8200112c0cedceba
- tick_log.jsonl sha256 (A): 7ec88d9691ee33c00e6ff57017fff9f969e95d21384f1e0489acf455e266ddf2
- states.csv sha256 (A): 3c94bfe926eee77fb5345ddf995c9ab9e51e1bddfc8bb026ec2d41e51e1a73c9
- manifest.json sha256 (B): d1d4a973a3fd4c8a4ac746e0f7c10600459c555941bb739f307772393583fcc0
- tick_log.jsonl sha256 (B): 87004f2ad00aeb5d106c6a888e2f04639b2f4eecf4ee2eeba692f53bfca3aeea
- states.csv sha256 (B): 0fe2b03eb4362818ba318ea13bec69854b2885dafaf5fcced28d21bcc5fd6f0c
- card_set_hash: a401244b561d1172edf5890609d3ac5f038a3837083ffd7c35ec7763613cee6c (cards manifest hash)
- determinism: rules-only engine runs are byte-reproducible (identical manifest.json / tick_log.jsonl / states.csv); the generation timestamp above and the embedded PNG plot are excluded from determinism claims (PNG bytes are not guaranteed reproducible).
- command: python3 -m simulator.reports.generate_report --run simulator/reports/runs/CIPN_28d --compare simulator/reports/runs/naive_28d --out simulator/reports/report_CIPN_vs_naive.md --plots-dir simulator/reports/plots

## 8. Comparison A vs B (cipn_28d vs naive_28d)

Common window: ticks 1..28 (28 ticks)

| readout | cipn_28d (A) | bar | naive_28d (B) | bar | delta (B-A) |
|---|---|---|---|---|---|
| pain_score | 0.2974 | [###.......] | 0.0500 | [..........] | -0.2474 |
| inflammation_index | 0.6107 | [######....] | 0.5000 | [#####.....] | -0.1107 |
| barrier_integrity | 0.3534 | [####......] | 0.5000 | [#####.....] | +0.1466 |
