# Signed-path inference over the knowledge graph

Signed graph: 5384 links (5131 crawled and unreviewed, 253 curated) over 3135 nodes; 151 pain nodes. Excluded: {'refuted': 8, 'null_result_wording': 58, 'review_wrong': 16}.

**Every inference below is a hypothesis built from signs composed along paths; most links are crawled and unreviewed.** The calibration section says how far to trust them.

## 0. Calibration: does composing signs along paths reproduce known links?

- two-hop paths predict a direct link's sign (curated): **85%** (28/33)
- two-hop paths predict a direct link's sign (crawled): **90%** (1321/1472)
- two-hop paths predict a direct link's sign (all): **90%** (1349/1505)
- ... with at least 1 supporting two-hop path(s): 90% (1349/1505)
- ... with at least 2 supporting two-hop path(s): 92% (493/538)
- ... with at least 3 supporting two-hop path(s): 93% (236/253)
- leave-one-out, 128 drugs with a known direct effect on pain (that link removed, the effect re-predicted from the other paths): known analgesics predicted analgesic 95% (117/123), known pain-raising drugs predicted pain-raising 80% (4/5). **But the method calls 87% of all drugs analgesic**, so recovering known analgesics is almost uninformative: the crawl is selection-biased, since a drug that appears in a pain paper is mostly being studied as an analgesic.
- discrimination: a known analgesic scores lower (more analgesic) than a drug with no direct pain link with probability **0.61** (AUC; 123 known analgesics vs 804 others; 0.5 is chance, and drugs with more links tend to score more extreme, which inflates it)
- the clearest check is the rare opposite call: 31 drugs are predicted pain-raising (section 1 lists them), and they should be known pain inducers

Outcome set for ranking: the 20 best-evidenced pain nodes (Activity-induced muscle pain, Cisplatin-induced mechanical and cold allodynia, Mechanical Allodynia, Neuropathic Pain, Oxaliplatin-induced mechanical allodynia, Vincristine-induced mechanical allodynia, acute pain, allodynia, bone cancer pain, cancer pain, central post-stroke pain, chronic pancreatitis pain, ...). Each outcome counts at most 1, so reaching a hub that fans out to many pain nodes does not inflate a score.

## 1. Predicted drug effects on pain (paths up to 4 links)

999 drugs reach the core pain nodes. **Novel analgesic candidates** (net score <= -1, >=2 independent mediators, >=80% of reached pain nodes agree, no direct drug -> pain link in the graph): 281. *Read this as a literature-weighted ranking, not a prediction: the AUC above is only 0.61, because most drugs in a pain crawl are analgesics.* Strongest:

| drug | score | pain nodes (-/+) | mediators | shortest strong path |
|---|---|---|---|---|
| Paeoniflorin | -14.93 | 19/0 | 8 | Paeoniflorin --(-)--> TRPV1 --+--> cancer pain |
| emodin | -14.71 | 18/0 | 9 | emodin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| ferulic acid | -14.09 | 19/0 | 5 | ferulic acid --(-)--> TLR4 --+--> tactile allodynia |
| AICAR | -13.81 | 17/0 | 6 | AICAR --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| resveratrol | -13.80 | 17/1 | 8 | resveratrol --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| ADM_12 | -13.74 | 18/0 | 4 | ADM_12 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Linarin | -13.70 | 19/0 | 5 | Linarin --(-)--> TLR4 --+--> tactile allodynia |
| JQ1 | -13.52 | 19/1 | 5 | JQ1 --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| naringin | -13.22 | 18/0 | 5 | naringin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| Euphorbium total triterpenes | -13.19 | 17/0 | 4 | Euphorbium total triterpenes --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| GTS-21 | -13.14 | 18/1 | 4 | GTS-21 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| semaglutide | -13.09 | 18/0 | 5 | semaglutide --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| CYM51010 | -13.06 | 18/0 | 4 | CYM51010 --(-)--> TRPV1 --+--> cancer pain |
| Panlongqi Tablet | -13.02 | 19/0 | 3 | Panlongqi Tablet --(-)--> TLR4 --+--> tactile allodynia |
| Gastrodin | -12.99 | 17/1 | 7 | Gastrodin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |

