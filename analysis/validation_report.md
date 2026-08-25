# Claim Validation Report — Literature Round 2026-08

**Scope:** all 262 claim cards in `analysis/claims/claims.json` (169 edge claims EC-0001…EC-0169; 93 quantitative claims QC-0001…QC-0093), validated against the ten literature sweeps of 2026-08-25 (`analysis/literature/theme_01…10_*.md`), plus 4 targeted adjudication websearches on the highest-stakes contradictions. Full per-claim record: `analysis/claims/verdicts.json`.

## Executive Summary

| Verdict | Count | % of 262 |
|---|---|---|
| CONFIRMED | 86 | 32.8% |
| EXTENDED | 37 | 14.1% |
| REFUTED | 8 | 3.1% |
| MIXED | 6 | 2.3% |
| NO_EVIDENCE_FOUND | 56 | 21.4% |
| UNREVIEWED | 69 | 26.3% |

- **Priority coverage** (substantively reviewed = CONFIRMED/EXTENDED/REFUTED/MIXED):
  - **P0:** 88/138 reviewed (**63.8%**); 28 P0 claims untouched by any sweep finding, 22 P0 claims outside all ten themes.
  - **P1:** 9/31 reviewed (**29.0%**); 13 untouched, 9 out-of-theme.
  - All QC cards are P3; reviewed or explicitly flagged unverified.
- **Headline confirmations:** BDNF–TrkB→KCC2 cascade now human-tissue anchored (Davis 2025 human dorsal horn; Dedek 2019 *Brain*); MMP-9 hub reconfirmed end-to-end incl. phase structure (Kawasaki 2008 intact through 2025 reviews); Rbfox1–NrCAM splicing axis confirmed verbatim incl. the 72-h ASO figure; BRADiNP quotes verified word-for-word against Stemper et al., *Pain* 2025; P2X7 reaches a clinical-track antagonist (AK1780); lactylation–IGF2BP2 axis multiply replicated.
- **Headline refutations:** DRGX polarity fully inverted (EC-0031…0034, adjudicated vs Ito et al., *Mol Pain* 2020); ZFHX2 regulome mismatch (EC-0131, EC-0133 — regulome is SST/PTGIR/GFRA3/GAL, not Nav/TRPV1/CGRP/BDNF; Zfhx2-null mice heat-HYPERsensitive); Kalirin-7 injury-downregulation claims (EC-0058/EC-0059) inverted at spinal level where Kal7 gain-of-function is pronociceptive.

## Refuted or Inverted Claims (action required)

| Claim | Verdict | What literature shows | Suggested KB fix |
|---|---|---|---|
| EC-0031 | REFUTED | DRGX downregulated in small/medium DRG neurons after SNL; shRNA knockdown induces mechanical/thermal pain; overexpression suppresses maintenance-phase pain by restraining MMP-9 (EP2 not rescued). No DRGX→BDNF-TrkB-KCC2 link exists. | Invert polarity: `DRGX loss → derepresses MMP-9 → microglial activation → pain`; add peripheral arm `DRG-KCC2 ⊣ BDNF release` (Xian 2025) |
| EC-0032 | REFUTED | Sensitization rationale runs opposite: DRGX restoration alleviates; loss maintains sensitization. | Flip sign; retitle as protective TF post-development |
| EC-0033 | REFUTED | A DRGX-knockdown ASO would be predicted to worsen pain. | Replace knockdown therapy with restoration strategy (AAV overexpression) or delete |
| EC-0034 | REFUTED | No SCN9A/SCN10A/TRPV1 battery; only MMP-9 restraint demonstrated. | Corrected regulome: Mmp9 (rescued), Ptger2 (not rescued) |
| EC-0058 | REFUTED | CCI associates with Kalirin-7 recruitment/upregulation driving pronociceptive sensitization (Nat Commun 2015 + SGK1/SIRT1/T2D/fracture follow-ups). ACC-specific downregulation has no retrievable source. | Delete or demote to hypothesis; separate "general Kal7 biology (supported)" from "Kal7-in-ACC-pain (unsupported)" |
| EC-0059 | REFUTED | Same sign inversion for SNI-type injuries. | As above |
| EC-0131 | REFUTED | ZFHX2 ChIP-seq regulome excludes BDNF; Zfhx2-null mice are heat-hypersensitive (opposite of analgesic LOF). | Rebuild mechanism cards on SST↑/PTGIR↓/GFRA3↓/GAL↓; keep human R1913K genetics premise |
| EC-0133 | REFUTED | Claimed Nav1.7/Nav1.8/TRPV1/TRPA1/CGRP transactivation contradicted by published regulome. | Replace ion-channel battery with corrected neuropeptide-signalling gene set |

