# The Lamina I Projection-Neuron Double Hit — PNN Stripping Plus KCC2 Failure

*Generated from inference round 2026-08: hypothesis H2 of analysis/hypotheses.md — resolves the EC-0070 contradiction (Theme 1 F1.13 ↔ Theme 2 F2.3); structural origin LC-0053*

## Summary

The strongest new mechanistic fact of the validation round is a **cell-type retargeting**: after nerve injury, microglia degrade perineuronal nets that selectively enwrap **lamina I spinoparachial projection neurons** — not PV interneurons — and this GAG stripping alone promotes pain [Tansley et al., Science 377:80–86, 2022]. Combined with the human-anchored disinhibition cascade, this yields a **dual-hit model**: allodynia requires coincident (1) microglial PNN removal from projection neurons and (2) KCC2-dependent weakening of inhibitory control onto those same cells. Either hit alone is compensated.

## The Two Hits

```
HIT 1 (permissive): microglial phagocytic GAG stripping
   → WFA loss on lamina I spinoparabrachial projection neurons
   → projection-neuron hyperexcitability (aggrecan core preserved)

HIT 2 (amplifying): BDNF-TrkB / PKC-driven KCC2 downregulation
   → PV + NPY inhibitory output weakened
   → unrestrained projection-neuron firing

ALLodynia = HIT 1 × HIT 2  (compensation window if only one)
```

*Sources: Tansley Science 2022; Mol Pain 19 (2023); Qiu PNAS 2024; Mapplebeck Cell Rep 2019*

## Region-Conditioned Sign Table

The KB's uniform "PNN loss → disinhibition → pain" framing must be split by region:

| Region | PNN perturbation | Pain effect | Key source |
|---|---|---|---|
| Spinal lamina I | Microglial GAG stripping of projection-neuron nets | Pronociceptive | Tansley, Science 2022 |
| Somatosensory cortex / reticular thalamus | PNN build-up; chABC analgesic; MMP-9 KD lowers sham thresholds | PNN accumulation pronociceptive (sign inverted) | Mascio, Pain 2025 (PMC12004981) |
| Spinal lamina I (enzymatic) | Intrathecal chABC in CCD rats: WFA loss → neuronal Ca²⁺ overload → hyperalgesia | Pronociceptive | Front Mol Neurosci 2026, doi:10.3389/fnmol.2026.1860375 |
| SCI repair context | chABC promotes sprouting without allodynia | Safe/pro-regenerative | Cafferty J Neurosci 2008; Chase Nat Neurosci 2019 |

## Relation to Prior Claims

- **Corrects EC-0070**: cell type reassigned from PV interneurons to lamina I spinoparabrachial projection neurons (Tansley 2022); dominant early degradative step is phagocytic GAG removal ± MMP-9, not aggrecan-core proteolysis.
- **Corrects the PNN_ECM cortical section**: forebrain sign inversion (Mascio 2025) demands region-conditioned edge signs.
- **Extends EC-0093**: PNN-degradation → Ca²⁺-overload direction now experimentally demonstrated.
- **Extends EC-0099/EC-0097**: firing-pattern restoration readout added (Qiu PNAS 2024); both-sexes evidence (Tansley) tempers male-bias caution for this specific mechanism.
- **Structural seed (LC-0053)**: the graph already pairs "PV Inhibition KCC2-Dependency" with the NK1 receptor community via shared BDNF/KCC2 neighbors — the projection-neuron identity (classically NK1R⁺/TACR1⁺) should be re-verified against the Tansley population by co-labeling.

## Testable Predictions

1. WFA-stripped nets co-localize with NK1R⁺ spinoparabrachial neurons (immunostaining in SNI, both sexes).
2. Restoring KCC2 selectively in PV+ or NPY+ interneurons (AAV) blunts allodynia induced by lamina-I chABC more than expected additively (synergy = dual-hit confirmation).
3. Projection-neuron Ca²⁺ transients in behaving mice show compensation (normal firing) after either single perturbation but not both.
4. Early-window MMP-9 inhibition (AZD1236-class, within 24–72 h per Kawasaki-phase logic) prevents Hit 1 and thereby blocks the transition even when Hit 2 proceeds.

## Limitations

NK1R identity of the stripped population is classical inference, not yet demonstrated in the Tansley preparation. Single-hit sufficiency in some models (PV ablation alone; Petitjean 2015 lineage) would falsify the compensation requirement. WFA-only readouts overstate degradation when aggrecan cores survive (methodological caveat from Theme 2).