**Drugs predicted to worsen pain** (score >= 1, >=2 mediators, >=80% agreement): 31. Strongest:

| drug | score | direct link | shortest strong path |
|---|---|---|---|
| paclitaxel | +16.07 | [1] | paclitaxel --+--> Mechanical Allodynia |
| oxaliplatin | +15.80 | [1] | oxaliplatin --+--> Mechanical Allodynia |
| vincristine | +13.89 | none | vincristine --+--> TRPV1 --+--> cancer pain |
| morphine | +13.86 | none | morphine --+--> TLR4 --+--> tactile allodynia |
| nitroglycerin | +13.26 | none | nitroglycerin --+--> CGRP --+--> cold allodynia |
| nitrogen mustard | +12.89 | none | nitrogen mustard --+--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| capsaicin | +12.88 | [-1] | capsaicin --+--> CGRP --+--> cold allodynia |
| Piroxicam | +9.38 | none | Piroxicam --+--> CGRP --+--> cold allodynia |

**Double-edged drugs** (the direct link says one thing, the other paths the opposite; 6): a context-dependent effect, or an off-target liability.

| drug | direct link | score from other paths | shortest opposing path |
|---|---|---|---|
| capsaicin | analgesic | +12.9 | capsaicin --+--> CGRP --+--> cold allodynia |
| propofol | analgesic | +7.7 | propofol --+--> Bradykinin --+--> Cisplatin-induced mechanical and cold allodynia |
| ADU-S100 | analgesic | +6.2 | ADU-S100 --+--> IL-1beta --+--> Activity-induced muscle pain |
| CYN154806 | pain-raising | -4.7 | CYN154806 --(-)--> CGRP --+--> cold allodynia |
| Simvastatin | analgesic | +2.3 | Simvastatin --+--> TRPV1 --+--> cancer pain |
| DMTS | analgesic | +0.5 | DMTS --+--> TRPA1 Channel --+--> CGRP --+--> cold allodynia |

## 2. Targets: what drives pain, and what no drug yet hits

| target | drives pain (score) | core pain nodes driven | drugs inhibiting it |
|---|---|---|---|
| Tumor Necrosis Factor Alpha (molecule) | 13.60 | 20 | 187 |
| TLR4 (receptor) | 11.53 | 17 | 66 |
| IL-1beta (concept) | 10.65 | 17 | 39 |
| P2X4 Receptor (channel) | 10.29 | 17 | 7 |
| NLRP3 Inflammasome (concept) | 9.71 | 16 | 125 |
| CGRP (molecule) | 8.95 | 16 | 99 |
| HMGB1 (concept) | 8.54 | 16 | 16 |
| p38 MAPK (molecule) | 8.04 | 16 | 19 |
| Vascular Endothelial Growth Factor A (concept) | 7.94 | 18 | 42 |
| Spinal Microglia (cell_type) | 7.92 | 16 | 20 |
| TRPV4 (channel) | 7.82 | 17 | 1 |
| FTO (molecule) | 7.43 | 18 | 0 |
| Prostaglandin E2 (concept) | 7.42 | 16 | 54 |
| NGF (molecule) | 7.41 | 16 | 0 |
| TRPV1 (channel) | 7.21 | 17 | 113 |

**Druggable gaps** (drives >=2 core pain nodes, no inhibiting drug in the graph): 66. Top:

- FTO (molecule): score 7.43, drives 18 core pain nodes
- NGF (molecule): score 7.41, drives 16 core pain nodes
- miR-30b-5p (molecule): score 5.94, drives 17 core pain nodes
- galectin-3 (molecule): score 5.77, drives 16 core pain nodes
- RUNX1 (molecule): score 5.31, drives 16 core pain nodes
- spinal HDAC6 (molecule): score 5.15, drives 16 core pain nodes
- EZH2 (molecule): score 4.40, drives 15 core pain nodes
- NR2B (receptor): score 4.08, drives 15 core pain nodes
- DNMT1 (molecule): score 3.93, drives 15 core pain nodes
- B2 Receptor (receptor): score 3.87, drives 14 core pain nodes

