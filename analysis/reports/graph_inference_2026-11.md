# Signed-path inference over the knowledge graph

Signed graph: 5266 links (5013 crawled and unreviewed, 253 curated) over 3100 nodes; 151 pain nodes. Excluded: {'refuted': 8, 'null_result_wording': 54, 'review_wrong': 16}.

**Every inference below is a hypothesis built from signs composed along paths; most links are crawled and unreviewed.** The calibration section says how far to trust them.

## 0. Calibration: does composing signs along paths reproduce known links?

- two-hop paths predict a direct link's sign (curated): **84%** (27/32)
- two-hop paths predict a direct link's sign (crawled): **90%** (1267/1411)
- two-hop paths predict a direct link's sign (all): **90%** (1294/1443)
- ... with at least 1 supporting two-hop path(s): 90% (1294/1443)
- ... with at least 2 supporting two-hop path(s): 92% (471/514)
- ... with at least 3 supporting two-hop path(s): 93% (221/237)
- leave-one-out, 126 drugs with a known direct effect on pain (that link removed, the effect re-predicted from the other paths): known analgesics predicted analgesic 94% (114/121), known pain-raising drugs predicted pain-raising 80% (4/5). **But the method calls 87% of all drugs analgesic**, so recovering known analgesics is almost uninformative: the crawl is selection-biased, since a drug that appears in a pain paper is mostly being studied as an analgesic.
- discrimination: a known analgesic scores lower (more analgesic) than a drug with no direct pain link with probability **0.61** (AUC; 121 known analgesics vs 791 others; 0.5 is chance, and drugs with more links tend to score more extreme, which inflates it)
- the clearest check is the rare opposite call: 30 drugs are predicted pain-raising (section 1 lists them), and they should be known pain inducers

Outcome set for ranking: the 20 best-evidenced pain nodes (Activity-induced muscle pain, Calpain, Cisplatin-induced mechanical and cold allodynia, Congenital insensitivity to pain, Mechanical Allodynia, Neuropathic Pain, Oxaliplatin-induced mechanical allodynia, Vincristine-induced mechanical allodynia, acute pain, bone cancer pain, cancer pain, central post-stroke pain, ...). Each outcome counts at most 1, so reaching a hub that fans out to many pain nodes does not inflate a score.

## 1. Predicted drug effects on pain (paths up to 4 links)

986 drugs reach the core pain nodes. **Novel analgesic candidates** (net score <= -1, >=2 independent mediators, >=80% of reached pain nodes agree, no direct drug -> pain link in the graph): 269. *Read this as a literature-weighted ranking, not a prediction: the AUC above is only 0.61, because most drugs in a pain crawl are analgesics.* Strongest:

| drug | score | pain nodes (-/+) | mediators | shortest strong path |
|---|---|---|---|---|
| Paeoniflorin | -15.17 | 18/0 | 7 | Paeoniflorin --(-)--> TRPV1 --+--> cancer pain |
| emodin | -14.57 | 17/0 | 8 | emodin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| AICAR | -14.33 | 17/1 | 6 | AICAR --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| ferulic acid | -14.20 | 19/0 | 4 | ferulic acid --(-)--> TLR4 --+--> tactile allodynia |
| ADM_12 | -14.18 | 18/1 | 4 | ADM_12 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| Linarin | -14.10 | 18/0 | 5 | Linarin --(-)--> TLR4 --+--> tactile allodynia |
| JQ1 | -13.89 | 18/1 | 5 | JQ1 --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| Euphorbium total triterpenes | -13.74 | 17/1 | 4 | Euphorbium total triterpenes --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| GTS-21 | -13.63 | 18/1 | 4 | GTS-21 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| CYM51010 | -13.55 | 18/0 | 4 | CYM51010 --(-)--> TRPV1 --+--> cancer pain |
| naringin | -13.52 | 17/0 | 5 | naringin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| TAK242 | -13.45 | 18/1 | 4 | TAK242 --(-)--> Tumor Necrosis Factor Alpha --+--> Mechanical Allodynia |
| MSC-EVs | -13.43 | 18/1 | 3 | MSC-EVs --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| luteolin | -13.38 | 18/0 | 4 | luteolin --(-)--> CGRP --+--> cold allodynia |
| Gastrodin | -13.37 | 17/1 | 7 | Gastrodin --(-)--> NLRP3 Inflammasome --+--> Neuropathic Pain |

**Drugs predicted to worsen pain** (score >= 1, >=2 mediators, >=80% agreement): 30. Strongest:

