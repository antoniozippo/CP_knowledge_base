# Theme 6: DRG Excitability — Sodium/Calcium/TRPV1 Channels, Splicing Regulators
_Sweep date: 2026-08-25 · Scope: 2021-2026 + landmark classics_

## Search Log
| # | Query | Period | Key hits |
|---|-------|--------|----------|
| 1 | Nav1.7 Nav1.8 blockers pain clinical trials 2024 2025 suzetrigine | 2024–2026 | Suzetrigine (VX-548/Journavx) FDA-approved Jan 2025; two Phase 3 RCTs (Anesthesiology 2025, PMID 40117446); Stewart et al. PNAS 2025 human DRG suzetrigine physiology; Vasylyev/Waxman J Gen Physiol 2024 Nav1.8×Nav1.7 dynamic-clamp; Vertex microneurography Ph1 (VX-150/993/548, NCT06420765); Vienna NaV1.8 human-pain-model microdosing study (NCT07511400) |
| 2 | TRPV1 antagonists hyperthermia resensitization pain therapy review 2024 | 2019–2024 | Neuron 2024 biased-allosterism paper (S4–S5 linker; PSFL2874); Romanovsky-lab modeling/meta-analysis of human-trial hyperthermia (PMID 31926897); Life Sci 2024 TRPV1-neuropathic-pain review (S0024320524005447); JCI 2023 human TRPV1 K710N/N331K + V1-cal peptide (PMC9888373) |
| 3 | Cav3.2 T-type channel diabetic neuropathy O-GlcNAc glycosylation pain | 2013–2025 | Orestes Diabetes 2013 (NEU reverses ob/ob hyperalgesia); Joksimovic Front Cell Neurosci 2020 (STZ type-1); Mol Brain 2022 T-type-in-pain review (ABT-639 Phase II failure reconfirmed); Shanghai J Med Univ 2025 A-fiber N-glycosylation paper |
| 4 | Rbfox1 splicing dorsal root ganglion neuropathic pain Nrcam | 2020–2024 | He et al. Neurotherapeutics 2023 (Rbfox1→Nrcam exon 10; PMID 38241164); Liang/Tao J Pain 2020 (Nrcam+10 ASO; PMID 31917219); Neurotherapeutics editorial commentary 2024 (direction-of-binding caveat) |
| 5 | DRGX dorsal root ganglia homeobox transcription factor nociceptor pain | 1995–2020 | Mol Pain 2020 (DRGX DOWN after SNL; knockdown induces pain, overexpression suppresses via MMP-9; doi:10.1177/1744806920904462); Chen et al. 2001 Drg11-KO developmental phenotype (via OMIM 606701); NCBI Gene DRGX/PRRX-L1 annotations |
| 6 | ZFHX2 congenital insensitivity to pain Marsili mechanism BDNF nociceptor | 2017–2018 (+thesis) | Habib et al. Brain 2018;141:365–376 Marsili syndrome R1913K (PMID 29253101); OMIM 147430; UCL press 2017; Matsuyama UCL thesis (Zfhx2-null heat HYPERsensitivity detail) |
| 7 | antisense oligonucleotide SCN9A Nav1.7 pain intrathecal clinical trial | 2017–2026 | NO SCN9A-ASO clinical trial yet; Quiver QV-2421 NIH UG3/UH3 (UG3NS146009) IND-enabling → planned Ph I in erythromelalgia; ATL-301 di-siRNA >3-month rodent analgesia (WCP 2024 poster TH699); N02C0702 ASO-siRNA conjugate 56-day SNL analgesia (bioRxiv 2026, preprint); Zhao/Pain 2017 IT-ASO pharmacodynamics (doi:10.1097/j.pain.0000000000001074); Dovepress JPR 2023 SCN9A-targeting review |
| 8 | Waxman Cummins Nav1.7 SCN9A erythromelalgia inherited pain reviews | 2004–2019 | Drenth & Waxman JCI 2007;117:3603; Dib-Hajj/Cummins/Black/Waxman Annu Rev Neurosci 2010;33:325; Dib-Hajj & Waxman Annu Rev Neurosci 2019;42:87; Waxman Trends Pharmacol Sci 2013 "Painful Na-channelopathies"; GeneReviews NBK1163 |
| 9 | Cav3.2 O-GlcNAc hexosamine pathway verification query | — | No direct O-GlcNAc-transferase→Cav3.2 paper found; documented chemistry = hexosamine flux feeding N-glycan/sialic-acid chains on Asn192/Asn1466 (Keeling Loyola thesis; Orestes 2013; Weiss Pflügers Arch 2013) |
| 10 | ACD440 topical TRPV1 antagonist gel phase II verification | 2023–2025 | AlzeCure Phase 2a completed (NCT05416931, n=14); published Scand J Pain 2025 (PMID 40711349): ~50% reduction of 40 °C thermoroller-evoked pain in heat-hyperalgesic patients, period-1 analysis only |

