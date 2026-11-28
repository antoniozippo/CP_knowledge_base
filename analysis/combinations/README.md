# Combination experiments as a test of the functional model (scope phase 4)

Published combination experiments (two or more interventions given together, one readout) from the
combinations pass (`crawler/extractions/combinations/`, 240 rodent nerve-injury papers, 635 records),
scored against the Netflux model of phase 3 and its baselines.

    python3 analysis/scripts/evaluate_combinations.py

| File | Contents |
|---|---|
| `grounding.yaml` | Hand-entered map from intervention strings to HGNC symbols (unchecked) |
| `cases.csv` | The 72 scored cases: observed and predicted directions and interaction classes |
| `results.md` | Funnel and scores |

## Verdict

**The functional model does not predict interaction classes, and on these cases it is no better than
static paths at direction.** Details in `results.md`.

- **Interaction class** (62 cases with a class): 52 are "less than additive" (occlusion, antagonism, no
  added effect, sub-additive), 9 synergy, 1 additive. Netflux (mean logic, the phase-3 setting) answers
  "additive" on almost every case it calls (39 calls, 1 right); static paths are additive by
  construction (1/62). Always answering "less than additive" is right on 52/62 (84%).
  The model cannot produce occlusion because its inputs combine nearly linearly at these scales.
- **Direction** (one intervention alone, 69 cases with a direction): netflux 29%, static 41%, the
  actor's usual sign 32%, with many no-calls (an isolated or unlinked actor means "no change", scored
  wrong). The majority direction is right on 62%. These numbers are far below the 90% of phase 3
  because the actors here are not the ones the network was built around: drugs with an unclear target
  and natural products have no links, so most cases are no-calls rather than wrong calls.
- **Coverage is the limit**: 550 in-context records, 109 with both interventions and the readout
  grounded, 72 with two different nodes. The long tail is natural products, foods, acupuncture,
  lncRNAs and receptors with no gene mapping.

## What this does and does not show

- It shows the current model cannot be used to predict combination effects, and that a combination
  benchmark can tell models apart where single perturbations could not (every method scores
  about the same there; here additive and non-additive models separate immediately).
- It does not show that no dynamic model could. Occlusion (a drug blocked by its antagonist or lost in a
  knockout) needs the drug's effect to pass through a node the second intervention removes. A model
  with the drug-to-target link and a single path to pain would produce it. Most of the 72 cases lack the
  links, so the model is not given the chance.
- The interaction labels are a worker session's judgement (129 of 635 inferred, none expert-checked)
  and 16 of 62 classed cases are inferred. Same-node pairs (drug and its own antagonist, 37) are excluded
  as untestable by clamping.

## Step 2: can the model express occlusion when the structure allows it? (2026-11-28)

Drugs are already clamped at their gene targets here, so what step 2 tests is the combination rule.
Three Netflux rules (mean inputs, OR, OR scaled by input count) and a structural rule (an intervention
that reaches the other within three links makes the pair less than additive) were declared before
scoring; none was selected on these cases (`results.md`, last table).

- **No Netflux rule predicts occlusion.** Across mean, OR and OR-scaled, "less than additive" is
  called on none of the 52 cases that have it (OR also makes only 16 calls: it saturates). Mean and
  OR-scaled call "additive" or "synergy" instead. Dynamics alone do not produce occlusion here.
- **The structural rule is right when it applies and silent otherwise.** It finds an upstream pair in
  12 of 62 classed cases and is right on 9 of the 12 less-than-additive ones it flags (precision 9/12).
  It covers 9 of the 52 less-than-additive cases: for the rest, the network holds no path linking the
  two interventions. Overall 10/62 (16%), against 84% for always answering "less than additive".
- So the limit is missing links between the interventions, not the update rule. Occlusion cases are
  mostly a drug and a second intervention on a mechanism the network does not connect.

## Next steps (not started)

1. Expert check of a sample of records (interaction class and direction); the labels bound every figure.
2. Add the missing mechanism links (the two interventions of an occlusion record are connected by the
   paper's own mechanism claim) as a test of whether a model given them then reproduces the label;
   this uses the answer as an input and can only show consistency.
3. Magnitudes and time courses, which no extraction yet records.
