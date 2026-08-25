# Theme 9: Epigenetics — HDAC / Lactylation / JAK-STAT / miRNA
_Sweep date: 2026-08-25 · Scope: 2021-2026 + landmark classics_

**Claims filtered (16 of 262):** EC-0018, EC-0045, EC-0047, EC-0048, EC-0049, EC-0051, EC-0072, EC-0114, EC-0152, EC-0155 (JAK-STAT edges, `JAK-STAT.md`); QC-0071, QC-0072, QC-0073, QC-0074 (lactylation quant statements, `epigenetic_mechanisms_pain.md`); QC-0090 (CREB phosphorylation, `prostaglandins.md`). Source dossiers consulted: `epigenetic_mechanisms_pain.md`, `JAK-STAT.md`, `karilin-7.md`.
_Note: QC-0075 (1400W/iNOS) matched spuriously on "amino**methyl**" and is out of scope for this theme._

## Search Log

| # | Query | Period | Key hits |
|---|-------|--------|----------|
| 1 | histone deacetylase inhibitor neuropathic pain HDAC6 HDAC4 | 2022–2026 | ACY-1215 HDAC6/STAT3/CCL7 SNI study (J Neuroinflammation 2025); HDAC-microglia review (Front Pharmacol 2025); panobinostat→GAD65 CCI (Pain Rep 2024); HDAC6i clinical translation review (Expert Opin Ther Targets 2024); sEH/HDAC6 dual inhibitor M9 |
| 2 | histone lactylation chronic pain IGF2BP2 m6A | 2024–2026 | H3K18la→IGF2BP2→CCT2 in DRG (J Neurosci 2025); AREG→EGFR→PKM2→p300 lactylation (Sci Signal 2025); microglial H4K12la review (Mol Neurobiol 2026); m6A↔lactylation crosstalk review (J Transl Med 2026) |
| 3 | H3K18la DRG dorsal root ganglion pain epigenetics | open | Same as #2 plus DOCK4/H4K8la/Nav1.7 trafficking (Nat Commun 2025); DNA methylation DRG reprogramming (J Neurosci 2018, background); G9a K+ channel silencing (background) |
| 4 | JAK STAT3 inhibitor microglia neuropathic pain ruxolitinib baricitinib | 2021–2026 | Baricitinib CAIA→CSF-1↓ (Arthritis Res Ther 2024); direct baricitinib effects on joint nociceptors/DRG Stat3 (IJMS 2024); JAK2/STAT3 chronic-pain targeting review (Aging Dis 2024); ruxolitinib BV2 NF-κB/MAPK (Eur J Pharmacol 2024) |
| 5 | CREB transcription factor phosphorylation spinal cord dorsal horn central sensitization | open | ERK/CREB in pain & analgesia review (Front Mol Neurosci 2023); cytokines→CREB phosphorylation in dorsal horn (J Neurosci 2008, classic); ERK/CREB CCI (Acta Pharmacol Sin 2005); formalin→pCREB Ser133 (J Neurosci 1997) |
| 6 | microRNA biomarker neuropathic pain circulating serum diagnostic | 2023–2026 | RNA-biomarker clinical review incl. miRNA panels (Front Pain Res 2026); circulating miRNAs nociceptive vs nociplastic (let-7a/miR-26a/miR-16 pilot, 2025); plasma miR-98-5p oxaliplatin NP (GEO GSE319960, 2026); serum miR-15a (Chin J Brain Dis Rehabil 2023); miRNA mechanisms review (Front Mol Neurosci 2023) |
| 7 | Landmarks: Denk 2013 HDAC; Tsuda/Uchida-Zhang STAT3 glia | classics | Denk et al., Pain 154(9):1668–1679, 2013 (confirmed full text); Tsuda et al., Brain 134(4):1127–1139, 2011 (confirmed — see Limitations re: "Uchida/Zhang" attribution); SOCS3-JAK/STAT3 blockade paper (PMC6632340, partial) |

## Findings vs Existing Claims

