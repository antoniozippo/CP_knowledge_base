# Theme 7: CGRP / Bradykinin-KKS / Prostaglandins / Substance P-NK1
_Sweep date: 2026-08-25 · Scope: 2021-2026 + landmark classics_

## Search Log
| # | Query | Period | Key hits |
|---|-------|--------|----------|
| 1 | "CGRP monoclonal antibody neuropathic pain beyond migraine clinical trials" | 2022-2026 | Russo & Kaiser 2026 Annu Rev Med (beyond-migraine chapter); open-label CM + comorbid peripheral neuropathy study; SAFE-CGRP real-world safety (Front Neurol 2025); ligand-vs-receptor mAb divergence (J Headache Pain 2026) |
| 2 | "gepants non-migraine pain indications rimegepant atogepant neuropathic pain osteoarthritis trials" | 2019-2026 | Wells-Gatnik 2024 Expert Rev Neurother; Efficacy/safety of gepants review (JOFPH 2026); PROGRESS/ADVANCE/ELEVATE (migraine-only); no non-headache gepant pain trials found |
| 3 | "bradykinin B1 B2 receptor antagonist chemotherapy-induced peripheral neuropathy fulmetibant icatibant trial" | 2021-2026 | Becker 2023 Pharmaceutics 15:852 (cisplatin CINP, DALBK+icatibant); Becker 2023 Pharmaceuticals 16:959 (B2R→TRPA1); **BRADiNP fulmetibant Ph2a (Stemper, Pain 2025)**; Sci Rep 2023 breast-cancer/AI pain |
| 4 | "kallikrein-kinin system neuropathic pain B1 receptor diabetic neuropathy review" | 2023-2024 | Human DRG BK-receptor mapping (Pain 2024); Frontiers Med 2025 diabetic-complication signaling review (stage-dependent B1R role); Sci Rep 2023 |
| 5 | "prostaglandin E2 EP4 receptor blockade mechanical allodynia neuropathic pain" | 2022-2026 + classics | Nat Commun 2023 docking-derived EP4 antagonists (anti-allodynic, carrageenan/CFA); **Nat Commun 2025 Schwann-cell EP2 (EP4 attribution challenged)**; EP3→CCL2→CCR2 SNI study; EP1 ONO-8711 CCI classic; PGE2 axonal EP4→ANO1/Nav1.8 (2024) |
| 6 | "substance P NK1 receptor antagonist chronic pain reappraisal why failed clinical trials" | 2000-2025 | Postoperative-pain meta-analysis (2025, 13 RCTs n=1959, positive 2 h/24 h); "Drug effects on neuropeptides" review 2024 (all NK1-RAs failed Ph II/III; hemokinin-1 hypothesis; no new pain trials); Revisiting SP in migraine (J Headache Pain 2025); Hill 2000 TIPS classic |
| 7 | Landmarks: CGRP sensitization (Iyengar/Edvinsson lineage); icatibant safety basis | 1993-2026 | Zhang/Russo J Neurosci 2007 (RAMP1 rate-limiting); Russo Annu Rev Pharmacol Toxicol 2015; Ho-Edvinsson-Goadsby Nat Rev Neurol 2010; icatibant FAST-1/2 NEJM 2010; Icatibant Outcome Survey (Allergy 2016; Clin Exp Allergy 2022; completion 2026) |

## Claims Inventory Note (filter result)
Keyword filter (`cgrp, bradykinin, kallikrein, prostaglandin, cox, pge2, substance p, nk1, calcitonin, icatibant`) over `analysis/claims/claims.json` (262 claims) yields **9 true claims**:
- **Bradykinin**: QC-0001, QC-0002, QC-0003, QC-0004, QC-0005, QC-0006 (all from `Bradykinin.md`)
- **Prostaglandins**: QC-0049 (15d-PGJ₂/PPARγ, from `PPARy.md`), QC-0089 (EP1⁺ cells ≈80% ED1⁺ macrophages, from `prostaglandins.md`), QC-0090 (ketorolac reverses PSNL allodynia >5 days, from `prostaglandins.md`)
- Two naive substring matches ("nk1" inside *PINK1*: EC-0080, EC-0096) were rejected as false positives.
- **Coverage gap:** dossiers `cgrp.md`, `Substance_P-NK1.md`, `calcitonin`-related notes exist in the vault root but contributed **zero** claims to the inventory. Theme-7 validation for those axes therefore runs at dossier level (below).

