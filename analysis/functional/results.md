# Functional model: results (scope phase 3)

Built by `analysis/scripts/evaluate_functional_model.py` on `analysis/canonical/network.json` and the 89 scorable cases. See `README.md` for the methods and caveats.

Majority implied sign among build cases: -1 (40 of 68).

## Accuracy: did the method predict the direction the readout moved?

Build cases: leave-one-paper-out. Test cases: papers after the test cut, never in the network. A prediction of no change counts as wrong.

`netflux` is the default fixed before scoring; `netflux_best` the setting chosen on build cases only (sweep below).

| Method | Build (leave one paper out) | Test (held out) |
|---|---|---|
| netflux | 2/68 = 3% (95% CI 1-10), 66 no call | 2/21 = 10% (95% CI 3-29), 19 no call |
| netflux_best | 61/68 = 90% (95% CI 80-95), 2 no call | 20/21 = 95% (95% CI 77-99) |
| boolean | 0/68 = 0% (95% CI 0-5), 68 no call | 0/21 = 0% (95% CI 0-15), 21 no call |
| boolean_threshold | 0/68 = 0% (95% CI 0-5), 68 no call | 0/21 = 0% (95% CI 0-15), 21 no call |
| static | 62/68 = 91% (95% CI 82-96), 2 no call | 19/21 = 90% (95% CI 71-97) |
| source | 59/68 = 87% (95% CI 77-93), 2 no call | 19/21 = 90% (95% CI 71-97) |
| majority | 40/68 = 59% (95% CI 47-70) | 17/21 = 81% (95% CI 60-92) |

### Drug cases

| Method | Build | Test |
|---|---|---|
| netflux | 2/46 = 4% (95% CI 1-15), 44 no call | 1/16 = 6% (95% CI 1-28), 15 no call |
| netflux_best | 42/46 = 91% (95% CI 80-97) | 15/16 = 94% (95% CI 72-99) |
| boolean | 0/46 = 0% (95% CI -0-8), 46 no call | 0/16 = 0% (95% CI 0-19), 16 no call |
| boolean_threshold | 0/46 = 0% (95% CI -0-8), 46 no call | 0/16 = 0% (95% CI 0-19), 16 no call |
| static | 41/46 = 89% (95% CI 77-95), 1 no call | 14/16 = 88% (95% CI 64-97) |
| source | 38/46 = 83% (95% CI 69-91), 2 no call | 14/16 = 88% (95% CI 64-97) |
| majority | 38/46 = 83% (95% CI 69-91) | 15/16 = 94% (95% CI 72-99) |

### Knockdown or overexpression cases

| Method | Build | Test |
|---|---|---|
| netflux | 0/22 = 0% (95% CI 0-15), 22 no call | 1/5 = 20% (95% CI 4-62), 4 no call |
| netflux_best | 19/22 = 86% (95% CI 67-95), 2 no call | 5/5 = 100% (95% CI 57-100) |
| boolean | 0/22 = 0% (95% CI 0-15), 22 no call | 0/5 = 0% (95% CI -0-43), 5 no call |
| boolean_threshold | 0/22 = 0% (95% CI 0-15), 22 no call | 0/5 = 0% (95% CI -0-43), 5 no call |
| static | 21/22 = 95% (95% CI 78-99), 1 no call | 5/5 = 100% (95% CI 57-100) |
| source | 21/22 = 95% (95% CI 78-99) | 5/5 = 100% (95% CI 57-100) |
| majority | 2/22 = 9% (95% CI 3-28) | 2/5 = 40% (95% CI 12-77) |

## Where the model and the majority baseline disagree

Agreement with a baseline earns nothing; these cases are where a model has to show what it adds.

- netflux: disagrees on 85 cases; right on 0, the majority baseline right on 53
- netflux_best: disagrees on 29 cases; right on 26, the majority baseline right on 2
- boolean: disagrees on 89 cases; right on 0, the majority baseline right on 57
- boolean_threshold: disagrees on 89 cases; right on 0, the majority baseline right on 57
- static: disagrees on 33 cases; right on 28, the majority baseline right on 4
- source: disagrees on 33 cases; right on 27, the majority baseline right on 6