### F9.1: H3K18la drives Igf2bp2 transcription in injured DRG — lactylation–m6A reader axis confirmed
- **Evidence:** Peripheral nerve injury raised H3K18la in injured DRG; increased binding at the *Igf2bp2* CpG island activated *Igf2bp2* transcription; IGF2BP2 stabilized *Cct2* mRNA; 2-DG or *Igf2bp2* knockdown attenuated mechanical/thermal hypersensitivity; sodium lactate injected into uninjured DRG induced pain-like behavior via H3K18la→IGF2BP2→CCT2. [Wang Q-H, Xie S, Yang K-H, et al. 2025, *Journal of Neuroscience*, DOI 10.1523/jneurosci.0365-25.2025]
- **Relation to KB:** QC-0071, QC-0072 → **SUPPORTS** (core premise: nerve-injury lactate→H3K18la at pronociceptive loci is causal and pharmacologically reversible); **EXTENDS** by naming the first concrete downstream target pair (IGF2BP2→CCT2) and formally bridging the KB's lactylation section to its m6A epitranscriptomics section (`epigenetic_mechanisms_pain.md`).

### F9.2: AREG–EGFR–PKM2 axis is an upstream driver of neuronal histone lactylation
- **Evidence:** Nerve injury increased AREG/EGFR in DRG; AREG-EGFR signaling activated PKM2-driven glycolysis; lactate enabled p300-catalyzed H3K18 and H4K12 lactylation promoting proinflammatory/pronociceptive gene expression; deletion/knockdown of AREG or inhibition of EGFR, PKM2, or p300 alleviated neuropathic pain and nociceptor hyperexcitability. [Deng et al. 2025, *Science Signaling*, DOI 10.1126/scisignal.adr9397]
- **Relation to KB:** QC-0071, QC-0072 → **NEW_MECHANISM** upstream arm (AREG/EGFR/PKM2 absent from KB graph); reinforces p300 as writer already named in `epigenetic_mechanisms_pain.md`.