Related MIXED items requiring action (support + contradiction): **EC-0070** (re-scope cell type to lamina-I spinoparabrachial projection neurons; region-conditioned signs), **EC-0094** (invert NG101/Nogo-A direction; NISCI Ph2b primary endpoint missed — soften dossier), **EC-0106** (invert RhoA↔NgR1 direction; qualify NgR1 necessity to acute collapse only), **EC-0122/EC-0124** (time-window qualifier: pathogenic chronic vs adaptive early post-lesion), **EC-0168** (VEGFR2 valence contested; pronociception segregates to VEGFR1).

## Mixed / Contested Claims

| Claim | Conflict | Resolution guidance |
|---|---|---|
| EC-0070 | Tansley 2022: spinal PNN degradation → pain via projection-neuron GAG stripping, not PV interneurons; Mascio 2025: forebrain sign inversion (PNN build-up pronociceptive; chABC analgesic; MMP-9 KD lowers sham thresholds) | Region-conditioned edge signs; dominant early step is microglial phagocytic GAG stripping ± MMP-9; encode early-MMP-9/late-MMP-2 windows |
| EC-0094 | Mechanism intact (NG101 neutralizes Nogo-A) vs NISCI Phase 2b negative primary endpoint | Fix predicate direction; dossier language → "well tolerated; subgroup/post-hoc signals only" |
| EC-0106 | NgR1 required for acute growth-cone collapse but dispensable for chronic substrate-bound inhibition (PirB/NgR2 redundancy); card direction inverted | Invert direction; scope convergence claim to acute signaling |
| EC-0122 / EC-0124 | Strong support (human SDH tissue, rodent, dynamic allodynia) vs Cheung 2023 adaptive early-phase motor-circuit downregulation; Rivera context-dependence | Time-window + circuit qualifiers mandatory |
| EC-0168 | Inferred pronociceptive VEGFR2→KCC2 chain vs 2025 VEGFR2-neuroprotective organotypic-cord data (pronociception via VEGFR1) | Mark contested; consider receptor reassignment; context differs (chemo vs nerve-injury models) |

## Extended Claims (qualifiers to add)