**Inducers** (nothing in the graph acts on them, so they are inputs, not targets): Chronic Constriction Injury (12.0), LPS (11.0), Spared Nerve Injury (9.8), Chikungunya virus (8.3), IL-33 (6.9), multiple lesion inductions (6.9), Interstitial cystitis/bladder pain syndrome (6.1), disulfide HMGB1 (6.0), feline odontoclastic resorptive lesion (6.0), Heme (6.0)


**Pain-suppressing nodes** (raising them lowers pain): CB2 (-7.90), Nrf2 (-7.27), PPARγ (-5.99), IL-10 (-5.71), TSG-6 (-4.95), SIRT1 (-4.82), endoglin (-4.64), beta-hydroxybutyrate (-4.61), PPAR-gamma (-4.47), SIRT6 (-4.15)

## 3. Chokepoints between nerve-injury models and pain

22 injury nodes, 33104 pain-promoting paths (up to 5 links). Share of the weighted flow passing through each node:

- Tumor Necrosis Factor Alpha (molecule): 49%
- TRPV1 (channel): 37%
- CGRP (molecule): 36%
- NLRP3 Inflammasome (concept): 36%
- IL-1beta (concept): 20%
- TLR4 (receptor): 17%
- Brain-Derived Neurotrophic Factor (molecule): 10%
- Nav1.7 (channel): 8%
- Vascular Endothelial Growth Factor A (concept): 7%
- NGF (molecule): 7%
- Hypoxia-Inducible Factor 1 Alpha (concept): 6%
- Spinal Microglia (cell_type): 5%
- KCC2 (channel): 5%
- Prostaglandin E2 (concept): 5%
- Nrf2 (process): 4%

## 4. Feedback loops

47 two-node loops (A acts on B and B acts back; 40 mutually reinforcing) and 4938 loops of 3-5 links: **3449 self-amplifying** (even number of inhibitory links), 1489 self-limiting.

Strongest mutually reinforcing pairs: Reactive Oxygen Species <-> NLRP3 Inflammasome (0.53); Tumor Necrosis Factor Alpha <-> TLR4 (0.53); NLRP3 Inflammasome <-> IL-1beta (0.53); CGRP <-> TRPV1 (0.53); Tumor Necrosis Factor Alpha <-> NF-κB (0.49); Tumor Necrosis Factor Alpha <-> NLRP3 Inflammasome (0.48); P2X3 <-> CGRP (0.43); Tumor Necrosis Factor Alpha <-> Vascular Endothelial Growth Factor A (0.40)

Nodes in the most self-amplifying 3+ node loops (a cut here breaks the most vicious circles): Tumor Necrosis Factor Alpha (2360), CGRP (1556), NLRP3 Inflammasome (1431), TRPV1 (1002), IL-1beta (814), Neuropathic Pain (722), MMP-9 (495), Vascular Endothelial Growth Factor A (372), Nrf2 (326), TLR4 (313)

Strongest self-amplifying 3+ node loops:

- Spinal Microglia -> Brain-Derived Neurotrophic Factor -> Central Sensitization -> PPAR-gamma -> Spinal Microglia  (weight 0.67, 2 inhibitory)
- IL-6/JAK2/STAT3 Axis -> Brain-Derived Neurotrophic Factor -> Central Sensitization -> PPAR-gamma -> IL-6/JAK2/STAT3 Axis  (weight 0.67, 2 inhibitory)
- Tumor Necrosis Factor Alpha -> TRPV1 -> CGRP -> Tumor Necrosis Factor Alpha  (weight 0.48, 0 inhibitory)
- CGRP -> Vascular Endothelial Growth Factor A -> TRPV1 -> CGRP  (weight 0.48, 0 inhibitory)
- KCC2 -> Central Sensitization -> PPAR-gamma -> Spinal Microglia -> Brain-Derived Neurotrophic Factor -> KCC2  (weight 0.47, 4 inhibitory)
- KCC2 -> Central Sensitization -> PPAR-gamma -> IL-6/JAK2/STAT3 Axis -> Brain-Derived Neurotrophic Factor -> KCC2  (weight 0.47, 4 inhibitory)
- COX-2 -> Prostaglandin E2 -> TRPV1 -> COX-2  (weight 0.45, 0 inhibitory)
- NGF -> CGRP -> IL-1beta -> NGF  (weight 0.43, 0 inhibitory)

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