### F9.3: H4K8 lactylation represses DOCK4 and dysregulates Nav1.7 trafficking (thermosensor-independent heat pain)
- **Evidence:** Across four pain models (SNL, CFA, paclitaxel, bone cancer), pan-Kla rose in DRG; H4K8la enriched at the *Dock4* promoter downregulated DOCK4; DOCK4 normally scaffolds a Dynein/DOCK4/Nav1.7 complex mediating Nav1.7 membrane-to-cytoplasm trafficking; loss of DOCK4 increased heat nociception in mice and male nonhuman primates; sodium oxamate restored DOCK4. [Nature Communications 2025, DOI 10.1038/s41467-025-62343-3]
- **Relation to KB:** QC-0071 → **NEW_MECHANISM** (repressive lactylation mark on an anti-nociceptive gene — sign logic differs from the KB's "lactylation activates pronociceptive promoters" framing); **NOVEL_TARGET** (DOCK4, Dynein/DOCK4/Nav1.7 complex; connects to any Nav1.7 nodes in Theme 6 DRG excitability).

### F9.4: HDAC6 inhibition analgesia runs through STAT3 deacetylation/phosphorylation balance and CCL7
- **Evidence:** Selective HDAC6 inhibitor ACY-1215 (20 mg/kg/day ×14 d) alleviated SNI allodynia in both sexes; raised Ac-STAT3(Lys685), reduced p-STAT3(Tyr705) in lumbar cord; SNI-enhanced HDAC6/STAT3 interaction reversed; neuronal STAT3 overexpression drove hypersensitivity and TNF-α/IL-1β release suppressed by ACY-1215; cytokine profiling identified CCL7 as key downstream effector of the HDAC6/STAT3/CCL7 axis. [Journal of Neuroinflammation 2025, DOI 10.1186/s12974-025-03400-y]
- **Relation to KB:** EC-0047/EC-0048 region → **SUPPORTS** (STAT3 is druggable and anti-allodynic when inhibited); **EXTENDS** by adding a non-canonical cross-link between the KB's HDAC module (HDAC6/tubastatin/ACY-738, CIPN 2023) and its JAK-STAT module — a missing inter-dossier edge (HDAC6 ⇄ STAT3 PTMs).

### F9.5: Pan-HDAC inhibition restores spinal GABA synthesis (GAD65) in established neuropathy
- **Evidence:** CCI upregulated neuronal HDAC3, HDAC4, HDAC6 in laminae I–III with reduced H3K9ac, GAD65 and GABA; daily intrathecal panobinostat (1 µg) attenuated hyperalgesia/allodynia days 5–28 and restored GAD65/GABA expression. [Pain Reports 2024, URL journals.lww.com/painrpts/fulltext/2024/12000/upregulated_spinal_histone_deacetylases_induce.16.aspx]
- **Relation to KB:** EC-0051 (object: "HDAC4 … represses KCC2/**GAD65**") → **SUPPORTS** (direct confirmation of HDAC4-class repression of GAD65 in dorsal horn neurons) and links mechanistically to Theme 1 disinhibition.

### F9.6: HDAC6 inhibitors reach translational testing for painful diabetic peripheral neuropathy
- **Evidence:** Expert review: HDAC6 inhibition in clinical trials spanning peripheral neuropathies; ricolinostat (ACY-1215) entered trials for painful diabetic peripheral neuropathy; brain-penetrant vs peripheral-restrictive compounds, PET tracers, and safety concerns for chronic use reviewed. [van Eyll J. 2024, *Expert Opinion on Therapeutic Targets* 28(9), DOI 10.1080/14728222.2024.2404571]
- **Relation to KB:** `epigenetic_mechanisms_pain.md` HDAC section → **EXTENDS** (updates clinical-development status beyond the KB's "clinical development limited by systemic toxicity" statement for broad-spectrum HDACi; isoform-selective HDAC6i partially escape that limitation).

### F9.7: Class I HDACi are prophylactic, not reversing, in traumatic neuropathy (landmark re-read)
- **Evidence:** Intrathecal MS-275/MGCD0103 attenuated hypersensitivity 40–50% across PSNL, L5Tx and d4T-neuropathy models **only if started before injury**; post-injury pumps ineffective; effects mapped to HDAC1 via compound signature/causal reasoning. [Denk F, Huang W, Sidders B, et al. 2013, *Pain* 154(9):1668–1679, DOI 10.1016/j.pain.2013.05.021]
- **Relation to KB:** `epigenetic_mechanisms_pain.md` ("broad-spectrum HDAC inhibitors have shown analgesic effects") → **EXTENDS with caveat**: the blanket claim needs schedule-of-administration qualifiers; contrasts with genuine reversal seen for HDAC6i in CIPN/SNI (F9.4, F9.6; J Neurosci 2022 ACY-1083 enkephalin-DOR mechanism, DOI 10.1523/JNEUROSCI). See Contradictions.

### F9.8: Baricitinib suppresses residual neuropathic-type allodynia via IL-6/JAK/STAT3 and CSF-1 in DRG
- **Evidence:** In collagen-antibody-induced arthritis mice, baricitinib (unlike celecoxib) normalized DRG transcriptome, suppressed interferon/JAK-STAT3/NF-κB programs and *Csf1*, prevented spinal microglial (and later astrocytic) proliferation, and uniquely reduced residual tactile allodynia. [Makabe K, Okada H, Tachibana N, et al. 2024, *Arthritis Research & Therapy* 26:121, DOI 10.1186/s13075-024-03354-1]
- **Relation to KB:** EC-0047 → **SUPPORTS** (baricitinib inhibits JAK/STAT3-dependent pain); **EXTENDS** with the downstream mediator edge STAT3→CSF-1→spinal glial activation, which the KB's JAK-STAT dossier lacks.

### F9.9: JAK inhibitors act directly on nociceptors — neuronal cell-autonomous arm
- **Evidence:** Intra-articular baricitinib reduced inflamed-joint C-fiber responses; blocked IL-6/sIL-6R-induced Stat3 activation in cultured DRG neurons and prevented IL-6+sIL-6R-induced hyperexcitability (mimicked by Stat3 inhibitor Sta21 after preincubation); TNF effects spared (non-JAK). [Int J Mol Sci 2024;25:11943, DOI 10.3390/ijms252211943]
- **Relation to KB:** EC-0047, EC-0048 → **EXTENDS** (adds neuronal, non-glial site of action consistent with EC-0045's neuron-facing KCC2 consequence).

### F9.10: STAT3 glial activation landmark and microglial JAK2/STAT3 loops reconfirmed
- **Evidence:** Nerve injury induced temporally restricted astrocyte proliferation requiring JAK-STAT3; intrathecal AG490/JAK Inhibitor I produced recovery from established tactile allodynia. [Tsuda M, Kohro Y, Yano T, et al. 2011, *Brain* 134(4):1127–1139, DOI 10.1093/brain/awr025]. Recent extensions: IL-6/JAK2/STAT3 drives microglia+astrocyte activation and below-level pain after SCI (AG490, anti-IL-6; PubMed 37863306, 2023-ish); red-nucleus IL-33→TNF-α via JAK2/STAT3 in mononeuropathic pain (J Neuroinflammation 2021, DOI 10.1186/s12974-021-02198-9); P2Y6 receptor→IL-6→JAK/STAT positive feedback in spinal microglia (PubMed 31281556); dedicated review [Targeting the JAK2/STAT3 pathway for chronic pain, *Aging and Disease* 2024;15(1):186–200, DOI 10.14336/AD.2023.0515].
- **Relation to KB:** EC-0018, EC-0045, EC-0072, EC-0114, EC-0152, EC-0155 → **SUPPORTS** (whole-network framing of IL-6/gp130/JAK2→STAT3 as central hub fed by BDNF/MMP-9/TNF-α/NF-κB matches current consensus reviews).

### F9.11: Circulating miRNA panels mature toward objective neuropathic-pain biomarkers
- **Evidence:** Clinical review proposing RNA-based testing (miRNA/lncRNA/m6A layers) with listed validated circulating candidates (e.g., serum miR-382-5p↑; whole-blood miR-128↑, miR-155/499↓; NEAT1/miR-183-5p axis) and caveats on pre-analytical variability; exploratory plasma study separated nociceptive vs nociplastic pain using let-7a/miR-26a/miR-16 (AUC >0.94 in decision-tree model); GEO deposit GSE319960 proposes plasma miR-98-5p as diagnostic marker for oxaliplatin-induced neuropathic pain. [Frontiers in Pain Research 2026, DOI 10.3389/fpain.2026.1874336; PMC12275945 2025; OmicsDI GSE319960 2026; serum miR-15a study, Chin J Brain Dis Rehabil 2023, DOI 10.3877/cma.j.issn.2095-123X.2023.05.006]
- **Relation to KB:** No existing claim → **NEW_MECHANISM** (biomarker/diagnostic layer entirely absent from the mechanistic graph; candidate "circulating miRNA panel" biomarker node).

### F9.12: miR-206-3p post-transcriptionally restrains HDAC4 in DRG
- **Evidence:** HDAC4 induced in rat DRG after CCI; targeting HDAC4 expression with miR-206-3p alleviated neuropathic pain in animals (cited within HDAC-microglia review summarizing Wen et al. 2019); same review flags HDAC4's contradictory roles in microglia (below). [Frontiers in Pharmacology 2025, DOI 10.3389/fphar.2025.1515787]
- **Relation to KB:** EC-0051 (KALRN→HDAC4) → **EXTENDS** (parallel post-transcriptional brake on the same effector; candidate edge miR-206-3p ⊣ HDAC4).

### F9.13: CREB phosphorylation as convergent pronociceptive transcriptional switch
- **Evidence:** Classic and recent work: IL-1β/IL-6/TNF-α all increase pCREB(Ser133) in superficial dorsal horn neurons and produce heat hyperalgesia (J Neurosci 2008, DOI 10.1523/JNEUROSCI.5189-07.2008); formalin induces rapid NMDAR-dependent pCREB preceding c-Fos (J Neurosci 1997, 17(5):1776); ERK→CREB required for CCI allodynia/hyperalgesia (Acta Pharmacol Sin 2005); systematic ERK/CREB review including analgesic side-effect caveats (Front Mol Neurosci 2023, DOI 10.3389/fnmol.2023.1156674).
- **Relation to KB:** QC-0090 (ketorolac suppresses injury-induced CREB phosphorylation) → **SUPPORTS** (COX/PGE2 and PIC inputs converge on pCREB as described; NSAID suppression of pCREB is mechanism-consistent).

## New Candidate Nodes/Edges for Graph

**Nodes**
| Candidate | Type | Rationale |
|-----------|------|-----------|
| Amphiregulin (AREG)/EGFR | signaling ligand/receptor | upstream glycolysis-lactylation trigger (F9.2) |
| PKM2 (kinase activity) | metabolic kinase | EGFR→glycolysis switch (F9.2) |
| IGF2BP2 (m6A reader) | RNA-binding protein | H3K18la target; CCT2 stabilizer (F9.1) |
| CCT2 | chaperonin | functional readout of lactylation axis (F9.1) |
| DOCK4 / Dynein–DOCK4–Nav1.7 complex | adaptor/trafficking | thermosensor-independent heat pain (F9.3) |
| H4K12la, H4K8la | histone marks | microglial (nucleus pulposus) and DRG repressive marks (F9.3, F9.2/review) |
| CCL7 | chemokine | HDAC6/STAT3 downstream effector (F9.4) |
| Ricolinostat (ACY-1215), Panobinostat, ACY-1083 | drug nodes | isoform-selectivity spectrum; clinical status (F9.4–F9.7) |
| miR-206-3p | microRNA | post-transcriptional restraint of HDAC4 (F9.12) |
| Circulating miRNA panel (let-7a, miR-26a, miR-16, miR-382-5p, miR-98-5p…) | biomarker node | diagnostic/stratification layer (F9.11) |
| CSF-1 (DRG neuronal) | secondary mediator | baricitinib-suppressed microglial activator (F9.8) |

**Edges**
- AREG→EGFR ⇒ PKM2 ⇒ glycolysis/lactate ⇒ p300-lactylation(H3K18la,H4K12la) ⇒ pronociceptive transcription [+]
- H3K18la @ *Igf2bp2* promoter ⇒ IGF2BP2 ⇒ CCT2 mRNA stability ⇒ pain signaling [+]
- H4K8la @ *Dock4* promoter ⊣ DOCK4 ⇒ impaired Nav1.7 internalization ⇒ heat nociception [+]
- HDAC6 ⊣ Ac-STAT3(K685) / ⇒ p-STAT3(Y705) ⇒ CCL7, TNF-α, IL-1β [+]
- HDAC3/4/6 ⊣ Gad2(GAD65)/GABA ⇒ spinal disinhibition [+]; panobinostat reverses
- STAT3 ⇒ CSF-1 (DRG neurons) ⇒ spinal microglial activation [+]; baricitinib ⊣ this arm
- JAK-STAT3 ⇒ dorsal-horn astrocyte proliferation ⇒ allodynia maintenance [+]
- miR-206-3p ⊣ HDAC4 (DRG)
- IL-6 ⇄ JAK/STAT3 positive-feedback loop in microglia (P2Y6-amplified) [+]

## Contradictions & Contested Areas
1. **Schedule dependence of HDACi analgesia.** Denk 2013: class I HDACi prevent but do **not reverse** traumatic neuropathy (F9.7) — qualifies the KB's unqualified "analgesic effects" statement for broad-spectrum HDACi; HDAC6i do reverse established CIPN/allodynia (ACY-1083, ACY-1215), so the property is isoform-dependent.
2. **Lactylation site heterogeneity.** In SNL DRG, H4K8la/H4K12la rose while H3K18la was unchanged (Nat Commun 2025), whereas CCI DRG showed robust H3K18la induction (J Neurosci 2025). QC-0071's ">28-day persistent H3K18la" generalization should be annotated as model- and locus-specific.
3. **HDAC4 dual role in myeloid cells.** Required for LPS-induced cytokines in BV2 yet degraded by prolonged glycolytic GSK3β-iNOS-NO/caspase-3 axis (Wang et al. 2014) and protective in immunometabolic programming (Crow 2015) — flagged in Front Pharmacol 2025 review; caution against linear "HDAC4 = pronociceptive everywhere" edges (relevant to EC-0051 scope).
4. **Unverified quantitative dosing claims.** QC-0072 (FX11 10 µg i.t., 72-h reversal) and QC-0073/QC-0074 (AZD3965 oral 50 mg/kg; systemic toxicity) were not independently encountered in this sweep — remain UNVERIFIED, not contradicted.
5. **HDAC6i selectivity caveat.** High-concentration ACY-1215 also inhibits HDAC1/2/3 (noted in both 2025 sources) — matters for attributing effects purely to HDAC6.
6. **Baricitinib BBB penetration** remains uncertain (IJMS 2024 discussion; Matsushita 2023 shows CNS action only where barrier is weak) — tempers expectations for central JAK-STAT3 targets despite strong DRG/peripheral data.

## Landmark Classics Reconfirmed
- **Denk et al. 2013, Pain 154(9):1668–1679** — first direct evidence HDACs drive emergence of neuropathic pain; HDAC1 implicated; prophylactic-window lesson intact.
- **Tsuda et al. 2011, Brain 134(4):1127–1139 (awr025)** — JAK-STAT3 as critical transducer of reactive astrogliosis and allodynia maintenance (see Limitations regarding the task's "Uchida/Zhang" label).
- **Ji et al. 1997, J Neurosci 17:1776** (formalin pCREB) and **Choi/Vega? — Kawasaki et al. 2008, J Neurosci 28:5189** (PICs→pCREB→hyperalgesia) — CREB as convergent plasticity switch underpinning QC-0090.
- Background reconfirmations: G9a/H3K9me2 K+-channel silencing (PMC4661086) and DRG DNA hypomethylation (J Neurosci 2018;38:6090) align with `epigenetic_mechanisms_pain.md` methylation sections.

## References
1. Wang Q-H, et al. Histone lactylation contributes to neuropathic pain by facilitating m6A reader protein IGF2BP2 expression in DRG sensory neurons. *J Neurosci* 2025. DOI 10.1523/jneurosci.0365-25.2025
2. Deng et al. Amphiregulin contributes to neuropathic pain by enhancing glycolysis that stimulates histone lactylation in sensory neurons. *Sci Signal* 2025. DOI 10.1126/scisignal.adr9397
3. Histone lactylation regulates DOCK4 to control heat nociception and supports Dynein-mediated Nav1.7 trafficking. *Nat Commun* 2025. DOI 10.1038/s41467-025-62343-3 (PMC12322138)
4. Inhibition of HDAC6 alleviates neuropathic pain via HDAC6/STAT3/CCL7 axis. *J Neuroinflammation* 2025. DOI 10.1186/s12974-025-03400-y
5. Histone deacetylases: critical enzymes for microglial activation in neuropathic pain (review). *Front Pharmacol* 2025. DOI 10.3389/fphar.2025.1515787
6. Upregulated spinal HDACs induce nociceptive sensitization by inhibiting GABA system in CCI rats. *Pain Rep* 2024. https://journals.lww.com/painrpts/fulltext/2024/12000/upregulated_spinal_histone_deacetylases_induce.16.aspx
7. van Eyll J. Therapeutic indications for HDAC6 inhibitors in PNS and CNS disorders. *Expert Opin Ther Targets* 2024;28(9). DOI 10.1080/14728222.2024.2404571
8. HDAC6 inhibition reverses cisplatin-induced mechanical hypersensitivity via tonic δ-opioid receptor signaling. *J Neurosci* 2022;42(42):7862. https://www.jneurosci.org/content/42/42/7862
9. HDAC6 inhibitor reverses chemotherapy-induced hypersensitivity via IL-10/macrophage pathway. *Brain Behav Immun* 2022. DOI 10.1016/j.bbi.2021.11.008 (S088915912100636X)
10. Design/synthesis of dual sEH–HDAC6 inhibitors (M9) for neuropathic pain. PMC11308793, 2024.
11. Makabe K, et al. Baricitinib ameliorates inflammatory and neuropathic pain in CAIA mice via IL-6/JAK/STAT3 and CSF-1. *Arthritis Res Ther* 2024;26:121. DOI 10.1186/s13075-024-03354-1
12. Direct effects of baricitinib on sensory neurons. *Int J Mol Sci* 2024;25:11943. DOI 10.3390/ijms252211943
13. Targeting the JAK2/STAT3 signaling pathway for chronic pain (review). *Aging Dis* 2024;15(1):186–200. DOI 10.14336/AD.2023.0515
14. Red nucleus IL-33 facilitates mononeuropathic pain via ERK/p38/JAK2-STAT3→TNF-α. *J Neuroinflammation* 2021. DOI 10.1186/s12974-021-02198-9
15. IL-6/JAK2/STAT3 axis mediates neuropathic pain via glial activation after SCI. PubMed 37863306.
16. P2Y6 receptor-mediated spinal microglial activation in neuropathic pain. PubMed 31281556.
17. Interplay between m6A RNA methylation and protein lactylation (review). *J Transl Med* 2026. DOI 10.1186/s12967-026-08663-4
18. A novel approach to NP treatment: lactylation targeting microglia (review). *Mol Neurobiol* 2026. DOI 10.1007/s12035-026-05989-4
19. METTL14-mediated m6A modification contributes to CINP by stabilizing GluN2A via IGF2BP2. *J Clin Invest* 174847. https://jci.org/articles/view/174847/ga
20. New insight into RNA biomarkers in neuropathic pain (review). *Front Pain Res* 2026. DOI 10.3389/fpain.2026.1874336
21. Circulating microRNAs differentiate nociceptive and nociplastic pain (pilot). PMC12275945, 2025.
22. Plasma miR-98-5p as diagnostic biomarker for oxaliplatin-induced neuropathic pain. GEO GSE319960 (OmicsDI), 2026.
23. Serum miR-15a in patients with neuropathic pain. *Chin J Brain Dis Rehabil* 2023;13(05). DOI 10.3877/cma.j.issn.2095-123X.2023.05.006
24. Emerging roles of miRNAs in neuropathic pain (review). *Front Mol Neurosci* 2023. DOI 10.3389/fnmol.2023.1110975
25. Mechanism of ERK/CREB pathway in pain and analgesia (review). *Front Mol Neurosci* 2023. DOI 10.3389/fnmol.2023.1156674
26. Kawasaki Y, et al. Cytokine mechanisms of central sensitization. *J Neurosci* 2008;28:5189. DOI 10.1523/JNEUROSCI.5189-07.2008
27. Ji R-R, Rupp F. Phosphorylation of CREB in rat spinal cord after formalin hyperalgesia. *J Neurosci* 1997;17:1776.
28. Song X-S, et al. Activation of ERK/CREB pathway in spinal cord contributes to CCI neuropathic pain. *Acta Pharmacol Sin* 2005;26:789. DOI 10.1111/j.1745-7254.2005.00123.x
29. Denk F, et al. HDAC inhibitors attenuate the development of hypersensitivity in models of neuropathic pain. *Pain* 2013;154:1668–1679. DOI 10.1016/j.pain.2013.05.021
30. Tsuda M, et al. JAK-STAT3 pathway regulates spinal astrocyte proliferation and neuropathic pain maintenance in rats. *Brain* 2011;134:1127–1139. DOI 10.1093/brain/awr025

## Sweep Limitations
- Websearch-snippet level only; full texts not systematically retrieved, so some dose/effect numbers above reflect author abstracts rather than verified tables.
- The task's landmark hint "Uchida/Zhang STAT3 microglia pain" did not resolve to papers authored by Uchida or Zhang on microglial STAT3; the canonical STAT3-glia pain landmark retrieved is **Tsuda et al. 2011, Brain** (astrocytes), supplemented by microglial IL-6/JAK2/STAT3 studies (refs 15, 16). If a specific Uchida/Zhang paper was intended, it requires a follow-up targeted query.
- KB quantitative lactylation claims (QC-0072/73/74: FX11, AZD3965 doses/time-courses) were not independently reproduced in sweep results — flagged unverified, not falsified.
- Several 2026-dated items (refs 17, 18, 20) are reviews; mechanism edges drawn from them should carry lower confidence until primary data are checked.
- Clinical-trial status for ricolinostat rests on one secondary expert review (ref 7); registry-level verification pending.
- No contradiction found against any existing KB claim; all 16 in-scope claims survived classification (10 SUPPORTED/EXTENDED JAK-STAT edges, 4 lactylation quants, 1 HDAC4 edge, 1 CREB quant).
