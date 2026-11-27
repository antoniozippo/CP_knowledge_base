# Perturbation validation set: summary

Context: rodent peripheral nerve injury. Built by `analysis/scripts/build_perturbation_cases.py` from `crawler/extractions/`; see `README.md` for the rules.

- candidate cases (a perturbation quote whose readout is pain behaviour or a marker): 768
- primary cases: 189 from 145 papers, 149 actors
- split by PubMed entry order: build 144, test 45 (PMID >= 40209863)

## Why candidates were excluded

| Status | Cases |
|---|---|
| excluded: other or unstated model | 265 |
| primary | 189 |
| excluded: other model (quote) | 129 |
| excluded: actor not in graph | 77 |
| excluded: drug and its own target | 44 |
| excluded: perturbation unclear | 34 |
| excluded: cell culture (quote) | 11 |
| excluded: nerve injury, species unclear | 9 |
| excluded: null result | 7 |
| excluded: review or background statement | 2 |
| excluded: actor is the readout | 1 |

## Primary cases by readout

| Readout | Modality | Cases | Papers |
|---|---|---|---|
| pain | mechanical | 81 | 72 |
| pain | general | 27 | 26 |
| TNF-alpha | - | 26 | 25 |
| NLRP3 | - | 17 | 16 |
| BDNF | - | 10 | 9 |
| IL-1beta | - | 7 | 7 |
| pain | thermal | 6 | 6 |
| TRPV1 | - | 6 | 6 |
| microglial activation | - | 4 | 4 |
| IL-6 | - | 3 | 3 |
| KCC2 | - | 2 | 2 |

## Primary cases by perturbation

| Perturbation | Cases | Readout rose | Readout fell |
|---|---|---|---|
| drug | 112 | 10 | 102 |
| gain | 21 | 9 | 12 |
| loss | 56 | 11 | 45 |

## Implied signs

Raising the actor raises the readout in 64 cases and lowers it in 125 (66% share the commoner sign, the majority baseline).

## Do papers agree with each other?

Pairs of papers that studied the same actor and readout: 9; they agree on the sign in 9 (100%). This is a rough ceiling for any model scored on these cases.


## Flags on primary cases

- mixed models in paper: 72
- hedged: 10
- in naive or sham animals: 5

## Most-tested actors

- PDTC: 4
- MCC950 (NLRP3 Inhibitor): 4
- capsaicin: 4
- Brain-Derived Neurotrophic Factor (BDNF): 3
- DXL-A-24: 3
- Paeoniflorin: 3
- lncRNA FIRRE: 2
- Lncenc1: 2
- magnolol: 2
- miR-223: 2
- melatonin: 2
- glucosamine sulphate: 2
- oxytocin: 2
- JWH-133: 2
- SIRT3: 2
