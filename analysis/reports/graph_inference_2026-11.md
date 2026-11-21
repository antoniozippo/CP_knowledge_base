# Signed-path inference over the knowledge graph

Signed graph: 5382 links (5129 crawled and unreviewed, 253 curated) over 3134 nodes; 151 pain nodes. Excluded: {'refuted': 8, 'null_result_wording': 58, 'review_wrong': 16}.

**Every inference below is a hypothesis built from signs composed along paths; most links are crawled and unreviewed.** The calibration section says how far to trust them.

## 0. Calibration: does composing signs along paths reproduce known links?

- two-hop paths predict a direct link's sign (curated): **85%** (29/34)
- two-hop paths predict a direct link's sign (crawled): **90%** (1328/1479)
- two-hop paths predict a direct link's sign (all): **90%** (1357/1513)
- ... with at least 1 supporting two-hop path(s): 90% (1357/1513)
- ... with at least 2 supporting two-hop path(s): 92% (496/541)
- ... with at least 3 supporting two-hop path(s): 93% (239/257)
- leave-one-out, 128 drugs with a known direct effect on pain (that link removed, the effect re-predicted from the other paths): known analgesics predicted analgesic 95% (117/123), known pain-raising drugs predicted pain-raising 80% (4/5). **But the method calls 87% of all drugs analgesic**, so recovering known analgesics is almost uninformative: the crawl is selection-biased, since a drug that appears in a pain paper is mostly being studied as an analgesic.
- discrimination: a known analgesic scores lower (more analgesic) than a drug with no direct pain link with probability **0.61** (AUC; 123 known analgesics vs 804 others; 0.5 is chance, and drugs with more links tend to score more extreme, which inflates it)
- the clearest check is the rare opposite call: 29 drugs are predicted pain-raising (section 1 lists them), and they should be known pain inducers

Outcome set for ranking: the 20 best-evidenced pain nodes (Activity-induced muscle pain, Cisplatin-induced mechanical and cold allodynia, Mechanical Allodynia, Neuropathic Pain, Oxaliplatin-induced mechanical allodynia, Vincristine-induced mechanical allodynia, acute pain, allodynia, bone cancer pain, cancer pain, central post-stroke pain, chronic pancreatitis pain, ...). Each outcome counts at most 1, so reaching a hub that fans out to many pain nodes does not inflate a score.

## 1. Predicted drug effects on pain (paths up to 4 links)

999 drugs reach the core pain nodes. **Novel analgesic candidates** (net score <= -1, >=2 independent mediators, >=80% of reached pain nodes agree, no direct drug -> pain link in the graph): 281. *Read this as a literature-weighted ranking, not a prediction: the AUC above is only 0.61, because most drugs in a pain crawl are analgesics.* Strongest:

| drug | score | pain nodes (-/+) | mediators | shortest strong path |
|---|---|---|---|---|
| Paeoniflorin | -13.43 | 18/0 | 8 | Paeoniflorin --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| emodin | -13.27 | 18/1 | 9 | emodin --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| ferulic acid | -12.12 | 19/0 | 5 | ferulic acid --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| AICAR | -11.96 | 17/0 | 6 | AICAR --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| ADM_12 | -11.93 | 18/0 | 4 | ADM_12 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| JQ1 | -11.82 | 19/1 | 5 | JQ1 --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| Linarin | -11.81 | 19/0 | 5 | Linarin --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| naringin | -11.67 | 17/0 | 5 | naringin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| resveratrol | -11.56 | 17/0 | 8 | resveratrol --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| GTS-21 | -11.28 | 18/1 | 4 | GTS-21 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Euphorbium total triterpenes | -11.19 | 17/0 | 4 | Euphorbium total triterpenes --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| TAK242 | -11.15 | 18/1 | 4 | TAK242 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| MSC-EVs | -11.00 | 18/1 | 3 | MSC-EVs --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| CYM51010 | -10.97 | 18/0 | 4 | CYM51010 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Gastrodin | -10.96 | 17/1 | 7 | Gastrodin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |

**Drugs predicted to worsen pain** (score >= 1, >=2 mediators, >=80% agreement): 29. Strongest:

