# Hub agent card review digest

generated: 2026-10-30T15:45:33Z

Proposed normal roles are `<LLM_ENRICH>` placeholders unless the builder ran with --hub-enrich.

## BDNF_TrkB_KCC2 (KCC2 (Potassium-Chloride Cotransporter))

- tier: HUB | entity_type: channel | compartment: other | community: 8
- proposed_normal_role: <LLM_ENRICH>
- pathological rules (3):
  - `RULE-BDNF_TrkB_KCC2-01` [down] KCC2 (Potassium-Chloride Cotransporter) causes Mechanical Allodynia
    - claim_refs: (none)
  - `RULE-BDNF_TrkB_KCC2-02` [down] KCC2 (Potassium-Chloride Cotransporter) causes Central Sensitization
    - claim_refs: (none)
  - `RULE-BDNF_TrkB_KCC2-03` [up] KCC2 (Potassium-Chloride Cotransporter) supports inhibitory output of Parvalbumin (PV) Interneurons
    - claim_refs: (none)

## GABA_apoptosis_HIF1alpha (HIF1α (Hypoxia-Inducible Factor 1 Alpha))

- tier: HUB | entity_type: concept | compartment: other | community: 1
- proposed_normal_role: <LLM_ENRICH>
- pathological rules (5):
  - `RULE-GABA_apoptosis_HIF1alpha-01` [up] HIF1α (Hypoxia-Inducible Factor 1 Alpha) drives transcription of HIF1α Transcriptional Battery (Pain Genes)
    - claim_refs: EC-0039 (CONFIRMED)
  - `RULE-GABA_apoptosis_HIF1alpha-02` [up] HIF1α (Hypoxia-Inducible Factor 1 Alpha) transcribes Vascular Endothelial Growth Factor A (VEGFA)
    - claim_refs: EC-0041 (CONFIRMED)
  - `RULE-GABA_apoptosis_HIF1alpha-03` [down] HIF1α (Hypoxia-Inducible Factor 1 Alpha) destabilizes YC-1 (HIF1α Inhibitor)
    - claim_refs: EC-0038 (CONFIRMED)
  - `RULE-GABA_apoptosis_HIF1alpha-04` [down] HIF1α (Hypoxia-Inducible Factor 1 Alpha) inhibits translation of PX-478 (HIF1α Inhibitor)
    - claim_refs: EC-0040 (CONFIRMED)
  - `RULE-GABA_apoptosis_HIF1alpha-05` [up] HIF1α (Hypoxia-Inducible Factor 1 Alpha) transcribes Angiopoietin-2 (Ang-2)
    - claim_refs: EC-0149 (NO_EVIDENCE_FOUND)

## GABA_apoptosis_mTORC1 (mTORC1 (Mammalian Target of Rapamycin Complex 1))

- tier: HUB | entity_type: drug | compartment: other | community: 1
- proposed_normal_role: <LLM_ENRICH>
- pathological rules (2):
  - `RULE-GABA_apoptosis_mTORC1-01` [down] mTORC1 (Mammalian Target of Rapamycin Complex 1) inhibits Rapamycin (mTOR Inhibitor / Autophagy Enhancer)
    - claim_refs: EC-0137 (UNREVIEWED)
  - `RULE-GABA_apoptosis_mTORC1-02` [up] mTORC1 (Mammalian Target of Rapamycin Complex 1) rationale for Rationale: Double-Edged Sword of Autophagy Modulation
    - claim_refs: EC-0169 (UNREVIEWED)

## Skill_neuroscientific_insights_seeker_skill (Skill: In Vivo Multimodal Circuit Dissection & Closed-Loop Neuromodulation for Neuropathic Pain)

- tier: HUB | entity_type: concept | compartment: other | community: 1
- proposed_normal_role: <LLM_ENRICH>
- rule_gap_reason: all candidate rules refuted or none found
- pathological rules (0):
  - (none surviving verdict filtering)

## ana_12_NLRP3_inflammasome (NLRP3 Inflammasome)

- tier: HUB | entity_type: concept | compartment: other | community: 1
- proposed_normal_role: <LLM_ENRICH>
- rule_gap_reason: all candidate rules refuted or none found
- pathological rules (0):
  - (none surviving verdict filtering)

## assaying_molecularly_structural_plasticity_BDNF (Brain-Derived Neurotrophic Factor (BDNF))