## Findings vs Existing Claims

### F7.1: Anti-CGRP mAbs in neuropathic pain — explored, but only open-label evidence
- **Evidence:** Annual Review of Medicine chapter states preclinical implication of CGRP in peripheral neuropathy, CRPS and painful neuromas, and that a small **open-label** study of chronic-migraine patients with comorbid peripheral neuropathy reported decreased neuropathic pain scores on CGRP mAbs — explicitly calling for larger placebo-controlled studies [<Russo & Kaiser 2026, Annu Rev Med, https://www.annualreviews.org/content/journals/10.1146/annurev-med-050224-111631>]
- **Relation to KB:** `cgrp.md` closing claim ("anti-CGRP mAbs and gepants … actively explored for other chronic pain conditions including neuropathic pain, with emerging efficacy signals") → **EXTENDS** (exploration confirmed; efficacy-signal wording must be qualified as open-label only, no RCT in non-headache pain to date)

### F7.2: Gepants remain migraine-confined; expansion pipeline is headache/perinatal, not neuropathic
- **Evidence:** Structured review of rimegepant/atogepant lists future innovation areas as pediatrics, pregnancy/breastfeeding, cluster headache and post-traumatic headache — no non-headache pain program [<Wells-Gatnik 2024, Expert Rev Neurother 24(11), https://www.tandfonline.com/doi/abs/10.1080/14737175.2024.2401558>; gepant class review JOFPH 2026, https://www.jofph.com/articles/10.22514/jofph.2026.046]
- **Relation to KB:** `cgrp.md` implies gepants are being explored across chronic pain conditions → **CONTRADICTS** (partial: gepant development beyond migraine is currently restricted to other *headache* disorders and special populations; no neuropathic-pain gepant trial identified 2019-2026)

### F7.3: Ligand vs receptor anti-CGRP mAbs diverge mechanistically (class-switch rationale)
- **Evidence:** Two independent migraine cohorts show erenumab (receptor mAb) did not normalize trigeminal sensory thresholds whereas galcanezumab (ligand mAb) previously did; up to 30% of non-responders to one class respond after switching [<J Headache Pain 2026, https://link.springer.com/article/10.1186/s10194-026-02316-z>; Van Veelen 2025 Eur J Neurol 32:e16542]
- **Relation to KB:** no claim IDs (cgrp gap) → **NEW_MECHANISM** (candidate distinction node: anti-CGRP-ligand vs anti-CGRP-receptor antibodies; possible amylin-1-receptor spillover for ligand mAbs)

### F7.4: Real-world CGRP-mAb safety in comorbidity populations excluded from trials
- **Evidence:** SAFE-CGRP retrospective multicenter study (n=353 with ≥1 trial-excluded comorbidity; mean 12.7 months): no serious adverse events attributable to treatment; 14 possible treatment-related worsenings (incl. 1 hereditary angioedema case, 7 Raynaud's) all reversible on discontinuation [<Front Neurol 2025, https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2025.1703876/full>]
- **Relation to KB:** `cgrp.md` therapeutic-window framing → **SUPPORTS** (favorable tolerability extends to vulnerable populations; flags Raynaud/HAE as watch-items consistent with CGRP vasodilatory physiology)

### F7.5: Kinin B1+B2 blockade in cisplatin CIPN — mechanical allodynia responsive, cold allodynia resistant
- **Evidence:** DALBK (B1) and icatibant (B2) each reduced established cisplatin-induced mechanical allodynia (~52% and ~57% at 2 h); non-peptide SSR240612/FR173657 similar; antisense knockdown confirmed (B1 −57%, B2 −33%); **peptide and non-peptide antagonists failed against cold sensitivity** [<Becker et al. 2023, Pharmaceutics 15:852, https://doi.org/10.3390/pharmaceutics15030852>]
- **Relation to KB:** QC-0001, QC-0003 → **SUPPORTS** (B1-selective antagonist reduces established mechanical allodynia days-to-weeks post-lesion); `Bradykinin.md` blanket statement that B1/B2 blockade also attenuates *cold* allodynia → **CONTRADICTS** (boundary condition: in this CIPN model cold hypersensitivity was kinin-blockade-resistant)

### F7.6: B2R→PLC/PKCε→TRPA1 cascade in cisplatin neuropathy
- **Evidence:** Bradykinin potentiated mechanical/cold nociception in cisplatin-treated mice; icatibant blocked potentiation (44%/64% inhibition); PLC and PKCε inhibitors abrogated the interaction; A967079 (TRPA1) strongly antiallodynic [<Becker et al. 2023, Pharmaceuticals 16:959, https://doi.org/10.3390/ph16070959>]
- **Relation to KB:** `Bradykinin.md` §"TRPA1 sensitisation" (B2R-mediated TRPA1 sensitisation via PLC/PKCε in cisplatin neuropathy) → **SUPPORTS**; same pathway replicated in aromatase-inhibitor pain [<Pharmaceutics 15:1136, https://mdpi-res.com/d_attachment/pharmaceutics/pharmaceutics-15-01136/article_deploy/pharmaceutics-15-01136.pdf>] → **EXTENDS**

### F7.7: BRADiNP — fulmetibant B1 antagonism fails Phase 2a in painful diabetic neuropathy
- **Evidence:** Randomized, double-blind, placebo-controlled 2-period crossover (n=158 treated, 75 completers both periods); primary endpoint change in weekly mean 24-h average pain NRS at week 4: treatment difference **0.07 (95% CI −0.170 to 0.314)** — negative; AEs mild/moderate in 51.3% [<Stemper et al. 2025, Pain, https://doi.org/10.1097/j.pain.0000000000003642; NCT05219812>]. Authors' conclusion: "preclinical efficacy seen with this bradykinin 1 receptor antagonist did not translate."
- **Relation to KB:** QC-0004, QC-0005, QC-0006 → **SUPPORTS** (design, endpoint and AE-rate quotes verified verbatim against the published paper; citation_status can move UNVERIFIED→VERIFIED). `Bradykinin.md` headline ("fulmetibant failed despite robust preclinical data") → **SUPPORTS**. Companion negative DNP trial of eliapixant (PUCCINI, Pain 2023) cited therein reinforces the translation-failure pattern [https://doi.org/10.1097/j.pain.0000000000003085]

### F7.8: Human DRG bradykinin receptor map — conserved acute excitation, bidirectional chronic effect
- **Evidence:** Organ-donor hDRG: B2R expressed by neurons (enriched in nociceptors) and satellite glia, B1R to lesser extent; acute BK increases human sensory-neuron excitability (conserved from rodents) while **prolonged exposure decreases excitability in a subpopulation**; pain history and age trend toward higher B1R expression [<Pain 2024, https://journals.lww.com/pain/fulltext/2024/01000/bradykinin_receptor_expression_and.18.aspx>]
- **Relation to KB:** `Bradykinin.md` §DRG distribution (human donor data, B2-enriched nociceptors, B1 predictors) → **SUPPORTS**; bidirectional time-dependence of BK action → **EXTENDS** (new qualifier: sustained kinin exposure is not uniformly pronociceptive even peripherally)

### F7.9: Stage-dependent (protective→pronociceptive) B1R biology in diabetes
- **Evidence:** Diabetic-complication signaling review: absence of B1R at DM onset worsens neuropathy (endogenous neuroprotection), whereas B1R antagonism 4 weeks after onset reduces oxidative stress and restores neuronal function; "improper inhibition… can have harmful or ineffective consequences" [<Front Med 2025, https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2024.1497750/full>]
- **Relation to KB:** QC-0002 (kinins protectively interact with opioid analgesia in CINP) and `Bradykinin.md` B1R-as-chronic-target framing → **NEW_MECHANISM** (temporal-context qualifier: sign of BDKRB1 edge flips with disease stage — a graph-relevant property, cf. BRADiNP failure interpretation)

### F7.10: Kinin receptor blockade in cancer-treatment pain; icatibant safety carried over
- **Evidence:** B1/B2 antagonism attenuated metastatic breast-tumor and anastrozole-induced allodynia without compromising paclitaxel cytotoxicity; authors note icatibant is approved and "described as safe and well tolerated" [<Sci Rep 2023, https://www.nature.com/articles/s41598-023-31535-6>]
- **Relation to KB:** no direct claim IDs → **EXTENDS** (`Bradykinin.md` therapeutic scope: add cancer/endocrine-therapy pain as candidate indication space)

### F7.11: Structure-based EP4 antagonists are antiallodynic in inflammatory pain models
- **Evidence:** Docking of >400M compounds vs EP4 crystal structure yielded 16 nM selective antagonists; oral/i.p. dosing reduced carrageenan and CFA mechanical allodynia and PGE₂-evoked hypersensitivity without affecting baseline thresholds [<Nat Commun 2023, https://doi.org/10.1038/s41467-023-43506-6>]
- **Relation to KB:** `prostaglandins.md` EP-pronociceptive framework (QC-0089/QC-0090 context) → **SUPPORTS** (EP4 remains a druggable antiallodynic node preclinically)

### F7.12: ⚠️ Contested: Schwann-cell EP2 — not EP4 — drives PGE₂/carrageenan/CFA allodynia
- **Evidence:** With modern selective tools: EP2 agonist butaprost produced robust allodynia where EP4 agonist L-902,688 gave mainly non-evoked nociception; three distinct EP4 antagonists (BGC20-1531, ONO-AE3-208, CJ-42794) spared allodynia; the older "EP4-selective" ER819762 proved unselective at higher doses; AAV silencing of **Schwann-cell EP2** abolished PGE₂-, carrageenan- and CFA-evoked allodynia via plasma-membrane cAMP/PKA-AKAP79/150; BGC20-1531 had already failed in migraine; no EP4-antagonist success in human inflammatory pain [<Nat Commun 2025, https://www.nature.com/articles/s41467-025-63782-8>]
- **Relation to KB:** `prostaglandins.md` EP-subtype attributions (and any EP4-weighted allodynia edge) → **CONTRADICTS** (receptor-subtype mis-attribution risk from legacy pharmacology; QC-0089's EP1-on-macrophages finding is untouched). Cross-check F7.11: same-year-class conflict between docking-paper pharmacology (EP4 antiallodynic) and this genetic/selectivity-controlled refutation → contested area, see below

### F7.13: Spinal EP3→CCL2→CCR2 axis gates *late-stage* neuropathic allodynia
- **Evidence:** In SNI, only EP3 deletion (of EP1-4) reduced late-phase mechanical allodynia; EP3 activation drove CCL2 release from DRG neurons/mast cells; CCR2 antagonist INCB3344 lost efficacy in EP3-KO mice — placing CCL2-CCR2 downstream of EP3 [<JCI-style EP3 study, https://pmc.ncbi.nlm.nih.gov/articles/PMC6016472/>]
- **Relation to KB:** bridges `prostaglandins.md` ↔ existing `CCL2-CCR2.md` dossier → **NEW_MECHANISM** (cross-theme edge; also complements QC-0089's macrophage-EP1 observation with an immune-recruitment route)

### F7.14: PGE₂ directly depolarizes sensory axons via EP4/cAMP→ANO1+Nav1.8
- **Evidence:** Microfluidic isolated-axon preparation: PGE₂ triggered persistent axonal spiking blocked by EP4 antagonist, adenylyl-cyclase blocker, Nav1.8 blockers and the ANO1 blocker T16Ainh-A01; chloride-gradient dependence shown via NKCC1 (not KCC2) manipulation [<Neuroscience 2024, https://pubmed.ncbi.nlm.nih.gov/39075089/>]
- **Relation to KB:** links `prostaglandins.md` ↔ existing `nav1.7-1.8.md` dossier; introduces ANO1 (TMEM16A) → **NEW_MECHANISM** (novel node + two edges into an existing KB channel hub)

### F7.15: NK1-antagonist reappraisal — positive signal confined to acute perioperative window
- **Evidence:** Meta-analysis of 13 RCTs (n=1959): single preoperative NK1-RA dose reduced postoperative pain at 2 h (MD −0.62) and 24 h (MD −0.65) but not 48 h, matching 9-12 h half-life; morphine consumption unchanged; authors call for reevaluation [<Brazilian-type anesthesiology/pain meta-analysis 2025, https://www.sciencedirect.com/science/article/abs/pii/S0952818025000327>]
- **Relation to KB:** `Substance_P-NK1.md` ("multiple NK1 antagonists failing in Phase II/III pain trials… renewed interest") → **EXTENDS** (the renewal is empirically anchored only in short-duration acute pain; does not rescue chronic neuropathic indications)

### F7.16: Why NK1 blockers failed — hemokinin-1/TAC4 confound and receptor promiscuity
- **Evidence:** Comprehensive neuropeptide-drug review: all NK1 antagonists tested (incl. aprepitant/fosaprepitant) lacked analgesia in Ph II/III; **no new pain-indicated NK-receptor trials registered**; proposed explanations include competition/allosteric modulation of NK1 by hemokinin-1 (Tac4-derived endokinins) and SP action via MRGPRX2; dual CGRP+NK1 inhibition proposed for trigeminal pain; SST4 agonists flagged as alternative neuropeptide strategy [<Pharmacol Ther-family review 2024, https://www.sciencedirect.com/science/article/pii/S1471489224000444>]
- **Relation to KB:** `Substance_P-NK1.md` clinical-translation caveat → **SUPPORTS**; HK-1/MRGPRX2 explanations → **NEW_MECHANISM** (candidate nodes: Hemokinin-1/TAC4, MRGPRX2)

### F7.17: Peptide-level (not receptor-level) SP targeting proposal for trigeminal pain
- **Evidence:** Methodological proposal modeled on anti-CGRP/anti-PACAP success argues past failures stemmed from single-receptor (NK1-only) blockade and proposes human provocation studies of substance P itself [<J Headache Pain 2025, https://link.springer.com/article/10.1186/s10194-025-01959-8>]
- **Relation to KB:** `Substance_P-NK1.md` functional-duality discussion → **EXTENDS**

### F7.18: COX-side corroboration retained (no new contradicting NSAID data)
- **Evidence:** EP4/EP2 papers above restate standard-of-care logic (COX-1 GI risk, COX-2 CV risk) motivating downstream prostanoid-receptor selectivity [<Nat Commun 2023, https://doi.org/10.1038/s41467-023-43506-6>]; ketorolac local-injection reversal of PSNL allodynia (KB QC-0090) remains uncontested in retrieved 2022-2026 literature
- **Relation to KB:** QC-0090 → **SUPPORTS** (no counter-evidence surfaced); QC-0049 (intrathecal 15d-PGJ₂ anti-allodynic) → **NOVEL_TARGET** status unchanged (PPARγ axis outside this sweep's hit set — see Limitations)

## New Candidate Nodes/Edges for Graph
**Nodes**
1. `Hemokinin-1 / TAC4-derived endokinins` — competitor ligand at NK1; explains NK1-RA failure (F7.16)
2. `MRGPRX2` — non-NK1 SP target on mast cells (F7.16)
3. `Schwann-cell EP2 receptor (PTGER2)` — principal mediator of inflammatory mechanical allodynia (F7.12)
4. `EP3 receptor (PTGER3)` — late-stage neuropathic allodynia gate (F7.13)
5. `ANO1 (TMEM16A)` — PGE₂/EP4-driven axonal chloride channel (F7.14)
6. `Fulmetibant (BRADiNP, NCT05219812)` — negative Ph2a B1-antagonist landmark (F7.7)
7. `Anti-CGRP-ligand vs anti-CGRP-receptor mAb class distinction` — mechanistic divergence/class switching (F7.3)
8. `AKAP79/150 nanodomain PKA signaling (Schwann cell)` — EP2 downstream compartmentalization (F7.12)

**Edges (subject → predicate/sign → object)**
- `PGE2–EP3 (spinal/mast cell/DRG)` — releases (+) → `CCL2` → activates (+) → `CCR2` → maintains (+) → `Late-stage Mechanical Allodynia (SNI)` (F7.13; ties into existing CCL2-CCR2 cluster)
- `Schwann-cell EP2` — activates (+) → `cAMP/PKA (membrane-compartmentalized)` → causes (+) → `Mechanical Allodynia (carrageenan/CFA)` (F7.12)
- `PGE2–EP4` — opens (+) → `ANO1 + Nav1.8` → triggers (+) → `Persistent Axonal Firing` (F7.14; links to nav1.7-1.8.md)
- `Kinin B2R` — via PLC/PKCε sensitizes (+) → `TRPA1` (cisplatin & AI-model confirmation) (F7.6; supports existing Bradykinin.md edge)
- `BDKRB1 (B1R)` — **context-flipping sign**: protective early diabetes / pronociceptive established inflammation & CINP (F7.9 + QC-0001/0002/0003)
- `Substance P` — alternatively signals via (+) → `MRGPRX2`; competes with ← `Hemokinin-1` at NK1 (F7.16)
- `Anti-CGRP-ligand mAb` ⊢ differs-from ⊣ `Anti-CGRP-receptor mAb` (trigeminal threshold normalization only for ligand class) (F7.3)

## Contradictions & Contested Areas
1. **EP-subtype attribution in inflammatory allodynia (HIGH impact):** F7.12 (EP2/Schwann-cell, genetically and pharmacologically controlled) vs F7.11 (EP4-antagonist antiallodynia via docking compounds) and vs legacy EP4 literature the KB leans on. Resolution requires head-to-head antagonist-selectivity audits; KB should downgrade EP4-allodynia edges until then.
2. **Cold allodynia & kinins:** `Bradykinin.md` generalization vs cisplatin-model resistance to B1/B2 blockade (F7.5) — scope-limiting amendment needed.
3. **CGRP-beyond-migraine optimism vs trial reality:** KB dossier language ("emerging efficacy signals") vs absence of any randomized controlled evidence outside headache/gepant-headache expansion (F7.1, F7.2).
4. **NK1 field split:** postoperative meta-analysis positive (F7.15) vs "no new NK-receptor pain trials registered" (F7.16) — reappraisal is real but narrow.
5. **B1R sign flip in diabetes** (F7.9): challenges any static pronociceptive labeling of BDKRB1 edges; interacts directly with interpreting BRADiNP failure.

## Landmark Classics Reconfirmed
- **Zhang et al., J Neurosci 2007** — RAMP1 is functionally rate-limiting for CGRP receptor activity in trigeminal ganglion (transgenic hRAMP1 ↑plasma extravasation 2.2×) [<https://www.jneurosci.org/content/27/10/2693>]: foundational basis for the KB's CIPN "sensitization-not-expression / RAMP1-upregulation" paradigm in `cgrp.md`. **Reconfirmed.**
- **Ho, Edvinsson & Goadsby, Nat Rev Neurol 2010** — CLR/RAMP1 receptor biology, trigeminovascular CGRP release during attacks [<https://www.nature.com/articles/nrneurol.2010.127>] **Reconfirmed.**
- **Russo, Annu Rev Pharmacol Toxicol 2015** — CGRP sensitization at multiple neuraxis levels [<https://www.annualreviews.org/content/journals/10.1146/annurev-pharmtox-010814-124701>] **Reconfirmed** (updated through the 2026 Annu Rev Med chapter, F7.1).
- **Icatibant FAST-1/FAST-2, NEJM 2010** — B2-selectivity, symptom relief vs tranexamic acid (FAST-2 p<0.001), no drug-related SAEs [<https://www.nejm.org/doi/full/10.1056/NEJMoa0906393>] **Reconfirmed.**
- **Icatibant Outcome Survey** — real-world registry: 78.6% AE-free patients, 3.1% treatment-related AEs only, no cardiovascular SAEs [<Zanichelli et al., Allergy 2016, https://doi.org/10.1111/all.13103>]; 10-year synthesis [<Clin Exp Allergy 2022, https://pubmed.ncbi.nlm.nih.gov/35861129/>]; survey completion after 15 years with **no new safety signals** [<Clin Exp Allergy 2026, https://doi.org/10.1111/cea.70271>]. This is the safety bedrock justifying icatibant's off-label repurposing attempts in pain (cf. QC-0006 AE framing, F7.7, F7.10).
- **Hill, Trends Pharmacol Sci 2000** — "why are they not analgesic in humans?" [<https://pubmed.ncbi.nlm.nih.gov/10871891/>] — the original NK1-translation critique; still the frame used by 2024-2025 reappraisals. **Reconfirmed.**
- **ONO-8711 (EP1 antagonist) in CCI rats** — hyperalgesia/allodynia reduction [<https://pubmed.ncbi.nlm.nih.gov/11574375/>] — supports QC-0089's EP1 relevance in nerve injury. **Reconfirmed.**

## References
1. Russo AF, Kaiser EA. CGRP and Migraine: Real-World Insights and Future Therapeutic Directions. Annu Rev Med (2026). https://www.annualreviews.org/content/journals/10.1146/annurev-med-050224-111631
2. Anti-CGRP receptor antibodies do not modulate trigeminal pain processing. J Headache Pain (2026). https://link.springer.com/article/10.1186/s10194-026-02316-z
3. SAFE-CGRP study. Front Neurol (2025). https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2025.1703876/full
4. Wells-Gatnik WD, et al. Rimegepant and atogepant: novel drugs… Expert Rev Neurother 24(11) (2024). https://www.tandfonline.com/doi/abs/10.1080/14737175.2024.2401558
5. Efficacy and safety of gepants in migraine management. JOFPH (2026). https://www.jofph.com/articles/10.22514/jofph.2026.046
6. Becker G, Fialho MFP, Brusco I, Oliveira SM. Kinin B1 and B2 Receptors Contribute to Cisplatin-Induced Painful Peripheral Neuropathy in Male Mice. Pharmaceutics 15:852 (2023). https://doi.org/10.3390/pharmaceutics15030852
7. Becker G, et al. Kinin B2 Receptor Mediates Cisplatin-Induced Painful Peripheral Neuropathy by Intracellular Kinase Pathways and TRPA1 Channel Sensitisation. Pharmaceuticals 16:959 (2023). https://doi.org/10.3390/ph16070959
8. Fialho MFP, et al. Kinin B2 and B1 Receptors Activation Sensitize the TRPA1 Channel Contributing to Anastrozole-Induced Pain Symptoms. Pharmaceutics 15:1136 (2023).
9. Stemper B, et al. The bradykinin-1 receptor antagonist fulmetibant in patients with diabetic neuropathic pain: BRADiNP. Pain (2025). https://doi.org/10.1097/j.pain.0000000000003642
10. Bouhassira D, et al. Eliapixant in diabetic neuropathic pain: PUCCINI. Pain 165(4):785-795 (2023). https://doi.org/10.1097/j.pain.0000000000003085
11. Bradykinin receptor expression and bradykinin-mediated sensitization of human sensory neurons. Pain 165(1) (2024). https://journals.lww.com/pain/fulltext/2024/01000/bradykinin_receptor_expression_and.18.aspx
12. Shared signaling pathways in diabetic complications. Front Med (2025). https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2024.1497750/full
13. Kinin B1 and B2 receptors mediate cancer pain associated with metastatic breast tumor and aromatase inhibitors. Sci Rep 13 (2023). https://www.nature.com/articles/s41598-023-31535-6
14. Docking for EP4R antagonists active against inflammatory pain. Nat Commun (2023). https://doi.org/10.1038/s41467-023-43506-6
15. Targeting prostaglandin E2 receptor 2 in Schwann cells… Nat Commun (2025). https://www.nature.com/articles/s41467-025-63782-8
16. The prostaglandin E2 receptor EP3 controls CC-chemokine ligand 2… (EP3/CCL2/CCR2, SNI). https://pmc.ncbi.nlm.nih.gov/articles/PMC6016472/
17. PGE2 depolarises sensory axons in vitro in an ANO1 and Nav1.8 dependent manner (2024). https://pubmed.ncbi.nlm.nih.gov/39075089/
18. ONO-8711 EP1 antagonist in CCI rats. https://pubmed.ncbi.nlm.nih.gov/11574375/
19. NK-1 receptor antagonists for postoperative pain: meta-analysis of RCTs (2025). https://www.sciencedirect.com/science/article/abs/pii/S0952818025000327
20. Drug effects on neuropeptides and their receptors: big hopes but moderate success in chronic pain (2024). https://www.sciencedirect.com/science/article/pii/S1471489224000444
21. Revisiting substance P in migraine. J Headache Pain (2025). https://link.springer.com/article/10.1186/s10194-025-01959-8
22. Zhang Z, et al. Sensitization of CGRP receptors by RAMP1 in the trigeminal ganglion. J Neurosci 27:2693 (2007). https://www.jneurosci.org/content/27/10/2693
23. Ho TW, Edvinsson L, Goadsby PJ. CGRP and its receptors… Nat Rev Neurol 6:573 (2010). https://www.nature.com/articles/nrneurol.2010.127
24. Russo AF. CGRP: A New Target for Migraine. Annu Rev Pharmacol Toxicol 55 (2015). https://www.annualreviews.org/content/journals/10.1146/annurev-pharmtox-010814-124701
25. Cicardi M, et al. Icatibant… in hereditary angioedema (FAST-1/2). N Engl J Med 363:532-541 (2010). https://www.nejm.org/doi/full/10.1056/NEJMoa0906393
26. Zanichelli A, et al. Long-term safety of icatibant… Allergy (2016). https://doi.org/10.1111/all.13103
27. Maurer M, et al. The Icatibant Outcome Survey: 10 years. Clin Exp Allergy 52:1048-1058 (2022). https://pubmed.ncbi.nlm.nih.gov/35861129/
28. Bouillet L, et al. Completion of the Icatibant Outcome Survey. Clin Exp Allergy (2026). https://doi.org/10.1111/cea.70271
29. Hill R. NK1 (substance P) receptor antagonists—why are they not analgesic in humans? Trends Pharmacol Sci 21:244-246 (2000). https://pubmed.ncbi.nlm.nih.gov/10871891/

## Post-Round Adjudications (2026-08-26)

### A7.1: fulmetibant → mechanical allodynia resolved (was graph AMBIGUOUS edge `Fulmetibant--[inhibits]-->Mechanical Allodynia`)
- **Evidence:** BRADiNP Phase 2a (randomized, double-blind, placebo-controlled 2-period crossover, n=158 treated, 75 completers both periods) of fulmetibant 450 mg once daily in painful diabetic neuropathy: primary endpoint change in weekly mean 24-h average pain NRS at week 4 showed treatment difference **0.07 (95% CI −0.170 to 0.314)** — negative; authors' conclusion: "preclinical efficacy seen with this bradykinin 1 receptor antagonist did not translate" [Stemper et al., Pain 2025, doi:10.1097/j.pain.0000000000003642; NCT05219812]. Preclinical B1-blockade analgesia remains model-supported (QC-0001/0003 cisplatin DALBK/icatibant data), and cold allodynia was B1/B2-blockade-resistant in the cisplatin model (F7 Contradictions); stage-dependent B1R sign-flip in diabetes (F7.9) further cautions against static drug→symptom edges.
- **Relation to KB:** raw-graph edge `Fulmetibant --[inhibits]--> Mechanical Allodynia` (AMBIGUOUS 0.2) → **REFUTED as a clinical drug effect** in the only human test (DNP Ph2a). Encoded as a QUARANTINE pair (sign 0 + validation_status REFUTED) so future graph rebuilds cannot resurrect it as an active simulator rule; preclinical mechanism-level B1 edges unaffected.

## Sweep Limitations
- **Snippet-level evidence:** all findings derive from websearch result extracts (abstracts/highlights); full texts, supplementary data and exact dose-response figures were not independently retrieved or verified.
- **Claims-inventory gap dominates this theme:** `cgrp.md` and `Substance_P-NK1.md` produced zero claims, so CGRP/SP-NK1 axes could be validated only at dossier level; conversely all six bradykinin claims are trial-design/quantitative statements whose source paper (BRADiNP) is now located and quotable.
- **Search-engine recency skew:** several surfaced items carry 2026 dates (e.g., JHP erenumab paper dated 2026-03); coverage of mid-2026 publications is necessarily incomplete.
- **Registry opacity:** ongoing/non-publishing trials (ClinicalTrials.gov entries for CGRP-in-pain or kinin-antagonist programs) were not systematically enumerated; absence-of-trials claims (F7.2, F7.16) reflect literature absence, not registry proof.
- **Contested EP4 question unresolved:** F7.11 vs F7.12 cannot be adjudicated without primary-data comparison of antagonist selectivity profiles.
- **Language/region bias:** English-language sources only; Japanese and Brazilian RCT clusters (per NK1 meta-analysis) entered only through secondary reporting.
- **Adjacent themes intentionally shallow:** PPARγ/15d-PGJ₂ (QC-0049), COX-2/mPGES-1 spinal endothelial axis and SST4-agonist alternatives were noted but not swept (assigned to neighboring themes).