## Head to head

- netflux_best vs static: disagree on 6 cases; netflux_best right on 3, static right on 3
- netflux_best vs source: disagree on 10 cases; netflux_best right on 6, source right on 3
- static vs source: disagree on 6 cases; static right on 4, source right on 1

## Cases a direct link already answers

37 of 89 scorable cases have a direct actor -> readout link from another paper (or the dossiers). Its sign alone is right on 36 of them. Only the 52 cases without one test reasoning over the network:

| Method | Cases with a direct link | Cases without one |
|---|---|---|
| netflux | 3/37 = 8% (95% CI 3-21), 34 no call | 1/52 = 2% (95% CI 0-10), 51 no call |
| netflux_best | 36/37 = 97% (95% CI 86-100) | 45/52 = 87% (95% CI 75-93), 2 no call |
| boolean | 0/37 = 0% (95% CI 0-9), 37 no call | 0/52 = 0% (95% CI 0-7), 52 no call |
| boolean_threshold | 0/37 = 0% (95% CI 0-9), 37 no call | 0/52 = 0% (95% CI 0-7), 52 no call |
| static | 34/37 = 92% (95% CI 79-97) | 47/52 = 90% (95% CI 79-96), 2 no call |
| source | 34/37 = 92% (95% CI 79-97) | 44/52 = 85% (95% CI 72-92), 2 no call |
| majority | 25/37 = 68% (95% CI 51-80) | 32/52 = 62% (95% CI 48-74) |

## Netflux parameter sweep (build cases only)

54 settings: logic OR (Netflux), OR with inputs scaled by their number, or mean of inputs; basal input 0.05/0.1/0.25; tier weights uniform or tiered (T1 1, T2 0.8, T3 0.5, P 0.6); all links, without T3, or without the prior. Hill exponent 1.4, EC50 0.5.

| Build correct | Setting |
|---|---|
| 61/68 | {'logic': 'mean', 'basal': 0.25, 'n': 1.4, 'ec50': 0.5, 'weights': 'tiered', 'tiers': 'all'} |
| 60/68 | {'logic': 'or-scaled', 'basal': 0.1, 'n': 1.4, 'ec50': 0.5, 'weights': 'uniform', 'tiers': 'all'} |
| 60/68 | {'logic': 'or-scaled', 'basal': 0.1, 'n': 1.4, 'ec50': 0.5, 'weights': 'tiered', 'tiers': 'all'} |
| 60/68 | {'logic': 'or-scaled', 'basal': 0.25, 'n': 1.4, 'ec50': 0.5, 'weights': 'uniform', 'tiers': 'all'} |
| 60/68 | {'logic': 'or-scaled', 'basal': 0.25, 'n': 1.4, 'ec50': 0.5, 'weights': 'tiered', 'tiers': 'all'} |
| 60/68 | {'logic': 'mean', 'basal': 0.1, 'n': 1.4, 'ec50': 0.5, 'weights': 'uniform', 'tiers': 'all'} |
| 2/68 | {'logic': 'or', 'basal': 0.1, 'n': 1.4, 'ec50': 0.5, 'weights': 'uniform', 'tiers': 'no prior'} |
| 2/68 | {'logic': 'or', 'basal': 0.25, 'n': 1.4, 'ec50': 0.5, 'weights': 'uniform', 'tiers': 'all'} |
| 1/68 | {'logic': 'or', 'basal': 0.05, 'n': 1.4, 'ec50': 0.5, 'weights': 'uniform', 'tiers': 'all'} |

Best on build: {'logic': 'mean', 'basal': 0.25, 'n': 1.4, 'ec50': 0.5, 'weights': 'tiered', 'tiers': 'all'}, 61/68 (`netflux_best` in the tables above, read once on the test cases). `netflux` is the default fixed before scoring.

