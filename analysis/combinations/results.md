# Functional model on combination experiments: results (scope phase 4)

Built by `analysis/scripts/evaluate_combinations.py` from `crawler/extractions/combinations/`. Links are leave-one-paper-out; the model is the Netflux setting chosen in phase 3 (`analysis/functional/model.yaml`). Interaction labels are the extracting session's judgement (stated in the paper for most, inferred for the rest); none has been checked by an expert.

## Funnel

- total: 635
- in vivo, rodent nerve injury: 550
- interventions and readout grounded: 109
- same node twice (not testable): 37
- distinct-node pairs: 72
- scored (isolated nodes included; no path means no call): 72

## Direction of the readout

Observed direction is the paper's, expressed as pain (threshold readouts flipped). A prediction of no change counts as wrong. `source` is the actor's usual sign.

| Method | One intervention alone | The combination (where the readout moved) |
|---|---|---|
| net | 20/69 = 29% (95% CI 20-41), 43 no call | 14/33 = 42% (95% CI 27-59), 12 no call |
| static | 28/69 = 41% (95% CI 30-52), 38 no call | 24/33 = 73% (95% CI 56-85), 6 no call |
| source | 22/69 = 32% (95% CI 22-44), 40 no call | 19/33 = 58% (95% CI 41-73), 10 no call |

Majority direction (-1) would be right on 43/69 (one alone).

Majority direction (-1) would be right on 24/33 (combination).

## Interaction class

62 cases have a class. Observed: less than additive 52, synergy 9, additive 1.

| Method | Right | Calls |
|---|---|---|
| netflux | 1/62 = 2% (95% CI 0-9) | made a call on 39 |
| static paths (always additive) | 1/62 = 2% (95% CI 0-9) | made a call on 62 |
| always "less than additive" (majority) | 52/62 = 84% (95% CI 73-91) | all |

Where netflux made a call: ('additive', 'less than additive') 29, ('additive', 'synergy') 9, ('additive', 'additive') 1 (predicted, observed).


### Other combination rules and a structural rule

`or`: activators OR-ed (saturates); `or-scaled`: OR with inputs scaled by their number; `mediation`: less than additive when one intervention reaches the other within three links, else additive. Declared before scoring; no rule was selected on these cases.

| Rule | Right | Calls | Per class (right/observed) |
|---|---|---|---|
| mean | 1/62 = 2% (95% CI 0-9) | 39 | less than additive 0/52, synergy 0/9, additive 1/1 |
| or | 0/62 = 0% (95% CI -0-6) | 16 | less than additive 0/52, synergy 0/9, additive 0/1 |
| or-scaled | 1/62 = 2% (95% CI 0-9) | 40 | less than additive 0/52, synergy 0/9, additive 1/1 |
| mediation | 10/62 = 16% (95% CI 9-27) | 62 | less than additive 9/52, synergy 0/9, additive 1/1 |

Mediation: 12 of 62 classed pairs have one intervention upstream of the other.
On the 47 cases whose interaction the paper states: netflux right on 1, majority right on 43.
