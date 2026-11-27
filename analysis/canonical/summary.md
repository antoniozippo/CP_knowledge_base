# Canonical network: summary

Built by `analysis/scripts/build_canonical.py`; rules in `analysis/canonical/config.yaml`, explicit node assignments in `node_map.yaml`. See `README.md`.

- nodes: 172 ([('literature node', 61), ('gene', 55), ('drug', 47), ('readout', 9)])
- links: 686 ([('T3', 363), ('T1', 169), ('T2', 64), ('P', 41), ('T1,T3', 28), ('D', 8)])
- test-era cut: papers with PMID >= 40209863 are left out
- links left out: {'refuted': 8, 'only test-era papers': 1303, 'review wrong or null result': 58}

## Coverage of the validation set

A case is covered when a signed path of at most 3 links joins its actor to its readout without the case's own paper.

| Evidence used | Build cases covered | Test cases covered | Nodes on those paths |
|---|---|---|---|
| T1 | 37 of 144 (26%) | 10 of 45 (22%) | 50 |
| T1+T2 | 42 of 144 (29%) | 14 of 45 (31%) | 84 |
| T1+T2+T3 | 65 of 144 (45%) | 21 of 45 (47%) | 157 |
| T1+T2+T3+P | 68 of 144 (47%) | 21 of 45 (47%) | 172 |

## Cases still not covered (all tiers)

- actor has no outgoing link besides its own paper: 63
- no path within 3 links: 19
- actor has no link besides its own paper: 18

Drug cases not covered: 50 (42 drugs). Most need their targets: a compound named only in the paper that tests it has no other link. Examples: DXL-A-24, glucosamine sulphate, PAP-1, NRP1-4, LXM-15, BoNT/E, Compound 22, deltorphin II, PDTC, N-demethylsinomenine, sinomenine, Qufeng Zhitong capsule.

## Covered cases by kind

- knockdown or overexpression: 27 of 77
- drug: 62 of 112

## Largest hubs in the canonical network

- PAIN: 124 links
- TNF: 85 links
- TRPV1: 56 links
- shared_cgrp: 43 links
- NLRP3: 41 links
- BDNF: 33 links
- MICROGLIA: 32 links
- IL1B: 27 links
- TLR4: 26 links
- CRAWLED_electroacupuncture: 25 links
- VEGFA: 21 links
- SCN9A: 21 links