| Claim | Qualifier to attach |
|---|---|
| EC-0013 | BSCB leaks transient (peak 24–48 h, often resolve ~d7–14); model-dependent; fix inverted predicate encoding |
| EC-0014 | Barrier-resealing is an instance of general resolution pharmacology; no approved resolvin drug |
| EC-0017 | Human-tissue anchored; peripheral DRG-KCC2 arm added; microglial P2X4-BDNF questioned, IRF5/P2X4 male-specific |
| EC-0042 | Pan-HIF1α inhibition harmful in ischemic/regenerative contexts (YC-1 stroke data; protective mitophagy/ferroptosis-suppression) |
| EC-0045 | IL-6/JAK2/STAT3 axis validated but terminal STAT3→KCC2 step unproven (NKCC1 phosphorylation documented instead) |
| EC-0047 / EC-0048 | JAKi analgesia extended to CSF-1 glial arm + neuronal cell-autonomous site; BBB penetration uncertain; predicates inverted |
| EC-0063 / EC-0066 | Pain-related anxiety real but attribution shifts from Kal7 to AC1/GluN2B/HCN pre-LTP circuits, ACC-VTA/LHb/BLA loops, P2X4R-BDNF |
| EC-0068 | Exercise/EE restores ACC synapses via unspecified mechanisms (NOT Kal7) — relabel mediator |
| EC-0073 | HIF1α↔MMP-9 is an axis/co-driver relation, not strict one-way induction |
| EC-0093 | Demonstrated direction is PNN-degradation→Ca²⁺-overload; annotate arrow direction |
| EC-0097 | Add firing-pattern-restoration readout (Qiu 2024 PNAS); RARα node is preprint-stage |
| EC-0099 | Disinhibition paradigm gains opioid-resistance dimension; KCC2 pipeline matured (AXN-027 FIH Q4 2024; OV350 H1 2025) |
| EC-0108 | LPA cascade gains satellite-glial/Schwann-cell peripheral arm; UD-039/UD-059Na, PIPE-791, oxypeucedanin new handles |
| EC-0110 | ROCK inhibition pro-regenerative instances widen context-dependence framing |
| EC-0117 | XPro1595 efficacy sex-dependent (males>females, estrogen-blunted); late SCI dosing failed; MINDFuL Ph2 = AD not pain; predicate phrasing inverted |
| EC-0120 | Mark synthetic/proposal-level; DMF-prevention and Denk-2013 schedule dependence give indirect conceptual support only |
| EC-0127 | Anti-TNF double hazard expanded: demyelination + impaired acute-to-chronic resolution (TNFR2 pro-resolving arm) |
| EC-0129 | Soften to neuroma-associated neovascularization unless causal VEGF-neuroma study attached |
| EC-0130 | Reframe duality via SRPK1 isoform splicing (Axxxa/xxxb) and VEGFR1-vs-VEGFR2 axes |
| EC-0146 | Recast garbled predicate as BDNF-linked microglial RhoA/ROCK activation |
| EC-0159 | Still INFERRED — no head-to-head SPM-vs-Ang-1 comparison exists |
| EC-0167 | Network-level cytokine→ACC plasticity supported; direct spine-morphology endpoint unverified |
| QC-0002 | B1R sign flips with disease stage (protective early diabetes / pronociceptive established disease) |
| QC-0008 | CB2 bench-bedside gap flag (inconsistent human trials; CNTX-6016 still Phase I) |
| QC-0012 / QC-0013 | CSF1R depletion efficacy sex-dimorphic (male>female; female mitochondrial-survival compensation); pexidartinib hepatotoxicity constraint |
| QC-0039 / QC-0040 / QC-0042 | KCC2-enhancer cards need MOA caveat (CLP257 indirect/clustering debate) and primary-source checks for ARN23746/lead figures |
| QC-0048 | TZD class safety caveats (rosiglitazone CV signal; fluid retention) |
| QC-0071 | H3K18la mark is model- and locus-specific (robust in CCI DRG; unchanged in SNL where H4K8la rose) |
| QC-0082 / QC-0083 | TREM2/LAMP1 phagocytosis-checkpoint angle makes claims actionable; CX3CR1 dependence contested |
| QC-0086 / QC-0087 | Extend into senescence/mitophagy frame; promote urolithin A to node; verify sources |

## Confirmed Core Claims

Grouped by pathway area:

- **Spinal disinhibition / KCC2:** EC-0005, EC-0027, EC-0035, EC-0095, EC-0098, EC-0111 (EC-0017, EC-0122, EC-0124 confirmed-with-qualifiers); QC-0038, QC-0057-family TRPV1 anchors, QC-0070. Landmarks Coull 2003/2005, Rivera 2002/2004, Duan 2014, Petitjean 2015 reconfirmed.
- **MMP-9 / PNN / ECM:** EC-0071, EC-0072, EC-0074, EC-0093, EC-0151. Kawasaki 2008 phase framework intact; Tansley 2022 confirmed (cell type refined); AZD1236-class dual MMP-9/12 inhibition new windowed target.
- **Neuroinflammation:** EC-0079, EC-0083; QC-0047, QC-0056, QC-0084, QC-0085. TNFR1/TNFR2 dichotomy supported; AK1780 brings P2X7 to clinical threshold.
- **HIF1α / metabolism / barriers:** EC-0011, EC-0012, EC-0015, EC-0024, EC-0038, EC-0039, EC-0040, EC-0041, EC-0044-adjacent lactylation replication. Glycolytic-shift hub validated with upstream PRMT6/Lyn-IRF5/HK2/FGF4 nodes.
- **NgR1 / RhoA:** EC-0030, EC-0069, EC-0100, EC-0102, EC-0107, EC-0113; QC-0050, QC-0051. Fasudil/ripasudil base widened; LPA-SGC peripheral arm added.
- **DRG excitability / splicing:** EC-0001, EC-0003, EC-0140 (ANA-12 tool validity), EC-0103, EC-0104, EC-0105, EC-0088; QC-0066, QC-0067, QC-0088, QC-0091. Suzetrigine Phase 3 supports Nav1.8 framing (with ceiling caveat).
- **CGRP / bradykinin / prostaglandins:** QC-0001, QC-0003, QC-0004, QC-0005, QC-0006 (BRADiNP verified verbatim — negative result itself confirmed), QC-0058–QC-0061, QC-0089, QC-0090.
- **Resolution / SPM / HO-1 / CB2 / S1P:** EC-0014 (with qualifier), EC-0159-adjacent family breadth; QC-0036, QC-0048, QC-0049, QC-0052, QC-0008. New bridge: RvD1 ⊣ microglial BDNF/TrkB (Eur J Med Res 2025).
- **Epigenetics / JAK-STAT:** EC-0018, EC-0047, EC-0048, EC-0114, EC-0152, EC-0155; QC-0071, QC-0090. Tsuda 2011 STAT3-glia landmark reconfirmed; HDAC4→GAD65 repression confirmed (panobinostat).
- **Kalirin-7 general biology / ACC plasticity canon:** EC-0052, EC-0053, EC-0057, EC-0060, EC-0062, EC-0065, EC-0067, EC-0101, EC-0121, EC-0123, EC-0125, EC-0016, EC-0020, EC-0021, EC-0022. Bliss/Collingridge/Koga ACC-LTP canon fully reconfirmed — molecular substrate there is AC1/GluN2B/HCN/PKMζ, **not** Kalirin-7.

