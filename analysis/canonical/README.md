# Canonical network (scope phase 1)

The part of the knowledge graph an executable model will run on, for one context: **rodent
peripheral nerve injury**. Built by `analysis/scripts/build_canonical.py`:

    python3 analysis/scripts/build_canonical.py

## Files

| File | Contents |
|---|---|
| `network.json` | Nodes (canonical id, label, kind, the graph nodes merged into it), links (sign, evidence tiers, papers, papers in context), and each node's combination rule |
| `summary.md` | Size, coverage of the validation set by evidence tier, uncovered cases and why, largest hubs |
| `scorable_cases.csv` | The validation cases the network covers, which phase 3 scores, with the least evidence that covers each |
| `config.yaml` | Readouts, tiers, prior settings, path length, default rule |
| `node_map.yaml` | Explicit node assignments, nodes never to merge, name synonyms |
| `drug_targets.yaml` | Hand-entered primary targets of tested drugs (check against ChEMBL; see the file) |
| `rules.yaml` | Per-node overrides of the default combination rule (none yet) |
| `prior/omnipath_signed.tsv.gz` | OmniPath snapshot (2026-11-27): 71,116 directed interactions with a consensus sign |

## How it is built

1. **Nodes are consolidated.**
   - A graph node whose short name names one gene becomes its HGNC symbol, so the three TNF-α
     nodes collapse into one.
   - Names are resolved through OmniPath's symbols, `crawler/aliases.yaml` and `node_map.yaml`
     synonyms. A location word ("spinal", "microglial") is dropped first.
   - Variants, isoforms, modified forms (disulfide HMGB1), agents (TrkB-Fc, antisense
     oligonucleotides, aptamers), cell populations and processes stay separate nodes. Context nodes
     (`crawler/context_nodes.yaml`) and the regional Kalirin-7 pools are never merged.
   - Pain-behaviour nodes become `PAIN`. A withdrawal threshold, latency, antinociception or
     analgesia node joins it with the signs of its links flipped.
   - Microglia nodes become `MICROGLIA`. Drugs keep their own nodes.
2. **Links are filtered.**
   - Every paper of the test era (PMID at or after the validation set's test cut) is removed, so
     the network never contains the test papers. A crawled link left without papers is dropped.
   - Refuted links, null results and links the review marked wrong stay out.
   - Each link records its tiers: **T1** crawled with a paper in context, **T2** dossier, **T3**
     crawled without a paper in context, **P** OmniPath, **D** hand-entered drug target, **L**
     target named in the drug's label ("P2X7R antagonist").
3. **Prior knowledge** (OmniPath, curation effort of at least 2) joins genes already in the
   literature graph. It does not import new nodes unless `allow_prior_only_nodes` is set.
4. **Nodes kept** are those on a signed path of at most 3 links from a validation actor to its
   readout. The case's own paper is left out when this is computed. The one exception is a drug's
   link to the target its quote names ("the TRPV1 antagonist capsazepine"), which defines the
   perturbation rather than its outcome.
5. **Combination rule.** Activators combine by OR, inhibitors by AND NOT (Netflux-style
   normalized-Hill logic). There are no per-node overrides yet.

## What it is, honestly

- **172 nodes, 686 links.** About half the links are T3: crawled evidence from papers that did not
  study nerve injury. Only 202 links have a paper in context (T1).
- **Coverage is 47%** of build and test cases alike (68 of 144, 21 of 45). The uncovered cases
  name actors that appear only in the paper that tests them: non-coding RNAs, rat-specific genes,
  and research compounds or herbal mixtures without a known target. OmniPath barely helps (3
  build cases), because these actors are not in protein-signalling databases.
- **ChEMBL could not be reached** while this was built, so `drug_targets.yaml` was entered by hand
  from textbook pharmacology, for 21 drugs with an established primary target. It must be checked
  against ChEMBL.
- **The mapping rules were checked by reading every merged node**, which led to several fixes
  (agents and variants merged into their gene, mind-map topics merged into PAIN). They have not been
  reviewed by a domain expert. `network.json` lists every merge, so a reviewer can check them.
- **The combination rule is a default**, not knowledge. No node has a curated rule yet, and the
  rule matters only when a node has several inputs, which hubs such as PAIN (148 merged nodes), TNF
  and TRPV1 do.
- **The 89 scorable cases are few for a test**: 21 test cases give a 95% interval of about ±20
  points on an accuracy. Phase 3 should report leave-one-paper-out results on the build cases too.
