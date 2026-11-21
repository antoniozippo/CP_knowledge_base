# Signed-path inference over the knowledge graph

Signed graph: 5397 links (5144 crawled and unreviewed, 253 curated) over 3140 nodes; 151 pain nodes. Excluded: {'refuted': 8, 'null_result_wording': 58}.

**Every inference below is a hypothesis built from signs composed along paths; most links are crawled and unreviewed.** The calibration section says how far to trust them.

## 0. Calibration: does composing signs along paths reproduce known links?

- two-hop paths predict a direct link's sign (curated): **88%** (30/34)
- two-hop paths predict a direct link's sign (crawled): **90%** (1352/1501)
- two-hop paths predict a direct link's sign (all): **90%** (1382/1535)
- ... with at least 1 supporting two-hop path(s): 90% (1382/1535)
- ... with at least 2 supporting two-hop path(s): 92% (519/562)
- ... with at least 3 supporting two-hop path(s): 93% (248/266)
- leave-one-out, 128 drugs with a known direct effect on pain (that link removed, the effect re-predicted from the other paths): known analgesics predicted analgesic 95% (117/123), known pain-raising drugs predicted pain-raising 80% (4/5). **But the method calls 87% of all drugs analgesic**, so recovering known analgesics is almost uninformative: the crawl is selection-biased, since a drug that appears in a pain paper is mostly being studied as an analgesic.
- discrimination: a known analgesic scores lower (more analgesic) than a drug with no direct pain link with probability **0.61** (AUC; 123 known analgesics vs 806 others; 0.5 is chance, and drugs with more links tend to score more extreme, which inflates it)
- the clearest check is the rare opposite call: 30 drugs are predicted pain-raising (section 1 lists them), and they should be known pain inducers

Outcome set for ranking: the 20 best-evidenced pain nodes (Activity-induced muscle pain, Cisplatin-induced mechanical and cold allodynia, Mechanical Allodynia, Neuropathic Pain, Oxaliplatin-induced mechanical allodynia, Vincristine-induced mechanical allodynia, acute pain, allodynia, bone cancer pain, cancer pain, central post-stroke pain, chronic pancreatitis pain, ...). Each outcome counts at most 1, so reaching a hub that fans out to many pain nodes does not inflate a score.

## 1. Predicted drug effects on pain (paths up to 4 links)

1001 drugs reach the core pain nodes. **Novel analgesic candidates** (net score <= -1, >=2 independent mediators, >=80% of reached pain nodes agree, no direct drug -> pain link in the graph): 282. *Read this as a literature-weighted ranking, not a prediction: the AUC above is only 0.61, because most drugs in a pain crawl are analgesics.* Strongest:

| drug | score | pain nodes (-/+) | mediators | shortest strong path |
|---|---|---|---|---|
| emodin | -13.31 | 18/1 | 9 | emodin --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Paeoniflorin | -13.28 | 18/1 | 9 | Paeoniflorin --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| ferulic acid | -12.04 | 19/0 | 5 | ferulic acid --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| AICAR | -11.78 | 17/0 | 6 | AICAR --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| ADM_12 | -11.73 | 18/1 | 4 | ADM_12 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Linarin | -11.65 | 18/0 | 5 | Linarin --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| JQ1 | -11.64 | 19/1 | 5 | JQ1 --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| naringin | -11.59 | 17/1 | 5 | naringin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| GTS-21 | -11.23 | 18/1 | 4 | GTS-21 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| TAK242 | -11.16 | 18/1 | 4 | TAK242 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| resveratrol | -11.13 | 17/0 | 8 | resveratrol --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| Euphorbium total triterpenes | -11.09 | 17/1 | 4 | Euphorbium total triterpenes --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| CYM51010 | -11.08 | 18/0 | 4 | CYM51010 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Gastrodin | -10.87 | 17/1 | 7 | Gastrodin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| Brilliant Blue G | -10.84 | 17/1 | 5 | Brilliant Blue G --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |

**Drugs predicted to worsen pain** (score >= 1, >=2 mediators, >=80% agreement): 30. Strongest:

| drug | score | direct link | shortest strong path |
|---|---|---|---|
| paclitaxel | +15.08 | [1] | paclitaxel --+--> Mechanical Allodynia |
| oxaliplatin | +14.37 | [1] | oxaliplatin --+--> Mechanical Allodynia |
| morphine | +12.61 | none | morphine --+--> TLR4 --+--> tactile allodynia |
| vincristine | +11.98 | none | vincristine --+--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| nitroglycerin | +11.83 | none | nitroglycerin --+--> CGRP --+--> cold allodynia |
| capsaicin | +11.10 | [-1] | capsaicin --+--> CGRP --+--> cold allodynia |
| nitrogen mustard | +10.54 | none | nitrogen mustard --+--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| BzATP | +7.60 | none | BzATP --+--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |

**Double-edged drugs** (the direct link says one thing, the other paths the opposite; 5): a context-dependent effect, or an off-target liability.

| drug | direct link | score from other paths | shortest opposing path |
|---|---|---|---|
| capsaicin | analgesic | +11.1 | capsaicin --+--> CGRP --+--> cold allodynia |
| propofol | analgesic | +5.7 | propofol --+--> Bradykinin --+--> Cisplatin-induced mechanical and cold allodynia |
| ADU-S100 | analgesic | +4.4 | ADU-S100 --+--> IL-1beta --+--> Activity-induced muscle pain |
| CYN154806 | pain-raising | -3.3 | CYN154806 --(-)--> CGRP --+--> cold allodynia |
| Simvastatin | analgesic | +2.5 | Simvastatin --+--> TRPV1 --+--> cancer pain |

