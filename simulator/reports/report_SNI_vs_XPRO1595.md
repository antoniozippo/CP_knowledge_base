# CP Simulator Experiment Report



## 1. Run Overview

- run_dir: simulator/reports/runs/SNI_28d
- scenario: sni_28d
- injury_model: SNI
- injury_tick: 0
- horizon_days: 28
- seed: 0
- engine_version: 0.1.0
- started_at_utc: 2026-08-26T13:27:11Z
- generated_at: 2026-08-26T13:29:35Z
- llm_calls_made: 0
- llm_calls_deferred: 0
- notes: SNI pilot scenario. Seeds are proximal injury drivers resolved against the real card set: microglial activation, TNF-alpha, ROS/oxidative stress, MMP-9, BDNF, HIF1-alpha. No DAMP card exists in the set; its canonical receptor TLR4 (tlr4_tlr4) is seeded as the DAMP-signaling proxy. Seed magnitude 0.92: orphan nodes contract toward baseline by a factor of ~0.637 per tick, so only seeds >= ~0.87 satisfy first_crossing with delta=0.15 and sustain=2 for two consecutive logged ticks. Sustained drives model tonic injury drivers after SNI: ongoing ectopic afferent firing and persistent glial activation keep microglia and TNF-a elevated through the whole horizon (value 0.9 from tick 0, no end tick = active while start <= tick < horizon).

## 2. Readout Trajectories

![readout trajectories](plots/SNI_28d_readouts.png)

| day | pain_score | inflammation_index | barrier_integrity |
|---|---|---|---|
| 2 | 0.1822 | 0.5827 | 0.4292 |
| 4 | 0.2931 | 0.5975 | 0.3805 |
| 6 | 0.3368 | 0.6063 | 0.3503 |
| 8 | 0.3457 | 0.6131 | 0.3358 |
| 10 | 0.3461 | 0.6187 | 0.3306 |
| 12 | 0.3465 | 0.6233 | 0.3291 |
| 14 | 0.3467 | 0.6273 | 0.3282 |
| 16 | 0.3469 | 0.6305 | 0.3269 |
| 18 | 0.3473 | 0.6332 | 0.3251 |
| 20 | 0.3478 | 0.6353 | 0.3232 |
| 22 | 0.3483 | 0.6370 | 0.3215 |
| 24 | 0.3488 | 0.6383 | 0.3200 |
| 26 | 0.3493 | 0.6394 | 0.3188 |
| 28 | 0.3497 | 0.6403 | 0.3178 |

## 3. Key Entity Traces

### CSF1-CSF1R_SpinalMicroglia — Spinal Microglia (Activated) (key: microglia)

state ▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.7725 vs baseline 0.5000 -> delta +0.2725

### GABA_apoptosis_TNF_alpha — TNF-α (Pro-Inflammatory Cytokine) (key: TNF)

state ▅▅▆▆▆▆▆▆▆▆▆▆▆▆▇▇▇▇▇▇▇▇▇▇▇▇▇▇
final 0.8452 vs baseline 0.5000 -> delta +0.3452

### BDNF_TrkB_proBDNF — proBDNF (key: BDNF)

state ▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅▅
final 0.5000 vs baseline 0.5000 -> delta +0.0000

### BBB_CypA_MMP9_pathway — CypA-MMP-9 Pathway (key: MMP-9)

state ▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.7370 vs baseline 0.5000 -> delta +0.2370

### BDNF_TrkB_CLP257 — CLP257 (KCC2 Enhancer) (key: KCC2)

state ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
final 0.0000 vs baseline 0.0000 -> delta +0.0000

### GABA_apoptosis_PNN_loss — Perineuronal Net (PNN) Loss and GABAergic Hyperactivity (key: perineuronal)

state ▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.7418 vs baseline 0.5000 -> delta +0.2418

### PV_interneurons_PV_interneurons — Parvalbumin (PV) Interneurons (key: parvalbumin)

state ▄▃▃▂▂▂▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
final 0.0270 vs baseline 0.5000 -> delta -0.4730

### shared_mechanical_allodynia — Mechanical Allodynia (key: allodynia)

state ▂▃▄▄▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆
final 0.6967 vs baseline 0.0500 -> delta +0.6467


## 4. Emergent Events

Top single-tick state changes (pre-tick 0 reconstructed from card baselines and scenario initial_perturbations):

