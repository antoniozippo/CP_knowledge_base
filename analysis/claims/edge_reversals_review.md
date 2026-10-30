# Edge-direction audit: items held for human review

Companion to `analysis/claims/edge_reversals.yaml` (applied by
`analysis/scripts/reverse_edges.py`). Audit date 2026-10-30, over all 260
signed links in `graphify-out/graph_v2.json` (225 extracted + 35
`dynamic_closure`).

## Method

A link was a candidate when the stored target is a drug, tool, intervention,
injury model or upstream regulator of the stored source (entity_type drug;
labels with inhibitor/antibody/shRNA/AAV/KO/model/stimulation/enrichment;
transcription factors, phosphatases, feedback regulators), or when the
relation text describes an action of the target on the source. Each
candidate was checked against its `source_file` dossier (`source_location` is
null on these links, so the dossier was searched for the statement) and
against `analysis/claims/verdicts.json`, where about 20 reviewers had already
written "predicate inverted" / "fix direction".

Result: 40 curated entries. 38 are `reverse` (swap endpoints, keep relation
and sign); 2 are `neutralize`, because the corrected orientation already
exists as another link:

- `ana_12_TrkB_T1 -inhibits-> ana_12_ANA_12` duplicates the existing
  `ana_12_ANA_12 -inhibits-> ana_12_TrkB_T1` edge.
- `bbb_bbb -disrupts(-1)-> AngPt_angiopoietin_2` duplicates the closure edge
  `AngPt_angiopoietin_2 -disrupts(+1)-> bbb_bbb`.

Validation statuses are unchanged. The ACC Kalirin-7 downregulation edges
(SNI/CCI → Kalirin-7) stay REFUTED. Per theme_10 F10.1 that narrative is
unsupported, and correcting its direction is not new evidence for it.

`analysis/claims/claims.json` still words EC-0013, EC-0022, EC-0026 and the
other affected claims in the old orientation. Card claim matching is
direction-agnostic, so `claim_refs` still resolve. The claim text was not
rewritten.

## Not reversed: direction ambiguous or not a pure swap

| Stored link | Why held back |
|---|---|
| `bbb_bbb -restores_integrity_of(+1)-> bbb_rvd1_barrier_reseal` (EC-0014) | BBB.md:32 supports RvD1 → barrier. The corrected sign depends on `bbb_bbb` polarity. Closure edges `vegf_VEGFA -disrupts(+1)->` and `AngPt_angiopoietin_2 -disrupts(+1)-> bbb_bbb` encode disruption as +1 (high = leak), but closure `BDNF -supports_integrity_via_tight_junctions(+1)-> bbb_bbb` encodes integrity as +1. Resolve the polarity first. |
| `bbb_bbb -stabilizes(+1)-> AngPt_angiopoietin_1` (EC-0015) | Same polarity issue (AngPt.md:9: Ang-1 promotes barrier integrity). |
| `BBB_tight_junction_proteins -downregulates(-1)-> vegf_VEGFR2` (EC-0119) | vegf.md:20 names VEGFA, not VEGFR2, as the tight-junction downregulator. The verdict asks to fix direction *and source*. |
| `igf_igf2 -stabilizes_mrna_of(+1)-> igf_igf2bp2` (EC-0044) | IGF1-2.md:21 says IGF2BP2 stabilizes transcripts but "is not IGF2 itself". The verdict flags possible IGF2/IGF2BP2 entity conflation. |
| `shared_nfkb -activates(+1)-> tnf_tnfr1` (EC-0083) | TNFR1 → NF-κB is canonical, but TNF.md does not state it and the reviewer CONFIRMED the stored reading ("NF-kB-driven TNFR1 program"). |
| `pnn_ecm_mmp9 -upregulates_via_rhoa_rock(+1)-> nogoa_ngr1_ngr1` (EC-0151) | NogoA-NgR1.md:65 reads Nogo-A/RhoA → MMP-9, but the reviewer CONFIRMED the stored direction. Conflicting sources. |
| `PV_interneurons_PV_interneurons -impairs_via_kcc2_bdnf(-1)-> il6_jak_stat3` (EC-0155) | JAK-STAT.md:87 has STAT3 → BDNF↑/KCC2↓ without naming PV. The reviewer kept the stored reading ("PV-KCC2/BDNF state modulates JAK/STAT tone"). |
| `RhoA_ROCK_RhoA -activates_via_lpar1(+1)-> rhoa_rock_lpa_demyelination` (EC-0108) | The target is the whole LPA–RhoA–demyelination cascade. LPA is upstream and demyelination downstream of RhoA (RhoA-ROCK.md:26), so either direction is partly true. |
| `autophagy-apoptosis_inhibition_Beclin_1 -inhibits(-1)-> GABA_apoptosis_mTORC1` (EC-0144) | GABA_apoptosis.md:31 has mTORC1 suppressing autophagy initiation. A Beclin-1 target is not stated, so this needs a new relation, not a swap. |
| `autophagy-apoptosis_inhibition_Beclin_1 -causes(+1)-> GABA_apoptosis_Calpain` (EC-0143) | GABA_apoptosis.md:30: calpain *cleaves* Beclin-1. The fix needs both a reversal and sign -1 (relation `causes` is wrong). |

## Direction correct, sign wrong (out of scope for reversal)

| Stored link | Issue |
|---|---|
| `karilin7_Kalirin7 -loss_causes(+1)-> karilin7_PainRelatedAnxiety` | "Loss causes" means Kal7↓ → anxiety↑, so the sign should be -1. This is the double-weighted driver of the pain readout described in the `facts.yaml` notes. The `rationale_for(+1)` parallel edge has the same problem. |
| `karilin7_Kalirin7 -loss_causes(+1)-> karilin7_DendriticSpineLoss` | Same as above (and its `rationale_for(+1)` parallel edge). |
| `gaba_apoptosis_cpampar -causes_excitotoxic_death_in(+1)-> PV_interneurons_PV_interneurons` | Death lowers PV, so the sign should be -1. |
| `PV_interneurons_PV_interneurons -hyperactivates_when_pv_fails(+1)-> SST_somatostatin_interneurons` (EC-0154) | PV failure raises SST (SST.md:16), so the sign should be -1. |

## Simulation note: the Ang-2 neutralization

Neutralizing `bbb_bbb -disrupts(-1)-> AngPt_angiopoietin_2` removes a
negative feedback (a disrupted barrier pushing Ang-2 down) that the
literature does not support. Without it, the closure loop
Ang-2 → microglia/TNF → HIF1α → Ang-2 (plus Ang-2 → BBB) becomes
self-sustaining, and two facts fail:

- F-03: the TNF gap after drive decay is ~0.05, below the 0.10 threshold.
- F-16: the XPro1595 inflammation reduction is ~0.014, below the 0.02 threshold.

The other 39 entries keep all 19 facts passing. Options:

1. Recalibrate F-03/F-16.
2. Re-examine the Ang-2 closure edges, which are INFERRED_CLOSURE topology.
3. Drop the entry from `edge_reversals.yaml`.