- tier: HUB | entity_type: molecule | compartment: other | community: 1
- proposed_normal_role: <LLM_ENRICH>
- pathological rules (16):
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-01` [up] Brain-Derived Neurotrophic Factor (BDNF) rationale for Rationale: BDNF has both pro-nociceptive and anti-nociceptive roles
    - claim_refs: EC-0021 (CONFIRMED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-02` [up] Brain-Derived Neurotrophic Factor (BDNF) upregulates translation Kalirin-7 (GEF for Rac1/RhoG)
    - claim_refs: EC-0147 (NO_EVIDENCE_FOUND)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-03` [down] Brain-Derived Neurotrophic Factor (BDNF) disrupts via trkb kcc2 PV Inhibition KCC2-Dependency
    - claim_refs: EC-0017 (EXTENDED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-04` [up] Brain-Derived Neurotrophic Factor (BDNF) stimulates release of HIF1α-Driven Microglial Glycolytic Shift (M1)
    - claim_refs: EC-0024 (CONFIRMED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-05` [up] Brain-Derived Neurotrophic Factor (BDNF) stimulates microglial release of VEGFR2 (Flk-1/KDR)
    - claim_refs: EC-0023 (NO_EVIDENCE_FOUND)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-06` [up] Brain-Derived Neurotrophic Factor (BDNF) drives transcription of IL-6/gp130/JAK2 Axis
    - claim_refs: EC-0018 (CONFIRMED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-07` [up] Brain-Derived Neurotrophic Factor (BDNF) promotes via trkb Synaptic Plasticity Protein Biomarkers
    - claim_refs: EC-0020 (CONFIRMED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-08` [up] Brain-Derived Neurotrophic Factor (BDNF) enhances excitability of Somatostatin (SST) Interneurons
    - claim_refs: EC-0145 (NO_EVIDENCE_FOUND)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-09` [up] Brain-Derived Neurotrophic Factor (BDNF) activates TrkB.FL (Full-Length TrkB Receptor)
    - claim_refs: EC-0016 (CONFIRMED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-10` [down] Brain-Derived Neurotrophic Factor (BDNF) sequesters TrkB-Fc (BDNF Sequestering Chimera)
    - claim_refs: EC-0022 (CONFIRMED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-11` [up] Brain-Derived Neurotrophic Factor (BDNF) induces release of TNF-α (Pro-Inflammatory Cytokine)
    - claim_refs: EC-0019 (NO_EVIDENCE_FOUND)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-12` [up] Brain-Derived Neurotrophic Factor (BDNF) mediates microglial release of ROCK (ROCK1/ROCK2)
    - claim_refs: EC-0146 (EXTENDED)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-13` [down] Brain-Derived Neurotrophic Factor (BDNF) downregulates KCC2 (Potassium-Chloride Cotransporter)
    - claim_refs: (none)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-14` [up] Brain-Derived Neurotrophic Factor (BDNF) supports integrity via tight junctions Blood-Brain/Spinal Cord Barrier (BBB/BSCB)
    - claim_refs: (none)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-15` [up] Brain-Derived Neurotrophic Factor (BDNF) drives AC1 dependent synaptic enhancement ACC Presynaptic LTP (Kainate/AC1/HCN)
    - claim_refs: (none)
  - `RULE-assaying_molecularly_structural_plasticity_BDNF-16` [up] Brain-Derived Neurotrophic Factor (BDNF) drives Pain-Related Aversion (rACC)
    - claim_refs: (none)

## karilin7_Kalirin7 (Kalirin-7 (GEF for Rac1/RhoG))

- tier: HUB | entity_type: molecule | compartment: other | community: 5
- proposed_normal_role: <LLM_ENRICH>
- pathological rules (6):
  - `RULE-karilin7_Kalirin7-01` [up] Kalirin-7 (GEF for Rac1/RhoG) activates GEF Rac1 GTPase
    - claim_refs: EC-0052 (CONFIRMED)
  - `RULE-karilin7_Kalirin7-02` [up] Kalirin-7 (GEF for Rac1/RhoG) activates GEF RhoG GTPase
    - claim_refs: EC-0053 (CONFIRMED)
  - `RULE-karilin7_Kalirin7-03` [up] Kalirin-7 (GEF for Rac1/RhoG) initiates Rac1-PAK-LIMK-Cofilin Actin Remodelling Pathway
    - claim_refs: EC-0060 (CONFIRMED)
  - `RULE-karilin7_Kalirin7-04` [down] Kalirin-7 (GEF for Rac1/RhoG) genetic deletion Kalirin-7 Global Knockout Mouse
    - claim_refs: EC-0057 (CONFIRMED)
  - `RULE-karilin7_Kalirin7-05` [up] Kalirin-7 (GEF for Rac1/RhoG) rationale for Rac1–PAK–LIMK–cofilin pathway
    - claim_refs: EC-0067 (CONFIRMED)
  - `RULE-karilin7_Kalirin7-06` [up] Kalirin-7 (GEF for Rac1/RhoG) causes Spinal Pronociceptive Kalirin-7 Role
    - claim_refs: (none)

## rage_rage (RAGE (Receptor for Advanced Glycation End-products / AGER))

- tier: HUB | entity_type: receptor | compartment: other | community: 10
- proposed_normal_role: <LLM_ENRICH>
- rule_gap_reason: all candidate rules refuted or none found
- pathological rules (0):
  - (none surviving verdict filtering)

## tlr4_tlr4 (TLR4 (Toll-like Receptor 4))

- tier: HUB | entity_type: receptor | compartment: other | community: 0
- proposed_normal_role: <LLM_ENRICH>
- rule_gap_reason: all candidate rules refuted or none found
- pathological rules (0):
  - (none surviving verdict filtering)