| drug | score | direct link | shortest strong path |
|---|---|---|---|
| paclitaxel | +16.24 | [1] | paclitaxel --+--> Mechanical Allodynia |
| oxaliplatin | +15.56 | [1] | oxaliplatin --+--> Mechanical Allodynia |
| vincristine | +14.35 | none | vincristine --+--> TRPV1 --+--> cancer pain |
| morphine | +14.08 | none | morphine --+--> TLR4 --+--> tactile allodynia |
| nitroglycerin | +13.27 | none | nitroglycerin --+--> CGRP --+--> cold allodynia |
| capsaicin | +12.81 | [-1] | capsaicin --+--> CGRP --+--> cold allodynia |
| nitrogen mustard | +12.61 | none | nitrogen mustard --+--> NLRP3 Inflammasome --+--> Neuropathic Pain |
| bortezomib | +10.05 | none | bortezomib --+--> NLRP3 Inflammasome --+--> Neuropathic Pain |

**Double-edged drugs** (the direct link says one thing, the other paths the opposite; 5): a context-dependent effect, or an off-target liability.

| drug | direct link | score from other paths | shortest opposing path |
|---|---|---|---|
| capsaicin | analgesic | +12.8 | capsaicin --+--> CGRP --+--> cold allodynia |
| propofol | analgesic | +7.6 | propofol --+--> Bradykinin --+--> Cisplatin-induced mechanical and cold allodynia |
| ADU-S100 | analgesic | +6.6 | ADU-S100 --+--> IL-1beta --+--> Activity-induced muscle pain |
| CYN154806 | pain-raising | -5.2 | CYN154806 --(-)--> CGRP --+--> cold allodynia |
| Simvastatin | analgesic | +3.5 | Simvastatin --+--> TRPV1 --+--> cancer pain |

## 2. Targets: what drives pain, and what no drug yet hits

| target | drives pain (score) | core pain nodes driven | drugs inhibiting it |
|---|---|---|---|
| Tumor Necrosis Factor Alpha (molecule) | 13.60 | 19 | 183 |
| TLR4 (receptor) | 12.43 | 18 | 66 |
| IL-1beta (concept) | 11.54 | 18 | 38 |
| NLRP3 Inflammasome (concept) | 10.40 | 16 | 125 |
| P2X7R (channel) | 9.78 | 17 | 1 |
| CGRP (molecule) | 9.64 | 16 | 99 |
| HMGB1 (concept) | 9.17 | 17 | 16 |
| P2X4 Receptor (channel) | 9.02 | 17 | 5 |
| p38 MAPK (molecule) | 8.73 | 17 | 19 |
| Spinal Microglia (cell_type) | 8.73 | 17 | 20 |
| TRPV4 (channel) | 8.29 | 17 | 1 |
| TRPV1 (channel) | 7.79 | 17 | 113 |
| NF-κB (concept) | 7.52 | 17 | 38 |
| NGF (molecule) | 7.36 | 16 | 0 |
| Bradykinin (concept) | 7.32 | 15 | 6 |

**Druggable gaps** (drives >=2 core pain nodes, no inhibiting drug in the graph): 67. Top:

- NGF (molecule): score 7.36, drives 16 core pain nodes
- P2X4R (channel): score 6.92, drives 16 core pain nodes
- FTO (molecule): score 6.30, drives 17 core pain nodes
- galectin-3 (molecule): score 6.18, drives 17 core pain nodes
- miR-30b-5p (molecule): score 5.93, drives 17 core pain nodes
- RUNX1 (molecule): score 5.65, drives 16 core pain nodes
- spinal HDAC6 (molecule): score 5.43, drives 17 core pain nodes
- EZH2 (molecule): score 4.80, drives 16 core pain nodes
- HIF-1alpha (molecule): score 4.60, drives 15 core pain nodes
- NR2B (receptor): score 4.42, drives 16 core pain nodes

**Inducers** (nothing in the graph acts on them, so they are inputs, not targets): Chronic Constriction Injury (12.6), LPS (11.6), Spared Nerve Injury (9.3), Chikungunya virus (8.8), IL-33 (7.4), multiple lesion inductions (7.4), disulfide HMGB1 (6.5), feline odontoclastic resorptive lesion (6.5), Heme (6.5), miR-155 (6.4)


