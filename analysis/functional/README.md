# Functional model (scope phase 3)

The canonical network (`analysis/canonical/`) run as an executable model and scored on the
validation set (`analysis/perturbation/`): for each experiment, does the model predict the direction
the readout moved when the actor was perturbed?

    python3 analysis/scripts/evaluate_functional_model.py

## Files

| File | Contents |
|---|---|
| `results.md` | Accuracy of every method on build and test cases, by kind, head to head, by whether a direct link exists, and the parameter sweep |
| `predictions.csv` | Each case's prediction from each method |
| `model.yaml` | The Netflux setting carried forward (chosen on build cases) |

Engine: `analysis/scripts/functional_model.py`. Evaluation: `analysis/scripts/evaluate_functional_model.py`.

## Methods

| Method | What it does |
|---|---|
| `netflux` | Normalized-Hill ODEs, default fixed before scoring: activators OR, inhibitors AND NOT, basal input 0.1, every link weight 1 |
| `netflux_best` | The same engine with the setting that scored best on build cases (`model.yaml`): inputs averaged instead of OR-ed, basal 0.25, link weights by evidence tier |
| `boolean`, `boolean_threshold` | On/off versions (OR logic, or on when more activators than inhibitors are on) |
| `static` | Sign of the summed signed paths of up to 3 links |
| `source` | The actor's usual sign (the sign of its out-links) |
| `majority` | The commoner implied sign of the build cases |

- **Perturbations.** A loss clamps the actor to 0; a gain or a drug clamps it to 1.
- **Baseline state.** Drugs, interventions and other diseases are off at baseline. There is no
  injury node in the network, so the baseline is a uniform basal state.
- **Leakage.** Build cases are scored leave-one-paper-out. Test cases come from papers after the
  test cut, which were never in the network.
- **Scoring.** A prediction of no change counts as wrong.

## Results

| Method | Build (68, leave one paper out) | Test (21, held out) |
|---|---|---|
| netflux (pre-registered default) | 3% (66 no call) | 10% (19 no call) |
| **netflux_best** | **90%** (61) | **95%** (20) |
| boolean, boolean_threshold | 0% (no calls) | 0% (no calls) |
| static paths | 91% (62) | 90% (19) |
| source tendency | 87% (59) | 90% (19) |
| majority sign | 59% (40) | 81% (17) |

On the 52 cases where no direct link from another paper already gives the answer, so that the
prediction must come from reasoning over the network: netflux_best 87%, static paths 90%, source
tendency 85%, majority 62%.

## Verdict: go/no-go

**The criterion set for this phase, that the dynamic model beat static paths, is not met.**

- The normalized dynamic model ties static paths. They disagree on 6 cases and each is right on 3.
  Both clearly beat the majority baseline. Both beat the actor's usual sign only slightly (on the
  test cases, not at all).
- **Most of the signal is the kind of actor.** "Drugs and anti-inflammatory molecules lower pain
  and inflammation; pro-inflammatory molecules raise them" explains about 85–90% of these cases.
  Single-perturbation directions cannot tell a dynamic model from a static one, because they do not
  exercise what dynamics adds: saturation, feedback, compensation and combinations.
- **The pre-registered default failed** for a mechanical reason. With every weight at 1 and OR
  logic, hubs with dozens of inputs (PAIN, TNF, TRPV1) saturate, and removing one input changes
  nothing (no call in 85 of 89 cases). Averaging the inputs fixes this. That fix was chosen
  after seeing build results; the test set was read once with it. Picking the best of 54 settings
  makes the build figure optimistic. The test figure (20 of 21, 95% CI 77–99%) is the honest one.
- **The Boolean models make no calls at all.** On a network this dense, every readout is on whatever
  single node is clamped. They are not useful here without weights.

## What this means for the project's goal

The model is usable for **hypothesis generation with a stated accuracy**: about 90% for the
direction of single perturbations in its context, with wide intervals. That is roughly what
simpler methods achieve. Whether it predicts **combinations** (synergy, redundancy) or **dynamics**
(onset, chronic drift) better than static reasoning is untested, because the validation set has
neither.

Before building combination experiments on it (phase 4):

1. **Expert adjudication** of `analysis/perturbation/adjudication_sample.csv`: the error rate of the
   cases bounds every figure above.
2. **Validation data that can tell models apart.** Published combination experiments (two drugs,
   or a drug in a knockout), magnitudes rather than directions, and time courses. The crawl does
   not extract any of these yet; the extraction schema would need fields for them.
3. **An injury input.** The baseline is a uniform basal state, not an injured network. The network
   has no node for the injury itself.
4. **Check the hand-entered drug targets** against ChEMBL when it can be reached.