| drug | score | direct link | shortest strong path |
|---|---|---|---|
| paclitaxel | +15.30 | [1] | paclitaxel --+--> Mechanical Allodynia |
| oxaliplatin | +14.57 | [1] | oxaliplatin --+--> Mechanical Allodynia |
| morphine | +12.62 | none | morphine --+--> TLR4 --+--> tactile allodynia |
| vincristine | +11.97 | none | vincristine --+--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| nitroglycerin | +11.65 | none | nitroglycerin --+--> CGRP --+--> cold allodynia |
| capsaicin | +11.31 | [-1] | capsaicin --+--> CGRP --+--> cold allodynia |
| nitrogen mustard | +10.71 | none | nitrogen mustard --+--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| Piroxicam | +7.35 | none | Piroxicam --+--> CGRP --+--> cold allodynia |

**Double-edged drugs** (the direct link says one thing, the other paths the opposite; 5): a context-dependent effect, or an off-target liability.

| drug | direct link | score from other paths | shortest opposing path |
|---|---|---|---|
| capsaicin | analgesic | +11.3 | capsaicin --+--> CGRP --+--> cold allodynia |
| propofol | analgesic | +5.7 | propofol --+--> Bradykinin --+--> Cisplatin-induced mechanical and cold allodynia |
| ADU-S100 | analgesic | +4.4 | ADU-S100 --+--> IL-1beta --+--> Activity-induced muscle pain |
| CYN154806 | pain-raising | -3.3 | CYN154806 --(-)--> CGRP --+--> cold allodynia |
| Simvastatin | analgesic | +1.7 | Simvastatin --+--> TRPV1 --+--> cancer pain |

## 2. Targets: what drives pain, and what no drug yet hits

| target | drives pain (score) | core pain nodes driven | drugs inhibiting it |
|---|---|---|---|
| Tumor Necrosis Factor Alpha (molecule) | 12.00 | 19 | 187 |
| TLR4 (receptor) | 10.52 | 17 | 66 |
| IL-1beta (concept) | 9.10 | 16 | 39 |
| P2X4 Receptor (channel) | 8.92 | 17 | 7 |
| NLRP3 Inflammasome (concept) | 8.42 | 16 | 125 |
| CGRP (molecule) | 7.63 | 15 | 99 |
| HMGB1 (concept) | 7.10 | 16 | 16 |
| Vascular Endothelial Growth Factor A (concept) | 6.71 | 18 | 42 |
| Spinal Microglia (cell_type) | 6.70 | 15 | 20 |
| p38 MAPK (molecule) | 6.59 | 16 | 19 |
| NGF (molecule) | 6.49 | 16 | 0 |
| Prostaglandin E2 (concept) | 6.27 | 16 | 54 |
| TRPV4 (channel) | 6.25 | 17 | 1 |
| TRPV1 (channel) | 6.22 | 17 | 113 |
| FTO (molecule) | 6.12 | 17 | 0 |

**Druggable gaps** (drives >=2 core pain nodes, no inhibiting drug in the graph): 67. Top:

- NGF (molecule): score 6.49, drives 16 core pain nodes
- FTO (molecule): score 6.12, drives 17 core pain nodes
- miR-30b-5p (molecule): score 4.67, drives 17 core pain nodes
- galectin-3 (molecule): score 4.59, drives 15 core pain nodes
- RUNX1 (molecule): score 4.15, drives 16 core pain nodes
- spinal HDAC6 (molecule): score 4.07, drives 16 core pain nodes
- EZH2 (molecule): score 3.54, drives 15 core pain nodes
- DNMT1 (molecule): score 3.16, drives 15 core pain nodes
- NR2B (receptor): score 3.11, drives 15 core pain nodes
- B2 Receptor (receptor): score 2.98, drives 14 core pain nodes

**Inducers** (nothing in the graph acts on them, so they are inputs, not targets): Chronic Constriction Injury (10.5), LPS (9.7), Spared Nerve Injury (8.2), Chikungunya virus (6.8), IL-33 (5.5), multiple lesion inductions (5.5), disulfide HMGB1 (4.9), feline odontoclastic resorptive lesion (4.9), Heme (4.9), Interstitial cystitis/bladder pain syndrome (4.9)


**Pain-suppressing nodes** (raising them lowers pain): PPARγ (-6.92), CB2 (-6.59), Nrf2 (-5.81), IL-10 (-4.77), SIRT1 (-3.97), TSG-6 (-3.82), endoglin (-3.68), beta-hydroxybutyrate (-3.63), SIRT6 (-3.32), FOXA2 (-3.16)

## 3. Chokepoints between nerve-injury models and pain