## Findings vs Existing Claims

### F6.1: Suzetrigine validates peripheral Nav1.8 blockade in humans — but relief is partial and not superior to hydrocodone/APAP
- **Evidence:** Two Phase 3 RCTs (abdominoplasty n=1,118; bunionectomy n=1,073) met primary endpoints vs placebo (SPID48 differences 48.4 and 29.3), but failed the key secondary of superiority over hydrocodone/acetaminophen; early post-dosing non-separation at bunionectomy attributed to residual ropivacaine co-blockade [Bertoch et al., Anesthesiology 142(6):1085–1099, 2025, PMID 40117446; https://pubmed.ncbi.nlm.nih.gov/40117446/]. Suzetrigine is ~31,000-fold selective for Nav1.8 [Osteen et al., Pain Ther 14:655–674, 2025].
- **Relation to KB:** nav1.7-1.8.md §6.1 table ("FDA-approved 2025 for acute pain") → SUPPORTS (now with full Phase 3 data); QC-0088 (target-occupancy/translation difficulty) → SUPPORTS (partial responder rates 30–70% even with >99% Nav1.8 occupancy).

### F6.2: Human DRG physiology explains partial Nav1.8-blocker efficacy — Nav1.7 still initiates action potentials under suzetrigine
- **Evidence:** At clinically relevant concentrations suzetrigine reduces AP amplitude/width in human DRG neurons but has minimal effect on AP threshold/upstroke velocity, implicating Nav1.7 in AP initiation; ~35% of nociceptive neurons retain substantial excitability after calibrated removal of 25–50% of Nav1.8 conductance (dynamic clamp modeling inherited erythromelalgia GOF) [Stewart et al., PNAS 122:e2503570122, 2025; Vasylyev, Zhao, Schulman & Waxman, J Gen Physiol 156:e202413596, 2024, doi:10.1085/jgp.202413596]. A PNAS commentary argues multi-channel cotargeting as the path forward ["Inhibiting Nav1.8 for pain: lessons from patients and from neurons", PMC12232689, 2025].
- **Relation to KB:** nav1.7-1.8.md §3.1 (functional redundancy among Nav isoforms) → SUPPORTS/EXTENDS (human-cell quantitative anchor; supports the KB's multi-target ANP-230 rationale).

### F6.3: The TRPV1 hyperthermia problem now has a structural solution — biased allosterism at the S4–S5 linker
- **Evidence:** Four antagonists compared across Trpv1+/+/−/−/T634A mice show CBT disturbance is unrelated to proton-mode block; hyperthermic (AMG517/AMG9810) vs thermoneutral (SB366791/SB705498) antagonists differ by S4–S5-linker/TRP-box contacts in the vanilloid pocket; PSFL2874, designed to avoid S4–S5 engagement, is analgesic without altering core body temperature [Neuron 112(11):1815–1831.e4, June 2024, PII S0896-6273(24)00126-0]. Meta-analysis of human trials: polymodal antagonists (ABT-102, AZD1386, V116517) raise temperature; mode-selective NEO6860 does not; in humans TRPV1 mediates both pH and thermal signals to thermoregulation [Romanovsky lab, PMID 31926897]. Human genetics converge: rare TRPV1 K710N reduces capsaicin sensitivity without affecting heat sensitivity/thermoregulation, and the membrane-permeable peptide V1-cal targeting that region reverses nerve-injury hyperalgesia in mice without hyperthermia [JCI 2023 commentary, PMC9888373, and He/Zambelli et al. + Katz/Zaguri et al. companion papers, J Clin Invest 2023].
- **Relation to KB:** TRPV1.md "hyperthermia problem" section (unnumbered context for QC-0058..QC-0061) → SUPPORTS (problem reconfirmed) + NEW_MECHANISM (biased allosterism decoupling nociception from thermoregulation) + NOVEL_TARGET (PSFL2874 chemotype; V1-cal/K710-site peptides).

### F6.4: ACD440 Phase 2a verified — significant thermal-hyperalgesia benefit but small n, period effect, primary endpoint missed
- **Evidence:** Randomized double-blind crossover (n=14, NCT05416931): ACD440 Gel reduced 40 °C thermoroller-evoked pain ~50% (median 6→1.5 vs placebo 4→5, p=0.029 in prespecified period-1 analysis); no effect on brush allodynia/mechanical hyperalgesia; no treatment-related adverse events; primary endpoint (most-sensitive-quality evoked pain) was NOT met due to a significant period effect [Scand J Pain 2025, PMID 40711349; https://clinicaltrials.gov/study/NCT05416931].
- **Relation to KB:** QC-0061 (ACD440 ~50% reduction of temperature-evoked pain, "clinically relevant") → SUPPORTS with caveats (figure matches; add qualifiers: n=14, post-hoc-style period-1 analysis, thermal-only benefit). QC-0059/QC-0060 (Qutenza capsaicin patch, ~30% pain-score reduction vs low-dose control) → consistent with retrieved trial literature background; unchanged.

### F6.5: Cav3.2 diabetic sensitization confirmed — but the chemical modification is N-glycosylation/sialylation, not O-GlcNAc per se
- **Evidence:** Hyperglycemia-driven hexosamine-pathway flux feeds UDP-GlcNAc into N-glycan/sialic-acid chains on Cav3.2; functional studies manipulate this with neuraminidase (desialylation) and PNGase, identifying Asn192 (surface expression) and Asn1466 (conductance/activity) as key sites; NEU completely reverses thermal/mechanical hyperalgesia in ob/ob mice without affecting healthy animals [Orestes et al., Diabetes 62:3828–3838, 2013, doi:10.2337/db13-0337]; type-1 STZ model concordant [Joksimovic et al., Front Cell Neurosci 14:605312, 2020]; new 2025 work extends Cav3.2 N-glycosylation contribution to mechanical allodynia in myelinated A-fiber DRG neurons [Liao et al., J Shanghai Jiao Tong Univ (Med Sci) 45(11):1458, 2025]. No publication found showing direct O-GlcNAc transferase modification of Cav3.2 or an OGT-inhibitor reversal of diabetic hyperalgesia.
- **Relation to KB:** cav3.2.md §2 "O-GlcNAc modification… inhibition of O-GlcNAc transferase reverses diabetic hyperalgesia" → CONTRADICTS as stated (chemistry refinement required: N-glycosylation/sialylation via hexosamine pathway; intervention evidence is neuraminidase/PNGase, not OGT inhibitors). QC-0070 (intrathecal Cav3.2-specific knockdown gives sustained analgesia) → SUPPORTS (in vivo antisense/ODN silencing alleviates STZ-rat hyperalgesia [Messinger et al., Pain 145:184–195, 2009]; duration claim consistent with ASO pharmacodynamics). EXTENDS: peripherally restricted T-type blocker ABT-639 failed Phase II in painful diabetic neuropathy despite robust preclinical efficacy — possibly because human DRG expresses less T-type current than rodents [Mol Brain 19:34, 2022, doi:10.1186/s13041-022-00923-w; Front Pain Res 3:869735, 2022] — reinforcing cav3.2.md's translation-caution section.

### F6.6: Rbfox1–NrCAM exon-10 splicing axis independently confirmed end-to-end
- **Evidence:** SNL decreases neuronal Rbfox1 in injured DRG; AAV5-Rbfox1 restoration mitigates hypersensitivity whereas AAV-shRNA mimicry induces allodynia/thermal sensitivity/spontaneous pain; Rbfox1 binds the (U)GCAUG motif downstream of Nrcam exon 10 (CLIP/qPCR) and its loss shifts splicing toward L-Nrcam; a splice-blocking ASO against the long isoform partially reverses SNL allodynia/hyperalgesia within 72 h [He et al., Neurotherapeutics 20(4):e00309, 2023, doi:10.1016/j.neurot.2023.e00309, PMID 38241164]. The precursor study mapped SNL-induced Nrcam+10 gain and showed intrathecal/DRG-microinjected exon-10 ASO attenuates SNL and CCD pain in both sexes [Liang, Wu, Lin, Chang & Tao, J Pain 21:625.e1–625.e14, 2020, doi:10.1016/j.jpain.2019.12.004, PMID 31917219].
- **Relation to KB:** EC-0103, EC-0104, EC-0105, QC-0091 → SUPPORTS (all four elements match the primary literature almost verbatim, including the 72-hour ASO figure). EC-0103's pleiotropy rationale → SUPPORTS (commentary stresses Rbfox1 regulates hundreds of transcripts; global targeting deemed unlikely therapeutic [Neurotherapeutics editorial, 2024, S1878-7479(24)00001-1]).

### F6.7: MAJOR — DRGX literature shows the OPPOSITE polarity to the KB dossier
- **Evidence:** After adult SNL, DRGX expression DECREASES in small/medium DRG neurons; AAV-shRNA knockdown of DRGX alone INDUCES mechanical allodynia and thermal hyperalgesia; AAV-DRGX overexpression SUPPRESSES maintenance-phase neuropathic pain; mechanistically DRGX restrains MMP-9 (overexpression blocks SNL-induced MMP-9 upregulation, MMP-9 inhibitor rescues knockdown-induced pain; EP2 upregulation was not rescued) [Mol Pain 16:33, 2020, doi:10.1177/1744806920904462, PMC7099666]. Developmental landmarks confirm the opposite pole of the same factor: Drg11-null mice die perinatally with defective nociceptor projection patterning and REDUCED acute pain responses (developmental, not therapeutic) [Chen et al., Neuron 2001, via OMIM 606701; Regadas et al. 2013].
- **Relation to KB:** EC-0031 (DRGX rationale_for BDNF–TrkB–KCC2 cascade), EC-0034 (rationale_for pronociceptive ion channels incl. claimed SCN9A/SCN10A/TRPV1 transactivation), EC-0032 (central sensitization maintenance via persistent/upregulated DRGX), EC-0033 (DRGX-knockdown ASO therapy) → CONTRADICTS. No evidence surfaced for: injury-induced DRGX activation/maintained expression; DRGX-driven Nav/TRPV1/CGRP/BDNF battery; pronociceptive DRGX overexpression; analgesic DRGX ASO/shRNA knockdown; electroacupuncture lowering DRGX. Retrieved literature supports the inverse graph: DRGX loss-of-function (post-developmental) → MMP-9 derepression → microglial activation → pain. Note the cross-theme implication: DRGX sits upstream of Theme 2's MMP-9 node.

### F6.8: ZFHX2/Marsili syndrome is real human genetic validation — but the KB mechanism details do not match the source
- **Evidence:** One Italian kindred (six affected members, autosomal dominant, "Marsili syndrome"): heterozygous ZFHX2 p.R1913K (homeodomain arginine-57 equivalent) segregates with hyposensitivity to noxious heat/capsaicin and painless fractures; BAC-transgenic mice carrying orthologous R1907K have elevated heat-pain thresholds with dose-copy dependence; CRITICAL NUANCE: Zfhx2-null mice are HYPERSENSITIVE to noxious heat (not hyposensitive) yet show impaired Randall-Selitto noxious-mechanical responses; downstream deregulated genes identified were SST (upregulated), PTGIR (↓2.4-fold), GFRA3 (↓), GAL (most downregulated), Fam89a, with ChIP-seq AG-rich motif upstream of neuropeptide-signalling genes — explicitly NOT linked to SCN9A/SCN10A/TRPV1/CALCA/BDNF regulation [Habib, Matsuyama, Okorokov, Santana-Varela, … Wood & Cox, Brain 141(2):365–376, 2018, doi:10.1093/brain/awx326, PMID 29253101; OMIM #147430]. No neuropathic-pain (SNI/CCI/SNL) ZFHX2 study, no ZFHX2-ASO/siRNA therapy study, and no electroacupuncture/rTMS-ZFHX2 study surfaced in any database searched.
- **Relation to KB:** ZFHX2.md core premise (transcription factor whose mutation confers congenital hypoalgesia → candidate target) → SUPPORTS (human genetics real). But: EC-0131 (ZFHX2 drives BDNF–TrkB–KCC2 cascade) → CONTRADICTS/UNSUPPORTED (BDNF absent from ZFHX2 regulome; null mouse is heat-HYPERsensitive, opposite of a clean analgesic LOF); EC-0133 (ZFHX2 directly activates Nav1.7/Nav1.8/TRPV1/TRPA1/CGRP) → CONTRADICTS (regulome is SST/PTGIR/GFRA3/GAL); EC-0132 (injury-upregulated ZFHX2 maintains central sensitization) → UNSUPPORTED (no SNI/CCI/SNL data found); EC-0134 (ZFHX2 ASO therapy) → UNSUPPORTED (no preclinical ASO literature found). Also note: the human mutation is an inherited dominant missense (possible altered-function/gain-of-function, single family), not "rare de novo mutations" nor LOF.

### F6.9: SCN9A-targeting oligonucleotides are advancing fast preclinically — still zero clinical trials
- **Evidence:** Intrathecal ASOs reach all DRG neuronal populations, spare basal sensation, and Nav1.7-ASOs give up to ~4 weeks analgesia in rodents [Zhao?/Ionis-lineage study, Pain 158:xxx, 2017, doi:10.1097/j.pain.0000000000001074]; ATL-301 divalent siRNA produces dose-dependent, >3-month analgesia after a single intrathecal dose with clean ion-channel selectivity [Alnylam-lineage poster TH699, IASP World Congress on Pain 2024, https://posters.worldcongress2024.org/poster/TH699]; ASO-siRNA conjugate N02C0702 achieves ~80% durable SCN9A knockdown and up-to-56-day SNL analgesia exceeding suzetrigine/pregabalin comparators (PREPRINT — not peer-reviewed) [bioRxiv 2026.03.27.714734]; Quiver Bioscience holds NIH UG3/UH3 UG3NS146009 to advance lead ASO QV-2421 through IND-enabling toward a first Phase I in young-adult erythromelalgia patients [HHS TAGGS award record]. No SCN9A-ASO clinical trial is registered as of sweep date.
- **Relation to KB:** nav1.7-1.8.md §5.3 (siRNA/gene silencing preclinical) → SUPPORTS/EXTENDS (now di-siRNA and conjugate modalities with months-long durations; named programs ATL-301, QV-2421). Any inference that SCN9A ASOs are clinically testable today would be premature — flag as EXTENDS with status caveat.

## New Candidate Nodes/Edges for Graph
- **Suzetrigine (VX-548/Journavx)** —[selectively inhibits]→ Nav1.8 (sign −1); edge: —[approved for acute pain 2025]— ; chronic/neuropathic extension ongoing.
- **Nav1.8** —[contributes AP upstroke; Nav1.7 retains threshold role under blockade]→ partial-analgesia ceiling (edge supported by PNAS 2025/JGP 2024).
- **PSFL2874** —[antagonizes TRPV1 without hyperthermia via S4–S5-linker avoidance]→ inflammatory pain relief (NOVEL_TARGET).
- **TRPV1 S4–S5 linker biased-allosterism** —[mediates]→ antagonist-induced hyperthermia (NEW_MECHANISM node).
- **V1-cal peptide / TRPV1 K710 region** —[reverses neuropathic hyperalgesia without CBT change]→ analgesia (preclinical).
- **Human TRPV1 variants K710N, N331K** — nodes anchoring human genetics of thermo-nociception.
- **ACD440 (topical TRPV1 antagonist gel)** —[Phase 2a: reduces thermally evoked pain in heat-hyperalgesic PNP patients]— (already in KB; add trial-ID qualifier NCT05416931).
- **Cav3.2 Asn192/Asn1466 N-glycosylation sites** —[hyperglycemia/hexosamine-dependent sialylation increases]→ channel surface expression & conductance (corrected chemistry replacing "O-GlcNAc" framing).
- **Neuraminidase (NEU)** —[desialylates Cav3.2, reverses]→ diabetic hyperalgesia (ob/ob, STZ models).
- **GM1 ganglioside** —[tonically inhibits]→ Cav3.2; lost in hyperglycemia (secondary modulator).
- **DRGX downregulation (adult DRG)** —[derepresses]→ MMP-9 transcription —[drives]→ spinal microglial activation/neuropathic pain (polarity-INVERTED replacement edges; links Theme 2 MMP-9 cluster).
- **EP2/PTGER2** —[upregulated after SNL independent of DRGX rescue]→ cAMP/PKA pronociceptive drive.
- **ATL-301 (di-siRNA)**, **QV-2421 (ASO)**, **N02C0702 (ASO-siRNA conjugate)** —[knock down SCN9A → months-long analgesia in rodents]— (preclinical pipeline nodes; N02C0702 flagged unreviewed).
- **ZFHX2-regulated gene set (corrected): SST ↑, PTGIR ↓, GFRA3 ↓, GAL ↓** — replaces the unsupported Nav/TRPV1/CGRP/BDNF battery.
- **Zfhx2-null heat HYPERsensitivity** edge (sign flip vs KB expectation) — guards against naive "LOF = analgesia" modelling.

## Contradictions & Contested Areas
1. **DRGX polarity inversion (highest severity):** KB dossier claims sustained/upregulated pronociceptive DRGX with analgesic knockdown; the only substantive adult-injury study reports decreased DRGX after SNL, pain-inducing knockdown, and pain-suppressing overexpression (F6.7). All four DRGX claims need re-scoping or sign inversion.
2. **ZFHX2 regulome mismatch:** KB asserts direct Nav1.7/Nav1.8/TRPV1/TRPA1/CGRP/BDNF transactivation; source human-genetics paper identifies SST/PTGIR/GFRA3/GAL and shows Zfhx2-null heat hypersensitivity (F6.8). The "higher-leverage than single-channel targets" argument currently rests on fabricated-looking specifics.
3. **Cav3.2 glycosylation chemistry:** "O-GlcNAc modification + OGT inhibitor reverses hyperalgesia" is unsupported; documented mechanism is hexosamine-fed N-glycan/sialylation manipulated by neuraminidase/PNGase (F6.5).
4. **Rbfox1 binding-direction paradox:** Neurotherapeutics commentary notes canonical Rbfox1-downstream binding promotes exon exclusion while the reported data direction remains debated; behavioral rescue is incomplete even with normalized splice ratios; EGFR-link hypothesis for L-NrCAM remains unproven (consistent with KB's own caution).
5. **Suzetrigine ceiling effects:** not superior to hydrocodone/APAP on key secondary endpoints; ropivacaine interaction at bunionectomy; 30–70% responder heterogeneity — tempers the "first-in-class success" narrative.
6. **ACD440 primary endpoint missed** (period effect; n=14); efficacy confined to thermally evoked pain — precision-medicine scoping needed before generalizing QC-0061.
7. **Peripherally-restricted T-type blockade may be insufficient in humans** (ABT-639 Phase II failure; possible low human DRG T-type density vs rodents) — qualifies optimistic Cav3.2 ASO/blocker translation.

## Landmark Classics Reconfirmed
- Cummins TR, Dib-Hajj SD, Waxman SG. Electrophysiological properties of mutant Nav1.7 sodium channels in a painful inherited neuropathy. J Neurosci 24:8232–8236, 2004.
- Drenth JPH & Waxman SG. Mutations in sodium-channel gene SCN9A cause a spectrum of human genetic pain disorders. J Clin Invest 117:3603–3609, 2007.
- Dib-Hajj SD, Cummins TR, Black JA, Waxman SG. Sodium channels in normal and pathological pain. Annu Rev Neurosci 33:325–347, 2010.
- Dib-Hajj SD & Waxman SG. Sodium channels in human pain disorders: genetics and pharmacogenomics. Annu Rev Neurosci 42:87–106, 2019.
- Waxman SG. Painful Na-channelopathies: an expanding universe. Trends Pharmacol Sci 34(9-10), 2013.
- Hisama FM, Dib-Hajj SD, Waxman SG. SCN9A Neuropathic Pain Syndromes. GeneReviews, NBK1163 (EM/PEPD/SFN triad; GOF vs recessive LOF-CIP).
- Cox et al. 2006 (SCN9A CIP) and Fertleman et al. 2006/2007 (PEPD) — reconfirmed as anchors within GeneReviews/Drenth-Waxman.
- Chen AI et al. 2001 Neuron (Drg11/Drgx-null nociceptive projection defects) and Regadas et al. 2013 (nociceptive glutamatergic spinal differentiation) — via OMIM 606701.
- Habib AM et al. Brain 2018 (ZFHX2/Marsili syndrome) — the foundational human validation for ZFHX2.
- Orestes P et al. Diabetes 2013 and Messinger RB et al. Pain 2009 — foundational Cav3.2-glycosylation/in-vivo-silencing pair.

## References
- Bertoch T, et al. Anesthesiology 142(6):1085–1099, 2025. PMID 40117446.
- Stewart RG, et al. Proc Natl Acad Sci USA 122:e2503570122, 2025.
- Vasylyev DV, Zhao P, Schulman BR, Waxman SG. J Gen Physiol 156:e202413596, 2024. doi:10.1085/jgp.202413596.
- Osteen JD, et al. Pain Ther 14:655–674, 2025.
- "Inhibiting Nav1.8 for pain: lessons from patients and from neurons." PNAS commentary, 2025. PMC12232689.
- TRPV1-biased allosterism. Neuron 112(11):1815–1831.e4, 2024. PII S0896-6273(24)00126-0.
- Hyperthermia meta-analysis/modeling. PMID 31926897 (Temperature, 2020).
- Human TRPV1 K710N/V1-cal and N331K papers + JCI commentary, J Clin Invest 2023. PMC9888373.
- Reimer M(?), et al. Scand J Pain, 2025. PMID 40711349; NCT05416931.
- Orestes P, et al. Diabetes 62(11):3828–3838, 2013. PMC3806612.
- Joksimovic SL, et al. Front Cell Neurosci 14:605312, 2020.
- Liao C, et al. J Shanghai Jiao Tong Univ (Med Sci) 45(11):1458, 2025. doi:10.3969/j.issn.1674-8115.2025.11.005.
- Central/peripheral T-type channels in pain. Mol Brain 15:34(?), 2022. doi:10.1186/s13041-022-00923-w.
- PDN ion-channel mechanisms review. Front Pain Res 3:869735, 2022. doi:10.3389/fpain.2022.869735.
- Keeling GM. Loyola thesis (hexosamine→N-glycan/sialic acid chemistry of Cav3.2). ecommons.luc.edu.
- Messinger RB, et al. Pain 145:184–195, 2009.
- He L, Guo H, Wang H, et al. Neurotherapeutics 20:e00309, 2023. doi:10.1016/j.neurot.2023.e00309. PMID 38241164.
- Liang L, Wu S, Lin C, Chang Y-J, Tao Y-X. J Pain 21:625, 2020. doi:10.1016/j.jpain.2019.12.004. PMID 31917219.
- Neurotherapeutics editorial commentary, 2024. S1878-7479(24)00001-1.
- DRGX downregulation study. Mol Pain 16:33, 2020. doi:10.1177/1744806920904462. PMC7099666.
- OMIM 606701 (DRGX/DRG11); OMIM #147430 (Marsili syndrome).
- Habib AM, Matsuyama A, Okorokov AL, et al. Brain 141(2):365–376, 2018. doi:10.1093/brain/awx326. PMID 29253101.
- Matsuyama A. UCL thesis (Novel analgesic drug targets; Zfhx2-null phenotypes). discovery.ucl.ac.uk.
- Pain 2017 ASO pharmacodynamics. doi:10.1097/j.pain.0000000000001074.
- ATL-301 poster TH699, IASP World Congress on Pain 2024.
- N02C0702 ASO-siRNA conjugate. bioRxiv 2026.03.27.714734 (PREPRINT).
- Quiver Bioscience NIH award UG3NS146009. taggs.hhs.gov.
- Dormer A, et al. J Pain Res 2023 (SCN9A/Nav1.7 therapeutic targeting review). dovepress.com.
- NCT06420765 (Vertex microneurography VX-150/993/548); NCT07511400 (Vienna NaV1.8 microdosing); NCT05416931 (ACD440).
- Dib-Hajj & Waxman. Annu Rev Neurosci 42:87–106, 2019; Dib-Hajj, Cummins, Black & Waxman. Annu Rev Neurosci 33:325–347, 2010; Drenth & Waxman. J Clin Invest 117:3603–3609, 2007; GeneReviews NBK1163.

## Sweep Limitations
- **QC-0032 (GM-CSF/TRPV1+ nociceptor colocalization controversy) was not specifically re-searched** this sweep (assigned to the immune-theme dossier); carried forward unverified here.
- **TRPV1 "resensitization"** (agonist-washout recovery kinetics) was not separately queried; the hyperthermia/desensitization axis dominated results. No contradiction surfaced for KB desensitisation claims.
- **DRGX and ZFHX2 searches returned sparse primary literature overall** (essentially one key paper each for adult pain relevance); absence of evidence for KB sub-claims (ASO therapies, electroacupuncture/rTMS modulation, conditional-KO neuropathic models) is therefore strong-but-not-exhaustive negative evidence — targeted PubMed/CTR verification recommended before deleting those graph edges.
- **Two sources are non-peer-reviewed**: N02C0702 bioRxiv preprint (2026) and the ATL-301 congress poster; company-stage programs (Quiver QV-2421) are award-record based.
- Some quantitative details (e.g., QC-0070's "7–10 days" Cav3.2 ASO duration; QC-0057's exact TRPV1 neuron percentages) were consistent with the retrieved literature family but not matched to a single primary table; retained as SUPPORTS-with-confidence-note rather than verified verbatim.
- Author lists were unavailable in retrieved records for two cited items (DRGX Mol Pain 2020; Pain 2017 ASO pharmacodynamics); cited by DOI/PMC instead.
