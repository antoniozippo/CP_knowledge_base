import json, collections

def v(cid, verdict, rationale, refs, cites, qual=None):
    return {"claim_id": cid, "verdict": verdict, "rationale": rationale,
            "evidence_refs": refs, "citations": cites, "qualifier": qual}

E = []
def add(cid, verdict, rationale, refs, cites, qual=None):
    E.append(v(cid, verdict, rationale, refs, cites, qual))

C="CONFIRMED"; EX="EXTENDED"; RF="REFUTED"; MX="MIXED"; NE="NO_EVIDENCE_FOUND"; UR="UNREVIEWED"

# ---------------- EDGE CLAIMS ----------------
add("EC-0001",C,"ANA-12 blocks TrkB-driven pronociceptive plasticity consistent with rACC/spinal TrkB-blockade literature.",
    ["theme_10#F10.5"],["Cazorla et al. 2011 line (via ana-12.md); Li TT et al. 2022, Brain Res Bull"])
add("EC-0002",NE,"No retrieved source corroborates an ANA-12->NLRP3 inhibitory edge; NLRP3 itself is a validated but model-dependent pronociceptive node.",
    ["theme_03#F3.4","theme_03#F3.5"],["Curto-Reyes et al. 2015 (tabulated, Front Physiol); Zhang et al. 2026, Sci Rep"],
    "NLRP3 necessity model-dependent (null in SNI; positive in CCI/DNP/cancer/EAE)")
add("EC-0003",C,"ANA-12 inhibition of neuropathic TrkB signaling matches published ANA-12/cyclotraxin-B pharmacology and usage.",
    ["theme_10#F10.5"],["Li TT et al. 2022, Brain Res Bull; Br J Anaesth 2025 (P2X4R-BDNF-TrkB)"])
add("EC-0004",NE,"General ANA-12 TrkB pharmacology validated but the truncated-isoform (TrkB.T1) interaction specifically was not resurfaced.",
    ["theme_10#F10.5"],["Cazorla et al. 2011 line (via ana-12.md)"],"TrkB.T1-selective binding unaddressed")
add("EC-0005",C,"TrkB-blockade preservation of KCC2 is anchored in rodent and human dorsal-horn tissue showing BDNF-TrKB drives membrane KCC2 loss.",
    ["theme_01#F1.3","theme_01#F1.4"],["Davis et al. 2025, bioRxiv/PMID 40667986; Dedek et al. 2019, Brain 142:1535"],
    "STEP61-pFyn-pGluN2B coupling is male-specific across rodent and human tissue")
add("EC-0006",C,"Ang-1 activation of Tie2 promoting endothelial quiescence/junction tightening is standard confirmed vascular biology in SCI/pain models.",
    ["theme_04#F4.6"],["Thurston-era biology; Nieswandt/Koh 2013 Trends Mol Med; Brain 2010;133:1026"])
add("EC-0007",C,"Ang-2 antagonism of Tie2 with TNF-alpha sensitization reconfirmed (Nat Med 2006 lineage) in SCI barrier work.",
    ["theme_04#F4.6"],["Rennel/Zhang-era Nat Med 2006;12:235; Acta Neuropathol Commun 2018 (sivelestat)"])
add("EC-0008",C,"Ang-2 synergy with VEGFA in vascular destabilization reconfirmed within the Ang/Tie2 SCI-pain literature.",
    ["theme_04#F4.6"],["Nat Med 2006;12:235; J Neurotrauma 2010;27:2067"])
add("EC-0009",UR,"Autophagy/apoptosis inhibitor dossier (Bcl-xL-Bax/Bak) lies outside all ten sweep themes.",
    [],[])
add("EC-0010",UR,"Bcl-xL-mPTP edge belongs to the unswept apoptosis/autophagy dossier.",
    [],[])
add("EC-0011",C,"VEGFA sequestration (bevacizumab/sFlt-1 class) relieves nerve-injury pain; strategy refined toward isoform/receptor selectivity.",
    ["theme_04#F4.7"],["Mol Pain 2022 (sFlt-1 trap); J Exp Clin Cancer Res 2021 (anti-VEGFR1 D16F7)"],
    "Blunt sequestration superseded by isoform (VEGF-Axxxa/xxxb) and receptor-selective approaches")
add("EC-0012",C,"Repair-versus-delivery barrier rationale supported at BBB/BSCB and mirrored at the blood-nerve barrier (perineurium).",
    ["theme_04#F4.5","theme_04#F4.8"],["Montague-Cardoso & Malcangio 2021, Pain Rep; PNAS 2012 (perineurial opening)"],
    "New compartment added: perineurial/BNB (claudin-1/-5, occludin)")
add("EC-0013",EX,"BSCB disruption in neuropathic pain is well supported preclinically but model-heterogeneous and often transient.",
    ["theme_04#F4.5"],["Beggs et al. 2010, Mol Pain 6:74; Montague-Cardoso & Malcangio 2021, Pain Rep"],
    "Leaks peak 24-48h and often resolve by day 7-14; SNI infiltration weak by lineage tracing; predicate direction appears inverted (Ang-2 disrupts barrier) - fix encoding")
add("EC-0014",EX,"SPM (RvD1/LXA4) pro-resolution role is mainstream and multiply replicated; direct barrier-resealing data remain thin.",
    ["theme_08#F8.1","theme_08#F8.2","theme_08#F8.3","theme_08#F8.4","theme_04#F4.5"],
    ["Wang YH et al. 2022, Neuroscience 494:12; Eur J Med Res 2025;30:189; Ji 2023 Annu Rev Pharmacol Toxicol"],
    "Barrier-resealing framing is a specific instance of the general resolution program; no approved resolvin drug; precursor supplementation weak/null")
add("EC-0015",C,"Ang-1 stabilization of barrier integrity reconfirmed by IV Ang-1 rescue of BSCB permeability after SCI.",
    ["theme_04#F4.6"],["Brain 2010;133:1026; J Neurotrauma 2010;27:2067"])
add("EC-0016",C,"BDNF activation of full-length TrkB is directly shown in rACC aversion circuits and canonical receptor biology.",
    ["theme_10#F10.4"],["Li TT et al. 2022, Brain Res Bull; Mol Brain 2021 (NB001-blockable enhancement)"])
add("EC-0017",EX,"Microglial/BDNF-TrkB disruption of KCC2-dependent inhibition is strongly supported and extended by a peripheral (DRG-KCC2) arm.",
    ["theme_01#F1.4","theme_01#F1.10","theme_01#F1.5","theme_01#F1.14","theme_03#F3.13"],
    ["Coull et al. 2005, Nature 438:1017; Mol Pain 19 (2023); Xian et al. 2025, Cell Biosci 15:12"],
    "Pathogenic in chronic dorsal-horn pain states (human-tissue anchored); early post-lesion downregulation can be adaptive in motor circuits; microglial P2X4-BDNF questioned and IRF5/P2X4 male-specific")
add("EC-0018",C,"BDNF feeding the IL-6/gp130/JAK2 hub matches current consensus network framing of pronociceptive transcription.",
    ["theme_09#F9.10"],["Tsuda et al. 2011, Brain 134:1127; Aging Dis 2024;15:186 (review)"])
add("EC-0019",NE,"The BDNF-induces-TNF release edge did not surface in any sweep; adjacent microglial BDNF/P2X4 pathway is itself contested.",
    ["theme_03#F3.13"],["Malcangio 2018 viewpoint PMC6148335"],
    "P2X4-BDNF microglial controversy; IRF5/P2X4 dependence is male-specific")
add("EC-0020",C,"BDNF-TrkB promotion of synaptic-plasticity protein programs (NR2B/pERK/pCREB) directly shown in rACC and spinal preparations.",
    ["theme_10#F10.8","theme_10#F10.4"],["Li TT et al. 2022, Brain Res Bull; Katano et al. 2011, Neuropharmacology"])
add("EC-0021",C,"Dual pro-/anti-nociceptive BDNF roles vindicated: pronociceptive via TrkB-NR2B-ERK in ACC, context-dependent ligand/receptor effects elsewhere.",
    ["theme_10#F10.4"],["Li TT et al. 2022, Brain Res Bull; psilocybin-review counter-note (cortical BDNF facilitatory)"],
    "Valence depends on ligand form (pro- vs mature-BDNF), region, and receptor complex")
add("EC-0022",C,"TrkB-Fc/cyclotraxin-B sequestration of BDNF reduces pain affect; tool biology supported despite inverted predicate wording.",
    ["theme_10#F10.4"],["Li TT et al. 2022, Brain Res Bull (cyclotraxin-B)"],
    "Predicate inverted in card (should read TrkB-Fc sequesters BDNF)")
add("EC-0023",NE,"Card predicate is malformed (release of a receptor); underlying BDNF-glial VEGF/VEGFR coupling is plausible-supported but the stated edge is unusable.",
    ["theme_04#F4.7"],["Theme 4 Contradictions #5 (data-quality flag)"],
    "Fix direction/source rather than delete; likely intended BDNF-glial VEGFR2 upregulation")
add("EC-0024",C,"BDNF-linked HIF1alpha-driven glycolytic shift in myeloid cells validated and extended beyond microglia to DRG macrophages and neurons.",
    ["theme_04#F4.1"],["Wang S et al. 2023, Glia (HK2, PMID 37909251); PRMT6-HIF1alpha Pain Res Forum 2024/25"],
    "Upstream regulators PRMT6/Lyn-IRF5/HK2/FGF4 newly identified above the HIF1alpha node")