22 injury nodes, 33365 pain-promoting paths (up to 5 links). Share of the weighted flow passing through each node:

- Tumor Necrosis Factor Alpha (molecule): 48%
- TRPV1 (channel): 36%
- CGRP (molecule): 35%
- NLRP3 Inflammasome (concept): 34%
- IL-1beta (concept): 20%
- TLR4 (receptor): 18%
- Brain-Derived Neurotrophic Factor (molecule): 11%
- Vascular Endothelial Growth Factor A (concept): 7%
- Nav1.7 (channel): 7%
- NGF (molecule): 7%
- Hypoxia-Inducible Factor 1 Alpha (concept): 6%
- KCC2 (channel): 6%
- Spinal Microglia (cell_type): 5%
- Prostaglandin E2 (concept): 5%
- Nrf2 (process): 4%

## 4. Feedback loops

47 two-node loops (A acts on B and B acts back; 40 mutually reinforcing) and 5042 loops of 3-5 links: **3539 self-amplifying** (even number of inhibitory links), 1503 self-limiting.

Strongest mutually reinforcing pairs: Tumor Necrosis Factor Alpha <-> TLR4 (0.47); NLRP3 Inflammasome <-> IL-1beta (0.47); CGRP <-> TRPV1 (0.47); Reactive Oxygen Species <-> NLRP3 Inflammasome (0.45); Tumor Necrosis Factor Alpha <-> NF-κB (0.42); Tumor Necrosis Factor Alpha <-> Vascular Endothelial Growth Factor A (0.40); Tumor Necrosis Factor Alpha <-> NLRP3 Inflammasome (0.39); P2X3 <-> CGRP (0.34)

Nodes in the most self-amplifying 3+ node loops (a cut here breaks the most vicious circles): Tumor Necrosis Factor Alpha (2406), CGRP (1586), NLRP3 Inflammasome (1457), TRPV1 (1004), IL-1beta (842), Neuropathic Pain (738), MMP-9 (497), Vascular Endothelial Growth Factor A (372), TLR4 (334), Nrf2 (329)

Strongest self-amplifying 3+ node loops:

- Spinal Microglia -> Brain-Derived Neurotrophic Factor -> Central Sensitization -> PPARγ -> Spinal Microglia  (weight 0.60, 2 inhibitory)
- IL-6/JAK2/STAT3 Axis -> Brain-Derived Neurotrophic Factor -> Central Sensitization -> PPARγ -> IL-6/JAK2/STAT3 Axis  (weight 0.60, 2 inhibitory)
- KCC2 -> Central Sensitization -> PPARγ -> Spinal Microglia -> Brain-Derived Neurotrophic Factor -> KCC2  (weight 0.47, 4 inhibitory)
- KCC2 -> Central Sensitization -> PPARγ -> IL-6/JAK2/STAT3 Axis -> Brain-Derived Neurotrophic Factor -> KCC2  (weight 0.47, 4 inhibitory)
- Tumor Necrosis Factor Alpha -> TRPV1 -> CGRP -> Tumor Necrosis Factor Alpha  (weight 0.41, 0 inhibitory)
- COX-2 -> Prostaglandin E2 -> TRPV1 -> COX-2  (weight 0.40, 0 inhibitory)
- CGRP -> Vascular Endothelial Growth Factor A -> TRPV1 -> CGRP  (weight 0.39, 0 inhibitory)
- NGF -> CGRP -> IL-1beta -> NGF  (weight 0.35, 0 inhibitory)

## 5. Graph hygiene: duplicate nodes split the evidence

12 crawled nodes name the same entity as a curated node under another spelling, so their links never reach the curated node. Largest:

- cannabidiol (20 links) = Cannabidiol
- Cannabidiol (CBD) vapor (2 links) = Cannabidiol
- JAK/STAT3 pathway (2 links) = JAK/STAT3 pathway
- MAPK pathway (2 links) = MAPK Pathway
- CGRP(8-37) (1 links) = CGRP
- chaperone-mediated autophagy (1 links) = LAMP2A
- NLRP3 inhibitor (1 links) = MCC950 / CRID3
- Pain chronification (1 links) = CXCL12/CXCR4 Positive-Feedback Loop
- cognitive deficits (0 links) = Hippocampus Kalirin-7
- Diabetic neuropathy (0 links) = O-GlcNAc Glycosylation of Cav3.2