## Unverified High-Priority Items (P0/P1 with no evidence found)

41 P0/P1 claims were touched by no sweep finding:

- **ACC Kalirin-7 narrative cluster (demote to hypothesis nodes):** EC-0054 (AAV-Kal7 rescue), EC-0055, EC-0056, EC-0061, EC-0064 (DBS), EC-0147 (BDNF→Kal7 translation), EC-0157, EC-0160, EC-0161, EC-0162, EC-0163 (antagonism edges), QC-0081 (time-course). Adjudication search found **TIAM1** (JCI 2022;132:e158545) as the evidenced ACC Rac1-GEF instead.
- **Encoding anomalies (fix, don't delete):** EC-0023, EC-0026, EC-0084 (implausible/inverted edges), EC-0118, EC-0119 (reversed subject-object), EC-0049, EC-0112 (inverted directions).
- **Untested sub-edges within swept areas:** EC-0002 (ANA-12→NLRP3 specifically), EC-0004, EC-0126 (TrkB.T1 interactions), EC-0019 (BDNF→TNF release; P2X4-BDNF controversy adjacent), EC-0025 (CP-AMPAR excitotoxicity — theme internally inconsistent), EC-0044 (possible IGF2/IGF2BP2 entity conflation), EC-0050, EC-0051 (KALRN upstream transcription edges), EC-0076, EC-0109 (simvastatin), EC-0118/EC-0119 (see above), EC-0128, EC-0132, EC-0134 (ZFHX2 injury/ASO absence), EC-0145, EC-0149, EC-0150 (Ang-2 chain — mark speculative), EC-0153 (NrCAM-NgR1 ambiguous), EC-0154, EC-0156 (inherits EC-0070 problem), EC-0166.

## Systemic Observations

1. **Male-only / male-biased evidence base.** STEP61–pFyn–pGluN2B is male-specific across rodent+human; IRF5/P2X4 microglial pathway is male-only; XPro1595 efficacy male-biased (estrogen blunts response, ovariectomy restores); CSF1R-depletion efficacy male>female; Tansley 2022 (PNN) a notable both-sexes exception. Sex annotations should ride every microglial and TNF-axis edge.
2. **Model-dependence is the rule.** NLRP3 null in SNI vs positive in CCI/DNP/cancer/EAE; BSCB leak magnitude/transience varies by model; KCC2 downregulation flips valence with phase and circuit (chronic DH pathogenic vs early motor adaptive); CX3CL1 fragment-dependent duality; PNN effects reverse between spinal lamina I (protective nets) and forebrain (pronociceptive build-up). Edges need model/phase properties, not static signs.
3. **Clinical-translation gaps concentrate in single-target chronic-pain programs.** Negative this round: fulmetibant BRADiNP (B1R/DNP), eliapixant PUCCINI (cited therein), ABT-639 (T-type/PDN), opicinumab ×3 (LINGO-1), NISCI (anti-Nogo-A primary endpoint). Partial ceilings: suzetrigine (not superior to hydrocodone/APAP), ACD440 (n=14, thermal only). Repurposed/approved-drug routes (DMF, baricitinib, pioglitazone, fasudil lineage, AXN-027/OV350 KCC2 pipeline) show the most momentum.
4. **Predicate-direction defects are systematic in drug-target / ligand-receptor cards.** At least 13 cards write target→drug or receptor→ligand: EC-0013, EC-0022, EC-0023, EC-0026, EC-0038, EC-0040, EC-0094, EC-0100, EC-0106, EC-0117, EC-0118, EC-0119, EC-0123 (+ garbled EC-0146). Underlying biology mostly survives; encodings don't — a one-pass normalization (drug inhibits target) is cheap and high-value.
5. **Entity-conflation risk.** IGF2 (ligand) vs IGF2BP2 (m6A reader) appear conflated around EC-0044. The sweep briefs themselves contained citation confluations worth auditing in dossiers: "Kawaji 2005" → actually Kawasaki 2008 Nat Med; "Dityatev 2010 chABC-allodynia" not found (nearest Dityatev 2007 culture work); "Tatsumi 2015 NgR1" actually Tatsumi 2015 Glia (microglial RhoA/ROCK); "Xie 2017 RhoA/ROCK" unidentifiable (nearest Xie 2016 AMD3100); "Uchida/Zhang STAT3" actually Tsuda 2011 Brain.
6. **Internal sweep inconsistency to note:** theme_01 F1.6 maps EC-0025 → SUPPORTS while its own Limitations section says CP-AMPAR-mediated PV excitotoxic death was "not directly probed/resurfaced". Verdict recorded as NO_EVIDENCE_FOUND pending reconciliation.
7. **Free wins — strongest cross-theme bridges for graph expansion:** DRGX↓→MMP-9 derepression (Theme 6↔2); nociceptor-localized KCC2 ⊣ BDNF release (Theme 1 peripheral arm, human avulsion concordant); RvD1 ⊣ microglial BDNF/TrkB (Theme 8↔1); ELF1→MMP-9 upstream initiator; ORL1→NgR1 maturation; neutrophil-elastase→Ang-1 degradation (sivelestat); TREM2/LAMP1 phagocytosis checkpoints; senolytics/SASP layer; circulating miRNA diagnostic panel.

## Method

- **Sweeps used:** ten theme files dated 2026-08-25 (`theme_01…10_*.md`), ~100 logged web queries across them, each mapping findings to claim IDs with SUPPORTS / CONTRADICTS / EXTENDS / NEW_MECHANISM / NOVEL_TARGET classes.
- **Verdict rules applied:** CONFIRMED = ≥1 SUPPORTS, no contradiction; EXTENDED = SUPPORTS + scope/timing/mechanism refinement (qualifier recorded); REFUTED = ≥1 CONTRADICTS and no adequate support; MIXED = both present; NO_EVIDENCE_FOUND = claim's thematic area swept but no finding touched it (or targeted search explicitly found nothing); UNREVIEWED = topic outside all ten themes. Conflicts weighed primary research > reviews > preprints.
- **Adjudication searches used:** 4 of 6 allotted. (1) DRGX direction → confirmed polarity inversion via Ito et al., *Mol Pain* 2020;16:33 (PMC7099666). (2) Kalirin-7 ACC narrative → no ACC-Kal7-pain study exists; TIAM1 identified as evidenced ACC Rac1-GEF (Ru et al., *J Clin Invest* 2022;132:e158545). (3) MMP-9→PNN→PV → Tansley et al., *Science* 2022;377:80 confirms lamina-I PNNs enwrap spinoparabrachial projection neurons (not PV), both sexes; Mascio et al., *Pain* 2025 confirms forebrain sign inversion. (4) Fulmetibant BRADiNP → Stemper et al., *Pain* 2025 (PMID 40334047; NCT05219812): treatment difference 0.07 (95% CI −0.170–0.314), negative; QC quotes verbatim.
- **Limitations:** sweeps rest on abstract/snippet-level evidence with some paywalled sources; several key items are preprints (RARα bioRxiv 2022, Nex-TNFR2 bioRxiv 2025, claudin-12 bioRxiv 2019, Davis 2025 bioRxiv/journal-in-press, N02C0702 2026) — flagged in qualifiers; search-engine recency skew means mid-2026 coverage is incomplete; negative findings are query-relative ("no retrievable source" ≠ proof of nonexistence) so ACC-Kal7 and ZFHX2 deletions should be preceded by one targeted PubMed check; KCC2-enhancer named compounds (ARN23746, STAB-1, BUM-9082) and FX11/AZD3965 figures remain unsourced and were graded NO_EVIDENCE_FOUND rather than accepted.
- **Provenance:** verdicts applied to dossiers (24 files) and graph edges (138 links annotated with `validation_status`) in commits `f681780`–`b37eda6`; original confidence/sign/relation fields preserved untouched.