add("EC-0025",NE,"PV dysfunction is strongly supported but the specific CP-AMPAR-mediated excitotoxic-death mechanism was not probed; theme internally inconsistent (F1.6 lists claim, Limitations say untouched).",
    ["theme_01#F1.6"],["Qiu et al. 2024, PNAS; Rankin et al. 2024, Cell Rep"],
    "Internal inconsistency flagged: F1.6 SUPPORTS mapping vs theme_01 Limitations 'left untouched'")
add("EC-0026",NE,"FK506-calcineurin enzymology is canonical but card direction inverted and the ACC-Kal7 degradation loop it serves has no retrievable primary source.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],
    "Part of unsupported ACC Kalirin-7 narrative; recommend demotion to hypothesis")
add("EC-0027",C,"Calpain cleavage of KCC2 impairing chloride homeostasis is directly documented in neuropathic pain and after SCI.",
    ["theme_01#F1.11"],["Zhou et al. 2012, J Biol Chem (via Lee-Hotta 2019, Neurochem Int); Aix-Marseille thesis 2018"])
add("EC-0028",UR,"ER-stress/UPR arm of the caspase cascade sits in the unswept GABA_apoptosis dossier.",
    [],[])
add("EC-0029",UR,"Closed-loop neuromodulation/Neuropixels meta-claim from skill notes outside all ten themes.",
    [],[])
add("EC-0030",C,"Cofilin-mediated actin depolymerization is core, well-replicated cytoskeletal biology used across NgR1/TRPV1 and Kal7 pathways.",
    ["theme_05#F5.3","theme_10#F10.1"],["Li Y et al. 2014, Sci Signal 7:ra61; Penzes et al. 2008, Trends Neurosci"])
add("EC-0031",RF,"Adjudicated: DRGX is anti-nociceptive post-development (down after SNL; knockdown induces pain); no DRGX-to-BDNF-TrkB-KCC2 link exists - KB polarity inverted.",
    ["theme_06#F6.7","theme_01#F1.5"],["Ito T et al. 2020, Mol Pain 16:33 (PMC7099666; adjudicated via websearch)","Chen et al. 2001, Neuron (Drg11 development)"],
    "Replace with inverted edges: DRGX loss-of-function derepresses MMP-9 -> pain; nociceptor-localized KCC2 suppresses BDNF release (peripheral arm)")
add("EC-0032",RF,"DRGX overexpression suppresses maintenance-phase central sensitization - the claimed pronociceptive rationale is opposite to evidence.",
    ["theme_06#F6.7"],["Ito T et al. 2020, Mol Pain 16:33 (adjudicated)"],
    "Invert sign: DRGX restoration alleviates; downregulation maintains sensitization")
add("EC-0033",RF,"A DRGX antisense/knockdown therapy would be predicted to worsen pain; the therapeutic direction is inverted.",
    ["theme_06#F6.7"],["Ito T et al. 2020, Mol Pain 16:33 (adjudicated)"],
    "Testable direction is DRGX restoration (AAV overexpression), not knockdown")
add("EC-0034",RF,"No SCN9A/SCN10A/TRPV1 transactivation battery exists; only MMP-9 restraint demonstrated (EP2 not rescued by DRGX).",
    ["theme_06#F6.7"],["Ito T et al. 2020, Mol Pain 16:33 (adjudicated)"],
    "Corrected regulome: MMP-9 (rescued), EP2/PTGER2 (not rescued)")
add("EC-0035",C,"Calpain activation downstream of calcium overload and its cleavage of KCC2 are experimentally supported; upstream cascade framing comes from an unswept dossier.",
    ["theme_01#F1.11"],["Zhou et al. 2012, J Biol Chem; Lee-Hotta et al. 2019, Neurochem Int"],
    "Calpain-to-KCC2 arm directly evidenced; 'GABAergic Ca2+ Overload Cascade' node itself unvalidated")
add("EC-0036",UR,"Cascade-to-mPTP edge resides in the unswept GABA_apoptosis dossier.",
    [],[])
add("EC-0037",UR,"Cascade-to-CP-AMPAR edge resides in the unswept GABA_apoptosis dossier.",
    [],[])
add("EC-0038",C,"YC-1 destabilizes/inhibits HIF1 transcriptional activity (card inverted) and carries a concrete safety red flag.",
    ["theme_04#F4.3"],["Selleck compilation (HeLa HRE IC50 ~1.2 uM); PMC3218033 (stroke worsening)"],
    "YC-1 increases mortality/infarct in rat stroke; no approved HIF1alpha inhibitor as of 2023")
add("EC-0039",C,"HIF1alpha transcriptional battery validated across microglia, macrophages and neurons with multiple upstream inducers identified.",
    ["theme_04#F4.1"],["Wang S et al. 2023, Glia; Wu/Chen 2026, J Headache Pain; PRMT6 entry Pain Res Forum"],
    "Cell-type scope broader than microglia; protective contexts exist (see EC-0042 qualifier)")
add("EC-0040",C,"PX-478 suppresses HIF1alpha at multiple levels including translation - mechanistic support solid, translational program absent.",
    ["theme_04#F4.3"],["Koh et al. 2008, Mol Cancer Ther 7:90; NCI Drug Dictionary"],
    "Oncology Phase I only (neutropenia DLT); no neurological/pain indication; card predicate inverted")
add("EC-0041",C,"HIF1alpha transactivation of VEGFA reconfirmed from founding hypoxia-VEGF observation through myeloid-pain work.",
    ["theme_04#F4.4"],["Shweiki et al. 1992, Nature; Cramer et al. 2003, Cell"])
add("EC-0042",EX,"Isoform/systemic-risk rationale strengthened by concrete counter-examples and bipolar HIF1alpha physiology.",
    ["theme_04#F4.3","theme_04#F4.9"],["PMC3218033 (YC-1 stroke harm); PMID 36017378 (protective mitophagy); PMID 38291291 (ferroptosis suppression)"],
    "Pan-inhibition harmful in ischemic/regenerative contexts; phase- and cell-type qualifiers required")
add("EC-0043",UR,"IGF2-NTRK1-ER-stress cascade (IGF1-2 dossier) untouched by all ten sweeps.",
    [],[])
add("EC-0044",NE,"IGF2BP2 is validated as a lactylation-driven m6A reader, but the claimed IGF2-to-IGF2BP2-mRNA-stabilization edge was never examined; possible entity conflation.",
    ["theme_09#F9.1"],["Wang Q-H et al. 2025, J Neurosci (H3K18la->Igf2bp2)"],
    "Possible IGF2 (ligand) vs IGF2BP2 (reader) conflation in KB - audit source_note")
add("EC-0045",EX,"IL-6/JAK2/STAT3 axis is a validated pronociceptive hub, but the terminal STAT3-to-KCC2 step is unproven (NKCC1 phosphorylation documented instead).",
    ["theme_01#F1.10","theme_01#F1.12","theme_09#F9.10"],["Lee et al. 2023, Exp Neurol 370:114576; Pieraut et al. 2011, J Neurosci 31:13516"],
    "Flag gap: direct STAT3->KCC2 transcriptional evidence absent; axis tied to glial activation and NKCC1")
add("EC-0046",UR,"IGF1 dual-role rationale (IGF1-2 dossier) untouched by sweeps.",
    [],[])
add("EC-0047",EX,"Baricitinib suppression of JAK/STAT3-dependent pain supported and extended by CSF-1/glial and neuronal cell-autonomous arms.",
    ["theme_09#F9.8","theme_09#F9.4","theme_09#F9.9"],["Makabe et al. 2024, Arthritis Res Ther 26:121; IJMS 2024;25:11943"],
    "BBB penetration uncertain (CNS action mainly where barrier weak); card predicate inverted (drug inhibits pathway)")
add("EC-0048",EX,"Ruxolitinib-class JAK inhibition analgesic in glial and neuronal preparations; CNS-delivery caveat applies.",
    ["theme_09#F9.4","theme_09#F9.9","theme_09#F9.10"],["Eur J Pharmacol 2024 (BV2 NF-kB/MAPK); Tsuda et al. 2011, Brain"],
    "Predicate inverted (ruxolitinib inhibits pathway); baricitinib/ruxolitinib brain exposure limited")
add("EC-0049",NE,"SOCS3 negative-feedback brake is consensus biology but the termination edge was not directly classified this round (only partial SOCS3-JAK/STAT3 hit in search log).",
    ["theme_09#F9.10"],["SOCS3-JAK/STAT3 blockade record PMC6632340 (partial)"],
    "Predicate inverted (SOCS3 terminates JAK/STAT3)")