| rank | day | agent | label | delta | direction | propagation |
|---|---|---|---|---|---|---|
| 1 | 1 | GABA_apoptosis_ROS_oxidative_stress | Reactive Oxygen Species (ROS) and Oxidative Stress | -0.1554 | down |  |
| 2 | 1 | tlr4_tlr4 | TLR4 (Toll-like Receptor 4) | -0.1554 | down |  |
| 3 | 1 | RhoA_ROCK_ROCK | ROCK (ROCK1/ROCK2) | +0.1480 | up | cross-community |
| 4 | 2 | shared_mechanical_allodynia | Mechanical Allodynia | +0.1241 | up | cross-community |
| 5 | 1 | BDNF_TrkB_KCC2 | KCC2 (Potassium-Chloride Cotransporter) | -0.1111 | down | cross-community |
| 6 | 1 | shared_mechanical_allodynia | Mechanical Allodynia | +0.1111 | up | cross-community |
| 7 | 1 | SST_somatostatin_interneurons | Somatostatin (SST) Interneurons | +0.1111 | up | cross-community |
| 8 | 1 | vegf_VEGFA | Vascular Endothelial Growth Factor A (VEGFA) | +0.1111 | up | cross-community |
| 9 | 3 | shared_mechanical_allodynia | Mechanical Allodynia | +0.1106 | up | cross-community |
| 10 | 2 | vegf_VEGFA | Vascular Endothelial Growth Factor A (VEGFA) | +0.1072 | up | cross-community |

## 5. Perturbation & Drug Accounting

### initial_perturbations (7)

- GABA_apoptosis_ROS_oxidative_stress -> value 0.9200
- PNN_ECM_MMP9 -> value 0.9200
- TNF_TNF_alpha -> value 0.9200
- assaying_molecularly_structural_plasticity_BDNF -> value 0.9200
- hif1a_HIF1alpha -> value 0.9200
- shared_microglia -> value 0.9200
- tlr4_tlr4 -> value 0.9200

### sustained_drives (2)
- TNF_TNF_alpha: value 0.9000, window [0, 28)
- observed effect @ TNF_TNF_alpha: mean-in 0.9676 vs mean-out n/a
- shared_microglia: value 0.9000, window [0, 28)
- observed effect @ shared_microglia: mean-in 0.9575 vs mean-out n/a

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
- PINNED: NSC23766 (Rac1 Inhibitor, ACC Microinjection) (karilin7_NSC23766) at 0.0000 for 21.43% of ticks (> 20%)
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

- manifest.json sha256 (A): 31558785eef2410f79466f2673265bd24c9f77079432b2841212d77ab097b3cb
- tick_log.jsonl sha256 (A): 40f233d862b42fb1766655d93d94c2c57539dfd37b763df9a6c9c8f8299524ab
- states.csv sha256 (A): 26ebd6f9dae2857cfb2d692a9ff6437981fb09690c2eaa21b452492961edd65f
- manifest.json sha256 (B): dbdd78cf4bdff6938ee1859bbf2f30ad09b516c7c18c34c81946a1099d84686e
- tick_log.jsonl sha256 (B): 184a67ed273ebb086b6eaa168eb62c768c8408bac9b652e6bd91e9a76b529ae3
- states.csv sha256 (B): 5c148e07db5182c88e67f36048f2e35f14a2750e54e02c10a928d2d64ec79a7b
- card_set_hash: a401244b561d1172edf5890609d3ac5f038a3837083ffd7c35ec7763613cee6c (cards manifest hash)
- determinism: rules-only engine runs are byte-reproducible (identical manifest.json / tick_log.jsonl / states.csv); the generation timestamp above and the embedded PNG plot are excluded from determinism claims (PNG bytes are not guaranteed reproducible).
- command: python3 -m simulator.reports.generate_report --run simulator/reports/runs/SNI_28d --compare simulator/reports/runs/SNI_28d_XPRO1595 --out simulator/reports/report_SNI_vs_XPRO1595.md --plots-dir simulator/reports/plots

## 8. Comparison A vs B (sni_28d vs sni_28d_xpro1595)

Common window: ticks 1..28 (28 ticks)

| readout | sni_28d (A) | bar | sni_28d_xpro1595 (B) | bar | delta (B-A) |
|---|---|---|---|---|---|
| pain_score | 0.3260 | [###.......] | 0.3064 | [###.......] | -0.0196 |
| inflammation_index | 0.6216 | [######....] | 0.5977 | [######....] | -0.0239 |
| barrier_integrity | 0.3412 | [###.......] | 0.3604 | [####......] | +0.0192 |
