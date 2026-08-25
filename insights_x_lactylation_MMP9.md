# Histone Lactylation as the Phase Gate on the MMP-9 Switch

*Generated from inference round 2026-08: hypothesis H3 of analysis/hypotheses.md — merges Theme 2 (MMP-9/ELF1/DRGX) with Themes 4/9 (lactylation machinery); structural origin LC-0049*

## Summary

Three independently validated findings have never been joined at the chromatin level: (1) MMP-9's pronociceptive action is **phase-structured** — rapid, transient DRG upregulation gates early-phase allodynia (Kawasaki 2008, intact through 2025 reviews); (2) injury derepresses *Mmp9* transcriptionally via **ELF1** and loss of the restraint factor **DRGX**; (3) the **lactylation machinery** (LDHA → lactate → p300 → histone Kla) is causal in injured DRG and pharmacologically reversible. The hypothesis: **histone lactylation marks at the Mmp9 locus are the permission step** that opens the early-phase switch — making glycolysis/lactylation blockade a windowed preventive for acute-to-chronic transition.

## The Regulatory Architecture

```
DEVELOPMENT/ADULT BASELINE
   DRGX (protective TF) ⊣ Mmp9

NERVE INJURY (early phase, hours–days)
   DRGX ↓ (SNL, small/medium DRG neurons)
   ELF1 ↑ → binds Mmp9 promoter
   Glycolytic shift (AREG-EGFR-PKM2 / HK2 / LDHA) → lactate ↑
   p300 → H3K18la / H4K8la @ pronociceptive loci   ← PROPOSED PERMISSION STEP
   → MMP-9 surge → IL-1β cleavage + microglial activation + BSCB opening
   → EARLY allodynia

LATE PHASE (days–weeks)
   lactylation marks decay (predicted) · MMP-2 takes over maintenance
```

*Sources: Mol Pain 2020;16:33 (DRGX); PMC9633582 (ELF1); Kawasaki Nat Med 2008; Wang J Neurosci 2025; Deng Sci Signal 2025*

## Evidence Base

| Layer | Source | Finding |
|---|---|---|
| Phase structure | Kawasaki et al., Nat Med 2008;14:331 | Early MMP-9 / late MMP-2; TIMP-1 effective early only; reconfirmed through 2025 reviews |
| Transcriptional initiator | ELF1 study, PMC9633582 (~J Neurosci 2022/23) | AAV-shRNA Elf1 blocks CCI-induced MMP-9 upregulation and hypersensitivity, both sexes |
| Restraint factor (corrected polarity) | Mol Pain 2020;16:33 (PMC7099666) | DRGX down after SNL; knockdown induces pain; overexpression restrains MMP-9 |
| Lactylation causality | Wang Q-H et al., J Neurosci 2025, DOI 10.1523/jneurosci.0365-25.2025 | H3K18la→IGF2BP2→CCT2 causal; 2-DG/lactate manipulations bidirectional |
| Upstream metabolic driver | Deng et al., Sci Signal 2025;18(891):eadr9397 | AREG→EGFR→PKM2→glycolysis→p300-lactylation in sensory neurons |
| Repressive-mark precedent | Nat Commun 2025, DOI 10.1038/s41467-025-62343-3 | H4K8la represses DOCK4 → Nav1.7 trafficking failure (shows repressive lactylation logic exists in DRG) |

## Relation to Prior Claims

- **Corrects EC-0031…EC-0034 (REFUTED)**: DRGX is protective, not pronociceptive — its loss derepresses MMP-9. All downstream "pronociceptive gene programme" edges are replaced by the inverted graph.
- **Extends EC-0070…EC-0074**: adds an upstream transcriptional/chromatin architecture above the MMP-9 hub and makes the phase windows mechanistically explicit.
- **Extends QC-0071** with a locus-level prediction (Mmp9 promoter marks) while respecting its model-specificity annotation (H3K18la robust in CCI; unchanged in SNL where H4K8la rose).
- **Connects EC-0120** (transient acute-to-chronic prevention): if the gate is early-window chromatin, prevention protocols gain a molecular deadline.

## Testable Predictions

1. CUT&RUN/ChIP-qPCR for H3K18la, H4K8la, p300, ELF1 at the *Mmp9* promoter in L4/5 DRG at 6 h / 24 h / 72 h / day 7 post-SNI — predict early peak decaying before the MMP-2-dominated phase.
2. Intrathecal 2-DG or DRG-specific LDHA knockdown within 24 h blunts *Mmp9* mRNA induction and early allodynia without touching baseline sensation.
3. Sodium lactate into uninjured DRG ± ELF1 overexpression suffices to induce MMP-9 and mechanical hypersensitivity.
4. In CCI-vs-SNL comparison, the mark type tracks the model annotation from QC-0071 (H3K18la-dominant vs H4K8la-shifted).

## Limitations

The junction itself is untested — no published ChIP of lactylation marks at *Mmp9* exists; lactylation may act exclusively through its validated targets (*Igf2bp2*, *Dock4*) leaving MMP-9 regulation purely TF-level. Mark heterogeneity across models could confine the hypothesis to a CCI-type subset. FX11-class quantitative figures in the KB remain UNVERIFIED pending primary-source checks.