add("EC-0050",NE,"KALRN-to-C/EBPbeta transcription edge is part of the unsupported ACC Kalirin-7 narrative; direction suspect (C/EBPbeta canonically upstream of Kalrn).",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Recommend demotion to hypothesis pending primary source")
add("EC-0051",NE,"Downstream HDAC4-represses-GAD65 effector arm is confirmed (panobinostat restores GAD65/GABA), but the KALRN-to-HDAC4-repression upstream link is unsourced.",
    ["theme_09#F9.5","theme_09#F9.12"],["Pain Reports 2024 (panobinostat/GAD65); Front Pharmacol 2025 HDAC-microglia review"],
    "miR-206-3p restrains HDAC4 post-transcriptionally; HDAC4 has dual roles in myeloid cells - avoid linear pronociceptive framing")
add("EC-0052",C,"Kalirin-7 GEF activation of Rac1 is canonical, replication-backed biology (spinal nociceptive sensitization flagship).",
    ["theme_10#F10.1"],["Nat Commun 2015 (ncomms7820); Penzes et al. 2008, Trends Neurosci"])
add("EC-0053",C,"Kalirin-7 GEF activity toward RhoG is textbook general biology within the supported Kal7 cluster.",
    ["theme_10#F10.1"],["Penzes et al. 2008, Trends Neurosci"])
add("EC-0054",NE,"AAV-Kalirin-7 ACC gene therapy has no retrievable primary source; adjudication found TIAM1 (not Kal7) as the evidenced ACC Rac1-GEF and spinal Kal7 is pronociceptive (sign-inversion risk).",
    ["theme_10#F10.1"],["Ru Q et al. 2022, J Clin Invest 132:e158545 (TIAM1-ACC); Nat Commun 2015 (spinal Kal7)"],
    "Demote to hypothesis; therapy logic may invert if generalized beyond hypothesized ACC compartment")
add("EC-0055",NE,"Calcineurin-dephosphorylation/degradation-of-Kal7 loop belongs to the unverifiable ACC narrative; card direction inverted.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Fix direction and demote pending primary source")
add("EC-0056",NE,"Kal7-via-calcineurin NMDAR-downregulation edge sits inside the unsupported ACC story; not explicitly classified by sweep.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"ACC-contextualized; treat as hypothesis")
add("EC-0057",C,"Global Kalirin knockout mouse existence and spine phenotypes rest on supported general neurobiology (KO/KD reduce spines), though not pain-model specific.",
    ["theme_10#F10.1"],["Penzes-lineage KO/KD literature (RNAi reduces spine density)"],
    "Developmental/neurobiology anchor; no chronic-pain KO phenotype retrieved")
add("EC-0058",RF,"Adjudicated: spinal injury models show Kalirin-7 recruitment/upregulation with pronociceptive function - the claimed CCI-induced downregulation has no retrievable support anywhere and inverse sign in the only available data.",
    ["theme_10#F10.1"],["Nat Commun 2015 (ncomms7820); SGK1-kalirin-PSD95/NR2B follow-ups (PubMed set)"],
    "ACC-compartment downregulation unverifiable; invert or demote to explicit hypothesis")
add("EC-0059",RF,"Same sign inversion as CCI: SNI-type injuries associate with Kal7 gain-of-function pronociceptively; downregulation claim unsupported.",
    ["theme_10#F10.1"],["Nat Commun 2015; SIRT1-CDK5-Kal7 and T2D follow-ups (PubMed set)"],
    "Invert or scope explicitly as unverified hypothesis")
add("EC-0060",C,"Rac1-PAK-LIMK-cofilin actin-remodeling initiation by Kal7 is the canonical, well-replicated module.",
    ["theme_10#F10.1"],["Nat Commun 2015 (ncomms7820); Li Y et al. 2014, Sci Signal"])
add("EC-0061",NE,"ACC shRNA-Kalirin-7 knockdown experiments could not be matched to any retrievable study.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Demote to hypothesis")
add("EC-0062",C,"Kalirin-7 loss reducing dendritic spines is supported as general cortical biology; the ACC-pain-specific instantiation lacks primary support and timing is biphasic.",
    ["theme_10#F10.1","theme_10#F10.7"],["Penzes-lineage KD spine data; Ru Q et al. 2022, J Clin Invest (SNI increases ACC spines at 7 wk)"],
    "Early LTP-gain vs late remodeling coexist; static 'injury->spine loss' needs time stamps")
add("EC-0063",EX,"Pain-related anxiety phenomenon is robustly ACC-linked but molecular attribution shifts to AC1/GluN2B/HCN pre-LTP circuits and P2X4R-BDNF rather than Kalirin-7.",
    ["theme_10#F10.6","theme_10#F10.2"],["Koga et al. 2015, Neuron 85:377; Nat Neurosci 2024;27:272 (ACC-VTA loop)"],
    "Attribution correction: replace Kal7-dependence with circuit/molecular handles (NB001, ZD7288, oxytocin)")
add("EC-0064",NE,"DBS-of-ACC normalizing Kalirin-7 signaling has no retrievable source.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Demote to hypothesis")
add("EC-0065",C,"Same general-biology support as spine-loss claim; ACC-pain attribution unverified.",
    ["theme_10#F10.7","theme_10#F10.1"],["Penzes-lineage KD data; ACC review PMC13080107"],
    "Time-window qualifier needed; molecular mediator in ACC-pain unestablished")
add("EC-0066",EX,"Anxiety-comorbidity framing supported at phenomenon level with corrected molecular attribution away from Kal7.",
    ["theme_10#F10.6"],["Koga et al. 2015, Neuron; Neurosci Biobehav Rev 2026 (ACC integrative hub)"],
    "Use AC1/GluN2B/HCN/PKMzeta and BLA/LHb/VTA circuit attributions")
add("EC-0067",C,"Rac1-PAK-LIMK-cofilin pathway rationale is the supported canonical module.",
    ["theme_10#F10.1"],["Nat Commun 2015; Li Y et al. 2014, Sci Signal"])
add("EC-0068",EX,"Exercise/environmental enrichment restoring ACC synaptic structure is supported, but Kalirin-7 as the mediating boost is unverified - relabel mechanism.",
    ["theme_10#F10.7"],["Mol Brain 2025 (voluntary running, knee OA); APC/C-Cdh1 Mol Pain 2015"],
    "Corrected mechanism label: running/exercise restores ACC synapses via unspecified (NOT Kal7) mechanisms")
add("EC-0069",C,"LIMK phosphorylation/inhibition of cofilin confirmed within the sensory-neuron actin/TRPV1 lineage.",
    ["theme_05#F5.3"],["Li Y et al. 2014, Sci Signal 7:ra61"])
add("EC-0070",MX,"Adjudicated: spinal PNN degradation promotes pain but targets lamina-I spinoparabrachial projection neurons (microglial GAG stripping +/- MMP-9), not PV interneurons, and forebrain PNN effects run opposite - claim needs cell-type and region re-scoping.",
    ["theme_02#F2.3","theme_02#F2.1","theme_01#F1.13","theme_02#F2.4","theme_02#F2.10"],
    ["Tansley et al. 2022, Science 377:80 (adjudicated); Mascio et al. 2025, Pain (thalamocortical PNNs)"],
    "Re-scope: cell type = projection neurons; encode region-conditioned signs (spinal protective PNNs / cortical pronociceptive PNNs) and phase windows (MMP-9 early, MMP-2 late)")
add("EC-0071",C,"MMP-9 degradation of tight-junction proteins and barrier opening reconfirmed across 2023-2025 reviews and BSCB studies.",
    ["theme_02#F2.1","theme_04#F4.5","theme_04#F4.8"],["Front Mol Neurosci 2025 MMP-9 review; Montague-Cardoso & Malcangio 2021"])
add("EC-0072",C,"MMP-9 feeding the IL-6/JAK inflammatory transcriptional hub fits consensus network framing; ELF1 identified as new upstream initiator.",
    ["theme_09#F9.10","theme_02#F2.2"],["ELF1 study PMC9633582; Aging Dis 2024 JAK2/STAT3 review"])
add("EC-0073",EX,"MMP-9-HIF1alpha linkage supported at axis level (co-driving central sensitization) rather than strict unidirectional induction.",
    ["theme_04#F4.4"],["Eur J Pharmacol 2023 (HIF-1alpha/MMP-9 sensitization)"],
    "Soften causal direction to bidirectional/co-driver axis")
add("EC-0074",C,"MMP-9-to-ROCK upregulation supported within microglial RhoA/ROCK-p38 cascade and MMP-9 hub broadening.",
    ["theme_02#F2.1","theme_05#F5.4"],["Tatsumi et al. 2015, Glia 63:216; Front Mol Neurosci 2025 review"])
add("EC-0075",UR,"Mitochondrial-dysfunction-to-caspase edge in unswept GABA_apoptosis dossier.",
    [],[])
add("EC-0076",NE,"HIF1alpha area heavily swept but the mitochondrial-dysfunction-to-HIF1alpha edge itself was never referenced; mtROS adjacency only.",
    ["theme_04#F4.4"],["Palazon et al. 2014, Immunity (ROS/NF-kB normoxic stabilization context)"],"Adjacent ROS-arm support only")
add("EC-0077",UR,"ROS-output edge of unswept mitochondrial dossier.",
    [],[])
add("EC-0078",C,"Mitochondrial dysfunction engaging RhoA/ROCK supported and extended by new upstream activators (USP53/FKBP51).",
    ["theme_05#F5.10"],["Acta Neurobiol Exp 2022;82 (USP53-FKBP51-RhoA/ROCK)"])
add("EC-0079",C,"Mitochondrial-to-TNF linkage indirectly supported via mtROS/mtDNA as canonical NLRP3 inflammasome activators.",
    ["theme_03#F3.4"],["Grace et al. 2016, PNAS (morphine/NLRP3); Gombault 2013, Front Immunol"],"Indirect (canonical DAMP logic), not edge-specific")
add("EC-0080",UR,"Mitophagy-inhibition edge in unswept autophagy/apoptosis dossier.",
    [],[])
add("EC-0081",UR,"mPTP-to-caspase edge in unswept dossier.",
    [],[])
add("EC-0082",UR,"mPTP-to-calcium edge in unswept dossier.",
    [],[])
add("EC-0083",C,"NF-kB-driven pronociceptive TNFR1 program supported by solTNF/TNFR1-selective genetics and pharmacology.",
    ["theme_03#F3.1","theme_03#F3.3"],["Cells 2025;14:1749 (TNFR1 KO phenocopy); PNAS 2019 (TNFR2 dichotomy)"],
    "TNFR2 is the pro-resolving arm - keep receptor specificity explicit")
add("EC-0084",NE,"Biologically implausible edge (NF-kB suppressing small-molecule binding) untouched by any finding; likely extraction artifact.",
    ["theme_10#F10.5"],[],"Audit extraction; delete or rewrite")
add("EC-0085",NE,"Ca-dependent calcineurin activation is canonical enzymology but the ACC Kal7-degradation context it serves is unsupported.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Keep enzymology, drop ACC-Kal7 packaging unless sourced")
add("EC-0086",NE,"AP-5 antagonism of NMDAR is trivial pharmacology; the preserve-Kal7-in-ACC interpretation is unsourced; card predicate inverted.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Fix direction; decouple from Kal7 narrative")
add("EC-0087",NE,"Ketamine-NMDAR antagonism established; preserve-Kal7 framing unsourced; related ketamine-TrkB interplay plausible-unverified.",
    ["theme_10#F10.1","theme_10#F10.5"],["QC-0068 source (diabetic ketamine study) not located"],"Decouple from Kal7 narrative")
add("EC-0088",C,"NMDAR Ca2+-influx activation of CaMKII as plasticity kinase confirmed in spinal and ACC pain preparations.",
    ["theme_10#F10.8"],["Katano et al. 2011; Neurosci Bull 2021 (pCaMKII-NR2B in ACC)"])
add("EC-0089",UR,"Calcium-to-calpain activation in unswept cascade dossier.",
    [],[])
add("EC-0090",UR,"Calcium-to-mTORC1 edge unswept.",
    [],[])
add("EC-0091",UR,"Calcium-to-CP-AMPAR edge unswept.",
    [],[])
add("EC-0092",UR,"Calcium-to-mitochondrial-dysfunction edge unswept.",
    [],[])
add("EC-0093",EX,"PNN loss and calcium overload are causally linked, with the demonstrated direction being PNN-degradation -> Ca2+-overload.",
    ["theme_02#F2.9"],["Tuina/chABC study doi:10.3389/fnmol.2026.1860375"],
    "Reciprocal direction (Ca2+ overload causes PNN loss) untested; annotate arrow direction")
add("EC-0094",MX,"NG101 does neutralize Nogo-A (mechanism intact) but the NISCI phase 2b trial missed its primary endpoint - efficacy optimism contradicted; card predicate inverted.",
    ["theme_05#F5.1"],["Kucher/Curci NISCI consortium, Lancet Neurol 2025 (PMID 39706632; NCT03935321)"],
    "Invert subject/object; soften dossier to 'well tolerated; subgroup/post-hoc signals only'; spasticity roughly halved vs placebo")
add("EC-0095",C,"Physiological circuit-stabilizing roles of Nogo-A/NgR1 supported, with the important qualification that NgR1 mediates acute collapse but not chronic substrate-bound inhibition.",
    ["theme_05#F5.8","theme_05#F5.1"],["Chivatakarn et al. 2007, J Neurosci 27:7117; Zheng et al. 2005"],
    "Redundancy: PirB, NgR2/gangliosides compensate; ORL1 gates NgR1 maturation (new handle)")
add("EC-0096",UR,"PINK1/Parkin-rapamycin edge in unswept mitophagy dossier.",
    [],[])
add("EC-0097",EX,"Chemogenetic/optogenetic PV rescue supported and extended to firing-pattern restoration as therapeutic readout; RARalpha node is preprint-stage.",
    ["theme_01#F1.6","theme_01#F1.7"],["Qiu et al. 2024, PNAS; Rankin et al. 2024, Cell Rep; Cao/Scherrer/Chen bioRxiv 2022 (preprint)"],
    "RARalpha homeostatic-plasticity mechanism unreviewed (bioRxiv)")
add("EC-0098",C,"PNN necessity for normal function demonstrated in vivo at spinal level via Crtl1/link-protein knockout hyperalgesia phenotype.",
    ["theme_02#F2.6"],["Sanchez-Ventura et al. 2024, Int J Mol Sci 25:4267"])
add("EC-0099",EX,"Spinal disinhibition paradigm rationale extended by opioid-resistant touch-pain dimension and matured KCC2 clinical pipeline.",
    ["theme_01#F1.1","theme_01#F1.6","theme_01#F1.9"],["PNAS 118(3) 2021; Koga 2017, Sci Rep; Pressey et al. 2024, Front Mol Neurosci"],
    "Adds opioid-sparing argument; AXN-027 first-in-human (Q4 2024), OV350 IV (H1 2025)")
add("EC-0100",C,"Fasudil inhibition of ROCK reconfirmed with widened preclinical base (transection repair, Minamata model, intrathecal ripasudil).",
    ["theme_05#F5.5"],["Kishima et al. 2021, Spine; J Orthop Translat 2024"],
    "Predicate inverted (fasudil inhibits ROCK); biphasic dose/context effects noted")
add("EC-0101",C,"Rac1 activation of PAK is canonical effector biology in the supported module.",
    ["theme_10#F10.1"],["Nat Commun 2015; Penzes et al. 2008"])
add("EC-0102",C,"NSC23766 Rac1 inhibition valid as pharmacology but off-target profile (muscarinic antagonist, NMDAR-CREB suppression) confounds behavioral interpretation; predicate inverted.",
    ["theme_10#F10.9"],["JPET 2013 (PMID 23887096); J Neurosci 2014;34:14006"],
    "No ACC-pain microinjection use found; interpret any future ACC results cautiously")
add("EC-0103",C,"Rbfox1 pleiotropy confirmed - regulates hundreds of transcripts; global targeting deemed unlikely therapeutic.",
    ["theme_06#F6.6"],["Neurotherapeutics editorial commentary 2024; He et al. 2023, Neurotherapeutics"],
    "Splice-targeting (downstream ASO) preferred over global Rbfox1 modulation")
add("EC-0104",C,"Rbfox1 expression preventing NrCAM exon-10 retention confirmed end-to-end (CLIP binding at (U)GCAUG downstream of exon 10).",
    ["theme_06#F6.6"],["He et al. 2023, Neurotherapeutics 20:e00309; Liang et al. 2020, J Pain 21:625"],
    "Canonical binding-direction (exon exclusion) debated in commentary; behavioral rescue incomplete")
add("EC-0105",C,"AAV5-Rbfox1 restoration mitigating hypersensitivity directly replicated.",
    ["theme_06#F6.6"],["He et al. 2023, Neurotherapeutics 20:e00309"])
add("EC-0106",MX,"Functional NgR1-RhoA coupling real but card direction inverted (ligand-NgR1 activates RhoA), and NgR1 is dispensable for chronic substrate-bound inhibition.",
    ["theme_05#F5.8","theme_05#F5.7"],["Chivatakarn et al. 2007, J Neurosci; Zheng et al. 2005; Sekine et al. 2018, Sci Signal (ORL1)"],
    "Invert direction; qualify NgR1-centric convergence to acute signaling; PirB/NgR2 redundancy")
add("EC-0107",C,"RhoA activation of ROCK reconfirmed as current standard model in spinal microglia (P2Y12/13-p38 cascade).",
    ["theme_05#F5.4"],["Tatsumi et al. 2015, Glia 63:216; Zhang et al. (P2Y12-GTP-RhoA)"])
add("EC-0108",EX,"LPA-LPAR1-RhoA demyelination cascade supported and extended to satellite-glial/Schwann-cell peripheral arm with new antagonists.",
    ["theme_05#F5.6"],["J Transl Med 2025 (Cx43-SGC crosstalk); STTT 2025 LPA review; IASP 2024 UD-039 posters"],
    "Peripheral arm absent from KB dossier; PIPE-791, oxypeucedanin novel handles")
add("EC-0109",NE,"Simvastatin blocking RhoA membrane anchoring is standard mevalonate pharmacology but was not resurfaced by this sweep.",
    ["theme_05#F5.5"],[],"Predicate inverted (statin blocks RhoA prenylation/anchoring)")
add("EC-0110",EX,"Context-dependent regeneration-vs-pain roles reinforced: ROCK inhibition aids regeneration/remyelination centrally and peripherally while relieving pain.",
    ["theme_05#F5.5"],["J Orthop Transl 2024; Ramer et al. 2004, J Neurosci; Xu et al. 2020, Mol Pain"],
    "Add pro-regenerative instances to caution framing")
add("EC-0111",C,"SST interneuron ablation abolishing mechanical pain and SST transcriptome handles reconfirmed.",
    ["theme_01#F1.8"],["Duan et al. 2014, Cell 159:1417; Chamessian et al. 2018, Sci Rep; Cav3.2-in-SOM+ Front Cell Neurosci 2022"])
add("EC-0112",NE,"SST circuitry solid, but Prdm12 developmental-specification edge was not resurfaced and direction reads backwards (Prdm12 specifies SST fate).",
    ["theme_01#F1.8"],[],"Fix direction; attach developmental source before promotion")
add("EC-0113",C,"TNF-alpha activation of RhoA supported and extended by USP53/FKBP51 deubiquitinase arm.",
    ["theme_05#F5.10"],["Acta Neurobiol Exp 2022;82; Tatsumi 2015 context"])
add("EC-0114",C,"TNF-alpha engagement of JAK/STAT3 (Src-dependent) matches consensus network framing.",
    ["theme_09#F9.10"],["Tsuda et al. 2011, Brain; Aging Dis 2024 review"])
add("EC-0115",C,"TNF-alpha downregulation of tight-junction proteins supported in BSCB/BBB disruption literature.",
    ["theme_04#F4.5","theme_04#F4.8"],["Montague-Cardoso & Malcangio 2021; claudin-12 bioRxiv 2019 (BNB mirror)"])
add("EC-0116",C,"Normoxic HIF1alpha stabilization by ROS/TNF/NF-kB systematized in landmark inflammation-immunity integration.",
    ["theme_04#F4.4"],["Palazon et al. 2014, Immunity 41:518"])
add("EC-0117",EX,"XPro1595 selective solTNF/TNFR1 blockade validated in vivo and extended by human Phase 2 safety precedent plus sex- and window-limitations.",
    ["theme_03#F3.1","theme_03#F3.2","theme_03#F3.3"],["Cells 2025;14:1749; Jaeger et al. 2026, npj Dementia (MINDFuL); O'Reilly 2021, J Neurotrauma"],
    "Sex-dependent efficacy (males respond, females blunted via estrogen); late SCI dosing failed; AD indication not pain; card predicate phrasing inverted")
add("EC-0118",NE,"Encoding inverted - CypA-MMP-9 degrades tight junctions, not vice versa; underlying proteolysis supported so fix direction rather than delete.",
    ["theme_04#F4.8"],["Theme 4 Contradictions #5 (data-quality flag)"],"Directionality fix required")
add("EC-0119",NE,"Encoding inverted - VEGFR2 is downregulated by disease signals, not by tight junctions; underlying coupling untested; fix direction/source.",
    ["theme_04#F4.7"],["Theme 4 Contradictions #5"],"Data-quality flag")
add("EC-0120",EX,"Staged-prophylaxis concept gains indirect/conceptual support (DMF prevention of chronification; schedule-dependent HDACi effects) but the staggered quadruple protocol itself is untested.",
    ["theme_08#F8.7","theme_09#F9.7"],["Le et al. 2025, Brain Behav Immun 128:725 (DMF pretreatment); Denk et al. 2013, Pain 154:1668"],
    "Proposal-level synthesis: mark evidence_level=synthetic; component edges individually graded elsewhere")
add("EC-0121",C,"TrkB-to-MAPK arm directly shown in rACC aversion (NR2B/pERK/pCREB reversed by TrkB block).",
    ["theme_10#F10.4"],["Li TT et al. 2022, Brain Res Bull"])
add("EC-0122",MX,"TrkB-driven KCC2 downregulation is strongly supported including human tissue, but early post-lesion downregulation can be adaptive - temporal qualifier mandatory.",
    ["theme_01#F1.3","theme_01#F1.4","theme_01#F1.10","theme_01#F1.14"],["Davis 2025 (human SDH); Dedek 2019, Brain; Cheung et al. 2023, Sci Rep 13:7871"],
    "Pathogenic in chronic dorsal-horn pain states; transiently beneficial early post-lesion in motor circuits; BDNF-TrkB effects context-dependent (immature/Shc-only upregulate KCC2)")
add("EC-0123",C,"ANA-12 antagonism of TrkB.FL is validated tool pharmacology; card predicate inverted.",
    ["theme_10#F10.5"],["Cazorla et al. 2011 line"],"Fix direction")
add("EC-0124",MX,"Full-length TrkB signaling downregulating KCC2 supported (rodent + human) with the same early-adaptive/temporal contradiction.",
    ["theme_01#F1.3","theme_01#F1.10","theme_01#F1.14"],["Rivera et al. 2002/2004; Cheung 2023, Sci Rep"],
    "Time-window and circuit qualifiers required (motor vs dorsal-horn)")
add("EC-0125",C,"TrkB potentiation of NMDAR/GluN2B trafficking shown in rACC aversion and PSD-95-GluN2B literature.",
    ["theme_10#F10.4","theme_10#F10.3"],["Li TT et al. 2022, Brain Res Bull; Sci Rep 2022 PSD-95/NR2B ACC"])
add("EC-0126",NE,"TrkB.T1-specific interaction with ANA-12 not separately resurfaced though ANA-12 tool validity holds broadly.",
    ["theme_10#F10.5"],[],"Isoform-specific binding unaddressed")
add("EC-0127",EX,"Anti-TNF paradox expanded to two distinct hazards: demyelinating neuropathy and impaired acute-to-chronic pain resolution (TNFR2 pro-resolving arm).",
    ["theme_03#F3.3"],["Reumatologia 2021 (Kucharz); J Pain Res 2025 (postoperative resolution); PNAS 2019 TNFR2/Treg"],
    "NEW_MECHANISM candidate: neuronal TNFR2->POMC/beta-endorphin + CB1 pro-resolution axis (bioRxiv 2025.11.24.690195)")
add("EC-0128",NE,"VEGFR2-NRP1 coreceptor enhancement is standard angiogenesis biology but unassessed in pain context this sweep.",
    ["theme_04#F4.7"],[],"Attach angiogenesis-domain source or mark out-of-scope")
add("EC-0129",EX,"Excess VEGFA driving aberrant angiogenesis and prolonged pain confirmed; direct painful-neuroma causality not retrieved.",
    ["theme_04#F4.7"],["J Neurochem 2013; Mol Pain 2022 (sFlt-1); PMID 42582843 (neuroma phenotypic shift, VEGF-untested)"],
    "Soften to neuroma-associated neovascularization unless a causal VEGF-neuroma study is attached")
add("EC-0130",EX,"Repair-vs-pain duality refined into isoform and receptor axes (VEGF-Axxxa/xxxb; VEGFR1 pronociceptive vs VEGFR2 context-protective).",
    ["theme_04#F4.7"],["Beazley-Long et al. 2013, Am J Pathol; Hulse 2017, Channels; Brain Sci 2025 pair"],
    "Replace blunt duality framing with SRPK1-splicing and receptor-resolved edges")
add("EC-0131",RF,"ZFHX2 regulome excludes BDNF and Zfhx2-null mice are heat-HYPERsensitive - the BDNF-TrkB-KCC2 rationale is contradicted.",
    ["theme_06#F6.8"],["Habib et al. 2018, Brain 141:365 (Marsili syndrome)"],
    "Human genetics premise real (R1913K hypoalgesia) but mechanism cards must be rebuilt on SST/PTGIR/GFRA3/GAL regulome")
add("EC-0132",NE,"No injury-model (SNI/CCI/SNL) ZFHX2 study exists; central-sensitization role unevidenced.",
    ["theme_06#F6.8"],[],"Strong-but-not-exhaustive negative evidence; targeted PubMed check advised before deletion")
add("EC-0133",RF,"Claimed Nav1.7/Nav1.8/TRPV1/TRPA1/CGRP transactivation contradicted: ChIP-seq regulome is neuropeptide-signalling genes (SST up; PTGIR, GFRA3, GAL down).",
    ["theme_06#F6.8"],["Habib et al. 2018, Brain 141:365"],
    "Replace battery with corrected gene set; note Zfhx2-null heat hypersensitivity guards against naive LOF-analgesia modeling")
add("EC-0134",NE,"No preclinical ZFHX2-ASO/siRNA study surfaced in any database searched.",
    ["theme_06#F6.8"],[],"Concept-only; keep unsourced")
add("EC-0135",UR,"mPTP-rapamycin protection edge in unswept mitophagy dossier.",
    [],[])
add("EC-0136",UR,"mPTP-Ru360/MCU edge in unswept dossier.",
    [],[])
add("EC-0137",UR,"mTORC1-rapamycin edge in unswept dossier.",
    [],[])
add("EC-0138",UR,"myr-Akt payload edge in unswept autophagy dossier.",
    [],[])
add("EC-0139",UR,"Skill/meta-appraisal design claim outside all ten themes.",
    [],[])
add("EC-0140",C,"ANA-12 preserving KCC2 via TrkB blockade consistent with validated BDNF-TrkB-to-KCC2 cascade and ANA-12 tool data.",
    ["theme_10#F10.5","theme_01#F1.4"],["Dedek et al. 2019, Brain; Mol Pain 2023 dynamic-allodynia study"])
add("EC-0141",UR,"Bcl-xL-Kozak vector-design edge in unswept autophagy dossier.",
    [],[])
add("EC-0142",UR,"Long-term autophagy-blockade risk rationale in unswept dossier.",
    [],[])
add("EC-0143",UR,"Beclin-1-calpain edge in unswept dossier.",
    [],[])
add("EC-0144",UR,"Beclin-1-mTORC1 edge in unswept dossier.",
    [],[])
add("EC-0145",NE,"BDNF enhancing SST interneuron excitability not resurfaced although SST area swept.",
    ["theme_01#F1.8"],[],"Attach source or drop")
add("EC-0146",EX,"Microglial BDNF/ROCK interplay supported via RhoA/ROCK-p38 microglial cascade, but card predicate wording ('release of ROCK') is garbled.",
    ["theme_05#F5.4"],["Tatsumi et al. 2015, Glia 63:216"],
    "Recast edge as BDNF-linked microglial RhoA/ROCK activation (kinases are not released)")
add("EC-0147",NE,"Explicitly flagged NO_SUPPORT_FOUND: no retrieved source connects BDNF to Kalrn translation in any region.",
    ["theme_10#F10.4","theme_10#F10.1"],[],"Drop or mark speculative")
add("EC-0148",UR,"Cascade-via-ROS HIF1alpha edge in unswept cascade dossier (HIF area swept, edge untouched).",
    [],[])
add("EC-0149",NE,"No pain-context study links HIF1alpha transcriptionally to ANGPT2; general-hypoxia plausibility only - mark speculative.",
    ["theme_04#F4.10"],[],"Keep sign, set evidence_level=speculative until primary source attached")
add("EC-0150",NE,"Glycolytic-shift-to-Ang-2 chain unsupported in pain literature; retrieved Ang-2 regulation is neutrophil-elastase-linked instead.",
    ["theme_04#F4.10","theme_04#F4.6"],["Acta Neuropathol Commun 2018 (sivelestat/Ang-1 alternative route)"],
    "Consider replacing with elastase->Ang-1-degradation edge")
add("EC-0151",C,"MMP-9-to-NgR1 upregulation via RhoA/ROCK listed among reconfirmed core claims; ORL1 maturation adds upstream handle.",
    ["theme_02#F2.1","theme_05#F5.7"],["Front Mol Neurosci 2025 review; Sekine et al. 2018, Sci Signal"])
add("EC-0152",C,"NF-kB upstream activation of IL-6/gp130/JAK2 hub matches consensus framing.",
    ["theme_09#F9.10"],["Tsuda 2011, Brain; Aging Dis 2024 review"])
add("EC-0153",NE,"Rbfox1-NrCAM splice axis confirmed end-to-end, but the NrCAM-NgR1 interaction edge remains ambiguous/untested (EGFR-link hypothesis also unproven).",
    ["theme_06#F6.6"],["Neurotherapeutics commentary 2024"],"Keep AMBIGUOUS status; do not promote without binding data")
add("EC-0154",NE,"PV-failure-to-SST-hyperactivation compensation edge not resurfaced (BLA bidirectional PV/SST appeared in search log only).",
    ["theme_01#F1.8"],[],"Spinal vs BLA context unclear - specify region before sourcing")
add("EC-0155",C,"Listed among IL-6/JAK-STAT network edges matching current consensus framing; semantics unusual but sweep-assigned SUPPORTS.",
    ["theme_09#F9.10"],["Tsuda et al. 2011, Brain"],"Reword predicate for clarity (PV-KCC2/BDNF state modulates JAK/STAT tone)")
add("EC-0156",NE,"Indirect PV-via-RhoA/MMP9/PNN impairment of NgR1 untested as a chain and inherits the EC-0070 cell-type problem.",
    ["theme_01#F1.13","theme_02#F2.3"],["Tansley et al. 2022, Science"],"Do not promote until EC-0070 re-scoped")
add("EC-0157",NE,"ACC-contextualized ROCK-antagonizes-Kal7 inference flagged unsupported; generic RhoA/Rac1 antagonism is textbook but pain-context source absent.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Demote with kalirin_inferred flag retained")
add("EC-0158",UR,"Goldilocks/dual-lock AAV rationale in unswept autophagy dossier.",
    [],[])
add("EC-0159",EX,"Family-level SPM pro-resolution support strong, but the specific SPM-complementary-to-Ang-1 barrier combination is untested head-to-head.",
    ["theme_08#F8.1","theme_08#F8.3","theme_04#F4.6"],["Ji 2023, Annu Rev Pharmacol Toxicol; Ferreira 2025, Eur J Pharmacol (AT-LXA4)"],
    "Remains INFERRED: no direct SPM-vs-Ang-1 comparison retrieved")
add("EC-0160",NE,"RhoA-antagonizes-Kal7 inference flagged unsupported in ACC framing.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"kalirin_inferred; demote")
add("EC-0161",NE,"Generic RhoA-Rac1 functional antagonism is standard biology but no pain-context primary source surfaced for the edge as framed.",
    ["theme_10#F10.1"],["Penzes-lineage general biology"],"Attach textbook/review source or leave low confidence")
add("EC-0162",NE,"Axis-level antagonism of Kal7 flagged unsupported (ACC-contextualized inferred).",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Demote")
add("EC-0163",NE,"Via-Rac1 antagonism variant likewise unsupported in pain context.",
    ["theme_10#F10.1"],[],"kalirin_inferred; demote")
add("EC-0164",C,"TNF-VEGFA mutual upregulation reconfirmed in inflammation-angiogenesis landmark literature.",
    ["theme_04#F4.4"],["Palazon et al. 2014, Immunity; Nat Med 2006 Ang-2/TNF era"])
add("EC-0165",UR,"Therapeutic-strategy rationale in unswept autophagy/apoptosis dossier.",
    [],[])
add("EC-0166",NE,"Ana-12 dossier swept but TrkB-causes-calcium-overload edge itself untouched.",
    ["theme_10#F10.5"],[],"Chain inference only; source or demote")
add("EC-0167",EX,"Cytokine-to-ACC-plasticity contribution supported at network level; direct TNFalpha-to-spine-elimination endpoint unverified.",
    ["theme_10#F10.10"],["ACC neuroplasticity review doi:10.1002/brb3.71408 (PMC13080107)"],
    "Low-medium confidence on morphology endpoint; time-stamp dynamics")
add("EC-0168",MX,"Contested VEGFR2 valence: 2025 organotypic-cord data show VEGFR2 signaling neuroprotective with pronociception segregating to VEGFR1, contradicting the inferred pronociceptive VEGFR2-to-BDNF-TrkB-to-KCC2 chain.",
    ["theme_04#F4.7"],["Brain Sci 2025 pii S1878747925000108/S1878747925000121; JECCR 2021 (anti-VEGFR1)"],
    "Context-dependent (chemotherapy neurotoxicity vs nerve-injury models); treat as contested, consider VEGFR1 reassignment")
add("EC-0169",UR,"mTORC1 double-edged-sword rationale in unswept autophagy dossier.",
    [],[])

# ---------------- QUANTITATIVE CLAIMS ----------------
add("QC-0001",C,"B1-selective des-Arg9-Leu8-bradykinin reducing established mechanical allodynia days-to-weeks post-lesion supported by kinin-antagonist CIPN work.",
    ["theme_07#F7.5"],["Becker et al. 2023, Pharmaceutics 15:852"],
    "Mechanical allodynia responsive; cold allodynia kinin-resistant in cisplatin model - scope boundary")
add("QC-0002",EX,"Protective kinin-opioid interaction conceptually reinforced by stage-dependent protective B1R biology, but the exact 30-35% double-KO figure was not independently reproduced.",
    ["theme_07#F7.9"],["Front Med 2025 (stage-dependent diabetic B1R); Stemper et al. 2025, Pain"],
    "B1R sign flips with disease stage (early protective / late pronociceptive) - add temporal qualifier")
add("QC-0003",C,"Established-allodynia reversal by kinin blockade supported (DALBK/icatibant ~52%/57% in cisplatin CIPN).",
    ["theme_07#F7.5"],["Becker et al. 2023, Pharmaceutics 15:852"],"Cold allodynia resistant boundary condition")
add("QC-0004",C,"BRADiNP crossover design statement verified verbatim against the published Phase 2a report (fulmetibant 450 mg once daily, 2x4-week periods).",
    ["theme_07#F7.7"],["Stemper et al. 2025, Pain (doi:10.1097/j.pain.0000000000003642; NCT05219812; adjudicated)"],
    "Trial negative: treatment difference 0.07 (-0.170 to 0.314) - contextualize as failed translation")
add("QC-0005",C,"Primary-endpoint statement verified verbatim against published BRADiNP report.",
    ["theme_07#F7.7"],["Stemper et al. 2025, Pain (adjudicated)"],"Negative primary result")
add("QC-0006",C,"AE-rate statement verified verbatim (mostly mild/moderate, 51.3% of treated participants; 41.8% drug vs 32.9% placebo).",
    ["theme_07#F7.7"],["Stemper et al. 2025, Pain (adjudicated); Icatibant Outcome Survey safety bedrock"],"Promote citation_status to VERIFIED")
add("QC-0007",NE,"~50% cognitive-impairment prevalence statistic not targeted by any executed query.",
    ["theme_08#F8.8"],[],"Left unverified; assign dedicated epidemiology check")
add("QC-0008",EX,"LY2828360 paclitaxel experiment reproduced exactly and extended (sensory-neuron locus; spontaneous-pain CPP; opioid-sparing).",
    ["theme_08#F8.8"],["Lin et al. 2018 (PMID 29192123); Guenther et al. 2024/2025, Biomed Pharmacother/Neuropharmacology"],
    "CB2 bench-bedside gap: inconsistent human trials; CNTX-6016 still Phase I")
add("QC-0009",UR,"AMG487 CCL21-CXCR3 dosing claim outside all ten themes.",
    [],[])
add("QC-0010",UR,"CCL21-neutralising antibody claim outside themes.",
    [],[])
add("QC-0011",UR,"48-hour CCL21 reversal claim outside themes.",
    [],[])
add("QC-0012",EX,"PLX5622 IC50/tool status supported; systemic myeloid effects and pexidartinib hepatotoxicity constraints added.",
    ["theme_03#F3.7"],["Nat Commun 2019 (PLX5622 pharmacology); Cell Reports 2025 (sex-dimorphic depletion)"],
    "Male>female depletion efficacy under identical regimens")
add("QC-0013",EX,"65 mg/kg pSNL PLX5622 experiment supported by CSF1R-depletion reversal literature with sex-dimorphic caveat.",
    ["theme_03#F3.7"],["Lee et al. 2018, Mol Pain 14; Henry et al. 2020, J Neurosci"],
    "Sex-dimorphic microglial response (female mitochondrial-survival compensation)")
add("QC-0014",UR,"CXCR4-GlyR alpha3 colocalization claim outside themes.",
    [],[])
add("QC-0015",UR,"AMD3100 SNL claim outside themes (nearest: Xie 2016 AMD3100 noted unresolved in theme 5 limitations).",
    [],[])
add("QC-0016",UR,"Systemic AMD3100 opioid-secretion claim outside themes.",
    [],[])
add("QC-0017",UR,"pSNL/CPIP AMD3100 cytokine claim outside themes.",
    [],[])
add("QC-0018",UR,"SNI AMD3100 claim outside themes.",
    [],[])
add("QC-0019",UR,"Bone-cancer AMD3100 claim outside themes.",
    [],[])
add("QC-0020",UR,"Cx43 hemichannel Ca2+-regulation claim outside themes (only incidental Cx43-SGC lexical appearance in theme 5).",
    [],[])
add("QC-0021",UR,"Cx43 injury-induced expression kinetics outside themes.",
    [],[])
add("QC-0022",UR,"Cx43 heterozygous-KO gene-dosage claim outside themes.",
    [],[])
add("QC-0023",UR,"ABT-627 endothelin diabetic-rat claim outside themes.",
    [],[])
add("QC-0024",UR,"Bosentan SCI claim outside themes.",
    [],[])
add("QC-0025",UR,"GLT-1 glutamate-gradient physiology outside themes.",
    [],[])
add("QC-0026",UR,"GLT-1 80-90% uptake share outside themes.",
    [],[])
add("QC-0027",UR,"Slc1a2 mRNA reduction kinetics outside themes.",
    [],[])
add("QC-0028",UR,"Microdialysis glutamate elevation outside themes.",
    [],[])
add("QC-0029",UR,"GLT-1 upregulation timecourse outside themes.",
    [],[])
add("QC-0030",UR,"GLT-1 heterozygous-KO severity claim outside themes.",
    [],[])
add("QC-0031",UR,"Ceftriaxone PHN pilot outside themes.",
    [],[])
add("QC-0032",UR,"GM-CSFR nociceptor-expression controversy explicitly carried forward unverified by theme 6 limitations.",
    [],[],"Assigned to immune-theme dossier; not re-searched")
add("QC-0033",UR,"Human DRG GM-CSFR map outside swept findings.",
    [],[])
add("QC-0034",UR,"DRG meninges leukocyte accumulation kinetics outside themes.",
    [],[])
add("QC-0035",UR,"Vertebral-BM myeloid migration percentages outside themes.",
    [],[])
add("QC-0036",C,"COHb >10-15% toxicity ceiling consistent with entire CORM-field premise of controlled local CO delivery.",
    ["theme_08#F8.5"],["Motterlini & Otterbein 2010, Nat Rev Drug Discov; Ling et al. 2017, J Med Chem"],
    "HO isoform dichotomy (HO-1 anti-, HO-2 pronociceptive) must accompany any HO-activity statement")
add("QC-0037",UR,"Intrathecal IGF2-siRNA 10-day claim (IGF1-2 dossier) untouched by sweeps.",
    [],[])
add("QC-0038",C,"[Cl-]i 4-7 mM physiological setting supported by chloride-homeostasis canon and newly human-anchored via HRDD biomarker extension.",
    ["theme_01#F1.3","theme_01#F1.15"],["Marshall et al. 2023, Brain Commun; Pressey et al. 2024, Front Mol Neurosci"],
    "HRDD matures as human pharmacodynamic readout of spinal KCC2; CSF-KCC2 still Rett-only")
add("QC-0039",EX,"CLP290 claim embedded in a field whose pipeline has advanced to named candidates (AXN-027 FIH; OV350); CLP290 figures themselves not independently resurfaced.",
    ["theme_01#F1.1","theme_01#F1.2"],["Pressey et al. 2024, Front Mol Neurosci 17:1503070"],
    "Attach primary CLP290 source; note no CLP257 clinical trial exists")
add("QC-0040",EX,"Potency/selectivity statements carry a mechanism-of-action caveat: CLP257 MOA debated (indirect; membrane-clustering mechanism supported 2026).",
    ["theme_01#F1.2","theme_01#F1.1"],["PNAS 2026 (prochlorperazine/CLP-257 clustering); PMC7371006 (MOA critique)"],
    "ARN23746 numbers not independently surfaced - verify against primary before promotion")
add("QC-0041",NE,"ARN23746 SNI efficacy figures not surfaced by sweep (flagged unverified quantitative card).",
    ["theme_01#F1.1"],[],"Verify ARN23746 primary source")
add("QC-0042",EX,"Lead-compound claim carries same MOA caveat; specific EC50/B:P figures not independently surfaced.",
    ["theme_01#F1.2"],["PMC7371006; PNAS 2026"],"Verify primary source for the unnamed lead")
add("QC-0043",NE,"STAB-1 prophylactic CIPN figure not surfaced (flagged unverified).",
    ["theme_01#F1.1"],[],"Verify STAB-1 primary source")
add("QC-0044",NE,"BUM-9082 brain-selectivity figure not surfaced (flagged unverified).",
    ["theme_01#F1.1"],[],"Verify BUM-9082 primary source")
add("QC-0045",NE,"CLP290+bumetanide dual ED50-synergy figure not surfaced (flagged unverified).",
    ["theme_01#F1.1"],[],"Verify synergy source")
add("QC-0046",NE,"200 mg/kg tolerability figure not surfaced (flagged unverified).",
    ["theme_01#F1.1"],[],"Verify tolerability source")
add("QC-0047",C,"P2X7 high-micromolar ATP affinity threshold reconfirmed ahead of clinical-track antagonist AK1780.",
    ["theme_03#F3.8"],["J Pain 2025 (AK1780/LY3857210); Chessell et al. 2005, Pain 114:386"],
    "AK1780 positioned for neuropathic-pain PoC trials")
add("QC-0048",EX,"PPARgamma agonist analgesia supported and mechanistically deepened (sTREM2 biomarker, M1/M2, mitochondrial axis) with TZD-safety caveats.",
    ["theme_08#F8.6"],["Acta Neuropathol Commun 2025; Trends Pharmacol Sci 2024"],
    "Rosiglitazone CV signal; fluid retention/weight gain limit chronic use")
add("QC-0049",C,"Intrathecal 15d-PGJ2 anti-allodynic claim supported at class level within PPARgamma agonist literature.",
    ["theme_08#F8.6"],["Pioglitazone NP literature (PMC4329091; Acta Neuropathol Commun 2025)"],
    "No 15d-PGJ2-specific study resurfaced this sweep - class-level only")
add("QC-0050",C,"Ripasudil intrathecal SCI allodynia effect (to day 28) directly reconfirmed.",
    ["theme_05#F5.5"],["Kishima et al. 2021, Spine (doi:10.1016/j.spinee.2020.08.011)"])
add("QC-0051",C,"RhoA-siRNA durability advantage over BA-210 consistent with ROCK-inhibitor preclinical base.",
    ["theme_05#F5.5"],["Spine 2021 ripasudil; J Orthop Transl 2024 fasudil"],"siRNA-vs-peptide durability contrast retained")
add("QC-0052",C,"Fingolimod lymphopenia to ~20-30% baseline via lymph-node trapping confirmed as class hallmark.",
    ["theme_08#F8.9"],["Doolen et al. 2018, Pain 159:224; S1PR pharmacology reviews"],
    "First-dose bradycardia additional class caveat")
add("QC-0053",NE,"Most-potent-SPM ED50 comparison not reproduced in sweep results though SPM area thoroughly covered.",
    ["theme_08#F8.1"],[],"Locate primary head-to-head ED50 source")
add("QC-0054",NE,"Omega-3-to-SPM conversion efficiency estimate not independently surfaced (adjacent null RA supplementation RCT noted).",
    ["theme_08#F8.4"],["Sci Rep 2017 17-HDHA association"],"Conversion-efficiency figure needs sourcing")
add("QC-0055",NE,"2-14 day Nogo-A therapeutic-window restriction not directly tested; NISCI results partially support windowing caution.",
    ["theme_05#F5.1"],["Lancet Neurol 2025 NISCI"],"Window rationale remains proposal-level")
add("QC-0056",C,"TLR2 mRNA/protein time course (rise 1-3 d, peak 7-14 d) supported by TLR-axis pain literature.",
    ["theme_03#F3.6"],["ACT001 study Front Immunol 2022; TLR4 review PMC7890571"],
    "Peripheral TLR4 stimulation can transiently release opioids - antagonism caveat")
add("QC-0057",C,"TRPV1 60-70% small/medium DRG neuron share consistent with literature family; not matched to a single primary table this sweep.",
    ["theme_06#F6.3","theme_06#F6.4"],["TRPV1-biased allosterism Neuron 2024 (area anchor)"],
    "Confidence-note retained per theme 6 limitations")
add("QC-0058",C,"Capsaicin 8% patch clinical basis uncontested in retrieved 2022-2026 TRPV1 literature.",
    ["theme_06#F6.4"],["Qutenza trial background via theme_07-style corroboration; Scand J Pain 2025 (ACD440 context)"])
add("QC-0059",C,"Qutenza statement consistent with retrieved trial-literature background; unchanged.",
    ["theme_06#F6.4"],["Scand J Pain 2025 (PMID 40711349) context"])
add("QC-0060",C,"~30% pain-score reduction vs low-dose control consistent with trial background; unchanged.",
    ["theme_06#F6.4"],["Qutenza trial background"],"Note substring false-positive flag in theme 3 (harmless)")
add("QC-0061",C,"ACD440 ~50% temperature-evoked pain reduction figure matches published Phase 2a; restrictive qualifiers apply.",
    ["theme_06#F6.4"],["Scand J Pain 2025 (PMID 40711349; NCT05416931)"],
    "n=14 crossover; benefit shown in prespecified period-1 analysis only; thermal-evoked pain only; primary endpoint missed due to period effect")
add("QC-0062",UR,"Etifoxine nerve-crush claim (TSPO dossier) outside themes.",
    [],[])
add("QC-0063",UR,"Etifoxine monoarthritis claim outside themes.",
    [],[])
add("QC-0064",UR,"TSPO low-affinity binder frequency outside themes.",
    [],[])
add("QC-0065",UR,"TSPO sex-difference kinetics outside themes.",
    [],[])
add("QC-0066",C,"ANA-12 IC50 ~45.6 nM high-affinity non-competitive TrkB binding revalidated.",
    ["theme_10#F10.5"],["Cazorla et al. 2011 lineage"])
add("QC-0067",C,"Systemic 0.5 mg/kg i.p. brain-wide partial TrkB inhibition within ~4 h matches published ANA-12 pharmacokinetics.",
    ["theme_10#F10.5"],["Cazorla-lineage; 2022/2025 rACC usage studies"])
add("QC-0068",NE,"Diabetic ketamine-ANA-12 reversal study directionally plausible but not independently located.",
    ["theme_10#F10.5"],[],"Keep medium-low confidence until primary source found")
add("QC-0069",NE,"S5E2 PV-enhancer >90% specificity figure not assessed by any query.",
    ["theme_01#F1.6"],[],"PV area swept; enhancer-specificity figure unsourced")
add("QC-0070",C,"Intrathecal Cav3.2 ASO sustained analgesia supported by in vivo silencing literature (Messinger 2009) with duration consistent with ASO pharmacodynamics.",
    ["theme_06#F6.5"],["Messinger et al. 2009, Pain 145:184"],
    "ABT-639 Phase II failure tempers blocker translation (possible low human DRG T-type density)")
add("QC-0071",EX,"H3K18la persistence core premise confirmed and extended with first concrete targets (IGF2BP2-CCT2), but mark is model- and locus-specific.",
    ["theme_09#F9.1","theme_09#F9.3","theme_04#F4.2"],["Wang Q-H et al. 2025, J Neurosci (DOI 10.1523/jneurosci.0365-25.2025); Nat Commun 2025 DOCK4"],
    "H3K18la robust in CCI DRG but unchanged in SNL where H4K8la rose - annotate model/locus")
add("QC-0072",NE,"Lactylation-blockade analgesia principle multiply replicated (2-DG, oxamate, LDN-193189) but FX11-specific 10 ug/72 h parameters were not reproduced verbatim - citation verification required.",
    ["theme_04#F4.2","theme_09#F9.1"],["J Neurosci 2026 PMID 41260921 (2-DG/Igf2bp2); Neurobiol Dis 2026 (oxamate)"],
    "Keep UNVERIFIED pending FX11 source check")
add("QC-0073",NE,"AZD3965 oral 50 mg/kg lactylation claim not encountered this sweep.",
    ["theme_09#F9.10"],[],"Unverified, not falsified - locate source")
add("QC-0074",NE,"Truncated claim text ('50 mg/kg)...') lacks compound identity and was not encountered; unverified.",
    [],[],"Fix truncated card text first")
add("QC-0075",UR,"1400W selectivity claim (iNOS dossier) outside all ten themes.",
    [],[])
add("QC-0076",UR,"1400W SNA early-window efficacy claim outside themes.",
    [],[])
add("QC-0077",UR,"1400W 7-day window-loss claim outside themes.",
    [],[])
add("QC-0078",UR,"GW274150 profile claim outside themes.",
    [],[])
add("QC-0079",UR,"KD7040 Phase IIa plan claim outside themes.",
    [],[])
add("QC-0080",UR,"1400W schedule-dependence summary outside themes.",
    [],[])
add("QC-0081",NE,"3-day onset/4-week persistence of ACC Kalirin-7 downregulation belongs to the unsupported ACC narrative.",
    ["theme_10#F10.1"],["Theme 10 Contradictions #1"],"Drop or demote with the ACC-Kal7 cluster")
add("QC-0082",EX,"TREM2 downregulation claim extended by TREM2/LAMP1 phagocytosis-targeting therapeutics and senescence dimension.",
    ["theme_03#F3.10","theme_02#F2.5"],["Tuina study 2026 (TREM2/LAMP1); Neurosci Biobehav Rev 2026 senescence review"],
    "Phagocytosis-checkpoint angle makes TREM2 actionable; CX3CR1 dependence contested")
add("QC-0083",EX,"AL002a reversal claim extended into microglial-phagocytosis and aging frameworks.",
    ["theme_03#F3.10","theme_02#F2.5"],["TREM2/LAMP1 2026; Aging Cell 2025 ABT-737"],"Registry-level verification of AL002a pain data advised")
add("QC-0084",C,"P2X7 >100 uM threshold driving NLRP3/IL-1beta/pyroptosis supported and clinically proximal (AK1780).",
    ["theme_03#F3.8"],["J Pain 2025 AK1780; Chessell 2005"],"Gasdermin-D pyroptosis added downstream")
add("QC-0085",C,"2-DG glycolysis-blockade analgesia independently replicated across lactylation and HK2/myeloid programs.",
    ["theme_04#F4.1","theme_04#F4.2"],["Wang 2023, Glia; J Neurosci 2026 (2-DG attenuates hypersensitivity)"],"Tool specificity caveats apply")
add("QC-0086",EX,"Urolithin A mitophagy claim extended by senescence/mitophagy targeting wave in microglia.",
    ["theme_03#F3.10"],["Aging Cell 2025; Neurosci Biobehav Rev 2026"],"Promote urolithin A to graph node per theme 3 suggestion")
add("QC-0087",EX,"Nicotinamide riboside CIPN claim extended within mitochondrial-restoration/senescence frame.",
    ["theme_03#F3.10"],["Neurosci Biobehav Rev 2026"],"Source-level verification advised")
add("QC-0088",C,"Target-occupancy/translation difficulty confirmed: partial responder rates 30-70% despite >99% occupancy.",
    ["theme_06#F6.1","theme_06#F6.2"],["Bertoch et al. 2025, Anesthesiology 142:1085; Stewart et al. 2025, PNAS"],
    "Nav1.7 retains AP-initiation role under suzetrigine - multi-channel cotargeting implication")
add("QC-0089",C,"EP1-on-infiltrating-macrophages finding untouched by EP2-refutation and EP1 relevance reconfirmed via ONO-8711 lineage.",
    ["theme_07#F7.12","theme_07#F7.18"],["ONO-8711 CCI classic (PMID 11574375); Nat Commun 2025 EP2/Schwann cell"],
    "EP-subtype attribution field contested (EP2/Schwann-cell vs legacy EP4) - keep EP1 scoping explicit")
add("QC-0090",C,"Local ketorolac reversing PSNL allodynia >5 days uncontested; CREB-phosphorylation suppression mechanism-consistent.",
    ["theme_07#F7.18","theme_09#F9.13"],["Kawasaki et al. 2008, J Neurosci 28:5189 (PICs->pCREB)"])
add("QC-0091",C,"NrCAM exon-10 ASO partial reversal within 72 h matches primary literature almost verbatim.",
    ["theme_06#F6.6"],["Liang et al. 2020, J Pain 21:625; He et al. 2023, Neurotherapeutics"],
    "Behavioral rescue incomplete even with normalized splice ratios")
add("QC-0092",UR,"Strategic-roadmap delivery claim outside themes.",
    [],[])
add("QC-0093",UR,"Wnt time-course claim outside themes.",
    [],[])

# ---- assemble & validate ----
claims = json.load(open("analysis/claims/claims.json"))
ids = {c["id"] for c in claims}
out_ids = {e["claim_id"] for e in E}
missing = ids - out_ids
extra = out_ids - ids
assert not missing, f"MISSING: {sorted(missing)}"
assert not extra, f"EXTRA: {sorted(extra)}"
assert len(E) == len(claims) == 262, (len(E), len(claims))

E.sort(key=lambda e: e["claim_id"])
with open("analysis/claims/verdicts.json","w") as f:
    json.dump(E, f, indent=2, ensure_ascii=False)

hist = collections.Counter(e["verdict"] for e in E)
prio = {c["id"]: c["priority"] for c in claims}
verdict_of = {e["claim_id"]: e["verdict"] for e in E}
cov = {}
for band in ("P0","P1"):
    ids_b = [i for i,p in prio.items() if p==band]
    rev = sum(1 for i in ids_b if verdict_of[i] in (C,EX,RF,MX))
    cov[band] = (len(ids_b), rev, round(100*rev/len(ids_b),1))
print("histogram:", dict(hist))
print("total:", len(E))
for b,(n,r,pct) in cov.items():
    print(f"{b}: {r}/{n} reviewed = {pct}%")
rf = sorted(i for i in ids if verdict_of[i]==RF)
mx = sorted(i for i in ids if verdict_of[i]==MX)
print("REFUTED:", rf)
print("MIXED:", mx)