**Pain-suppressing nodes** (raising them lowers pain): CB2 (-8.43), Nrf2 (-7.84), PPARγ (-5.93), IL-10 (-5.70), PPAR-gamma (-5.38), TSG-6 (-5.27), endoglin (-5.06), beta-hydroxybutyrate (-4.95), SIRT6 (-4.28), FOXA2 (-4.23)

## 3. Chokepoints between nerve-injury models and pain

22 injury nodes, 30967 pain-promoting paths (up to 5 links). Share of the weighted flow passing through each node:

- Tumor Necrosis Factor Alpha (molecule): 49%
- TRPV1 (channel): 39%
- NLRP3 Inflammasome (concept): 36%
- CGRP (molecule): 36%
- IL-1beta (concept): 21%
- TLR4 (receptor): 18%
- Brain-Derived Neurotrophic Factor (molecule): 12%
- Nav1.7 (channel): 8%
- NGF (molecule): 6%
- Vascular Endothelial Growth Factor A (concept): 5%
- KCC2 (channel): 5%
- Nrf2 (process): 5%
- Prostaglandin E2 (concept): 5%
- Spinal Microglia (cell_type): 4%
- NF-κB (concept): 4%

## 4. Feedback loops

44 two-node loops (A acts on B and B acts back; 37 mutually reinforcing) and 4015 loops of 3-5 links: **2792 self-amplifying** (even number of inhibitory links), 1223 self-limiting.

Strongest mutually reinforcing pairs: Reactive Oxygen Species <-> NLRP3 Inflammasome (0.53); Tumor Necrosis Factor Alpha <-> TLR4 (0.53); NLRP3 Inflammasome <-> IL-1beta (0.53); CGRP <-> TRPV1 (0.53); Tumor Necrosis Factor Alpha <-> NF-κB (0.49); Tumor Necrosis Factor Alpha <-> NLRP3 Inflammasome (0.48); P2X3 <-> CGRP (0.43); P2X4R <-> Brain-Derived Neurotrophic Factor (0.43)

Nodes in the most self-amplifying 3+ node loops (a cut here breaks the most vicious circles): Tumor Necrosis Factor Alpha (1956), CGRP (1277), NLRP3 Inflammasome (1247), TRPV1 (883), Neuropathic Pain (637), IL-1beta (491), TLR4 (305), Nrf2 (298), MMP-9 (284), Brain-Derived Neurotrophic Factor (273)

Strongest self-amplifying 3+ node loops:

- Spinal Microglia -> Brain-Derived Neurotrophic Factor -> Central Sensitization -> PPAR-gamma -> Spinal Microglia  (weight 0.67, 2 inhibitory)
- IL-6/JAK2/STAT3 Axis -> Brain-Derived Neurotrophic Factor -> Central Sensitization -> PPAR-gamma -> IL-6/JAK2/STAT3 Axis  (weight 0.67, 2 inhibitory)
- Tumor Necrosis Factor Alpha -> TRPV1 -> CGRP -> Tumor Necrosis Factor Alpha  (weight 0.48, 0 inhibitory)
- KCC2 -> Central Sensitization -> PPAR-gamma -> Spinal Microglia -> Brain-Derived Neurotrophic Factor -> KCC2  (weight 0.47, 4 inhibitory)
- KCC2 -> Central Sensitization -> PPAR-gamma -> IL-6/JAK2/STAT3 Axis -> Brain-Derived Neurotrophic Factor -> KCC2  (weight 0.47, 4 inhibitory)
- COX-2 -> Prostaglandin E2 -> TRPV1 -> COX-2  (weight 0.45, 0 inhibitory)
- NGF -> CGRP -> IL-1beta -> NGF  (weight 0.43, 0 inhibitory)
- NLRP3 Inflammasome -> IL-1beta -> NF-κB -> NLRP3 Inflammasome  (weight 0.42, 0 inhibitory)

## 5. Graph hygiene: duplicate nodes split the evidence

34 crawled nodes name the same entity as a curated node under another spelling, so their links never reach the curated node. Largest:

- cannabidiol (20 links) = Cannabidiol
- P2X7R (9 links) = P2X7 Receptor
- VEGF-A (9 links) = Vascular Endothelial Growth Factor A
- P2X4R (6 links) = P2X4 Receptor
- CSF-1 (5 links) = CSF1
- HIF-1α (5 links) = Hypoxia-Inducible Factor 1 Alpha
- HIF-1alpha (4 links) = Hypoxia-Inducible Factor 1 Alpha
- IGF-1 (3 links) = Insulin-like Growth Factor 1
- TIMP1 (3 links) = TIMP-1
- A-438079 (2 links) = A438079