## 2. Targets: what drives pain, and what no drug yet hits

| target | drives pain (score) | core pain nodes driven | drugs inhibiting it |
|---|---|---|---|
| Tumor Necrosis Factor Alpha (molecule) | 11.86 | 19 | 187 |
| TLR4 (receptor) | 10.49 | 17 | 66 |
| IL-1beta (concept) | 9.21 | 16 | 39 |
| P2X4 Receptor (channel) | 9.14 | 17 | 7 |
| NLRP3 Inflammasome (concept) | 8.15 | 16 | 125 |
| TRPV1 (channel) | 7.45 | 18 | 113 |
| CGRP (molecule) | 7.39 | 15 | 99 |
| HMGB1 (concept) | 7.08 | 16 | 16 |
| Spinal Microglia (cell_type) | 6.96 | 16 | 20 |
| p38 MAPK (molecule) | 6.74 | 16 | 19 |
| Vascular Endothelial Growth Factor A (concept) | 6.72 | 18 | 42 |
| P2X7 Receptor (channel) | 6.53 | 16 | 9 |
| NGF (molecule) | 6.28 | 15 | 0 |
| Prostaglandin E2 (concept) | 6.23 | 15 | 54 |
| TRPV4 (channel) | 6.17 | 17 | 1 |

**Druggable gaps** (drives >=2 core pain nodes, no inhibiting drug in the graph): 67. Top:

- NGF (molecule): score 6.28, drives 15 core pain nodes
- FTO (molecule): score 6.13, drives 17 core pain nodes
- miR-30b-5p (molecule): score 4.72, drives 17 core pain nodes
- galectin-3 (molecule): score 4.63, drives 15 core pain nodes
- spinal HDAC6 (molecule): score 4.12, drives 16 core pain nodes
- RUNX1 (molecule): score 4.05, drives 15 core pain nodes
- EZH2 (molecule): score 3.59, drives 15 core pain nodes
- NR2B (receptor): score 3.23, drives 15 core pain nodes
- DNMT1 (molecule): score 3.23, drives 15 core pain nodes
- B2 Receptor (receptor): score 3.09, drives 14 core pain nodes

**Inducers** (nothing in the graph acts on them, so they are inputs, not targets): Chronic Constriction Injury (10.4), LPS (9.7), Spared Nerve Injury (8.3), Chikungunya virus (6.8), IL-33 (5.4), multiple lesion inductions (5.4), microglial Orai1 (5.0), disulfide HMGB1 (4.9), feline odontoclastic resorptive lesion (4.9), Heme (4.9)


**Pain-suppressing nodes** (raising them lowers pain): PPARγ (-6.92), CB2 (-6.59), Nrf2 (-5.82), IL-10 (-4.68), TSG-6 (-3.76), endoglin (-3.72), SIRT1 (-3.71), beta-hydroxybutyrate (-3.68), SIRT6 (-3.32), FOXA2 (-3.23)

## 3. Chokepoints between nerve-injury models and pain

22 injury nodes, 35536 pain-promoting paths (up to 5 links). Share of the weighted flow passing through each node:

- Tumor Necrosis Factor Alpha (molecule): 51%
- TRPV1 (channel): 39%
- CGRP (molecule): 34%
- NLRP3 Inflammasome (concept): 34%
- IL-1beta (concept): 19%
- TLR4 (receptor): 18%
- Brain-Derived Neurotrophic Factor (molecule): 10%
- Nav1.7 (channel): 7%
- Vascular Endothelial Growth Factor A (concept): 7%
- NGF (molecule): 7%
- Hypoxia-Inducible Factor 1 Alpha (concept): 6%
- KCC2 (channel): 6%
- Spinal Microglia (cell_type): 5%
- Prostaglandin E2 (concept): 4%
- Nrf2 (process): 4%

## 4. Feedback loops

48 two-node loops (A acts on B and B acts back; 41 mutually reinforcing) and 5420 loops of 3-5 links: **3821 self-amplifying** (even number of inhibitory links), 1599 self-limiting.

Strongest mutually reinforcing pairs: Tumor Necrosis Factor Alpha <-> TLR4 (0.47); NLRP3 Inflammasome <-> IL-1beta (0.47); CGRP <-> TRPV1 (0.47); Reactive Oxygen Species <-> NLRP3 Inflammasome (0.45); Tumor Necrosis Factor Alpha <-> TRPV1 (0.45); Tumor Necrosis Factor Alpha <-> NF-κB (0.42); Tumor Necrosis Factor Alpha <-> Vascular Endothelial Growth Factor A (0.40); Tumor Necrosis Factor Alpha <-> NLRP3 Inflammasome (0.39)

Nodes in the most self-amplifying 3+ node loops (a cut here breaks the most vicious circles): Tumor Necrosis Factor Alpha (2684), CGRP (1697), NLRP3 Inflammasome (1558), TRPV1 (1275), IL-1beta (862), Neuropathic Pain (756), MMP-9 (510), Vascular Endothelial Growth Factor A (411), TLR4 (363), Nrf2 (350)

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
- Diabetic neuropathy (2 links) = O-GlcNAc Glycosylation of Cav3.2
- JAK/STAT3 pathway (2 links) = JAK/STAT3 pathway
- MAPK pathway (2 links) = MAPK Pathway
- MPTP (2 links) = Mitochondrial Permeability Transition Pore
- CGRP(8-37) (1 links) = CGRP
- chaperone-mediated autophagy (1 links) = LAMP2A
- cognitive deficits (1 links) = Hippocampus Kalirin-7
- neurite outgrowth (1 links) = DRG Kalirin-7
