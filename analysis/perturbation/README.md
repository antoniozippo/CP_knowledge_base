# Perturbation validation set (scope phase 2)

Test cases for the functional model: experiments in which an actor was perturbed and a readout
moved, in the first model's context, **rodent peripheral nerve injury** (CCI, SNI, SNL, PSNL,
sciatic injury). A model passes a case when it predicts the direction the readout moved.

Built by `analysis/scripts/build_perturbation_cases.py` from `crawler/extractions/`, with rules in
`config.yaml`. Rebuild with:

    python3 analysis/scripts/build_perturbation_cases.py

## Files

| File | Contents |
|---|---|
| `cases.csv` | Every candidate case with its status (`primary`, or why it was excluded) |
| `summary.md` | Counts, exclusions, agreement between papers, most-tested actors |
| `adjudication_sample.csv` | 150 primary cases, stratified, with empty columns for a domain expert |
| `config.yaml` | Context patterns, perturbation wording, readouts and markers, split, sample size |

## What a case says

| Column | Meaning |
|---|---|
| `actor`, `actor_node` | What was perturbed, grounded to a graph node. For an agent named as subject ("TLR4 siRNA", "P2X7R antagonist") the actor is its target. |
| `perturbation` | `loss` (knockout, knockdown, siRNA, inhibitor or antagonist of the actor), `gain` (overexpression, agonist, recombinant protein), or `drug` (a compound given; the model needs its targets) |
| `readout`, `readout_node` | `pain` (any pain-behaviour node, with `modality`: mechanical, thermal, cold or general) or one of the markers: TNF-α, IL-1β, IL-6, NLRP3, BDNF, TRPV1, KCC2, microglial activation |
| `implied_sign` | What the model must reproduce: raising the actor's activity raises (+1) or lowers (-1) the readout |
| `observed_change` | How the readout moved in the experiment (+1 rose, -1 fell) |
| `inverted` | 1 when the paper measured a withdrawal threshold or latency, or antinociception: a rise there means less pain, and the signs are already flipped |
| `split` | `build` or `test`: the most recent quarter of papers by PubMed entry order are held out |
| `flags` | `mixed models in paper` (the paper also uses another model and the quote does not say which), `hedged`, `in naive or sham animals` |

## Rules

1. A relationship is a candidate when its quote describes a perturbation and its object grounds to a
   readout. Drug–target descriptions ("capsazepine, a TRPV1 antagonist") are dropped as the drug's
   own target: they are model inputs, not tests of the network.
2. Context comes from the paper's abstract and methods (a nerve-injury model and a rodent) and from
   the quote and readout label. A quote or readout naming another model (CFA, chemotherapy,
   diabetes, incision, spinal cord injury, cardiac disease…), another organism, or cells in a dish
   is out of context.
3. Null results are dropped. Review papers and statements citing other work are dropped.
4. Repeats of the same actor, perturbation and readout within a paper become one case.
5. The test split is by PubMed entry order, not at random, so that the test papers are later
   than the build papers. When the model is built (phase 3), **every link and evidence item from a
   test paper must be left out**, not only the case's own quote.

## What the set is, honestly

- **190 primary cases from 146 papers, 150 actors** (45 in the test split). The full numbers are in
  `summary.md`.
- **Drug cases dominate**: 113 of 190, and the readout fell in 103 of them ("drug X reduced
  allodynia"). Two thirds of cases share one implied sign, so a model that always predicts it
  scores 66%. The 77 knockdown and overexpression cases are more balanced and more informative.
- **Most actors are tested once.** Only 9 pairs of papers studied the same actor and readout, so
  how often papers disagree, and therefore the ceiling any model can reach, cannot be estimated.
- **Most cases are out of reach of the current graph.** Only 68 of 190 have a signed path of up to
  four links from actor to readout without the case's own paper (18 of 77 knockdown or
  overexpression cases, 50 of 113 drug cases). Many actors enter the graph only through the paper
  that tests them. The canonical network (phase 1) has to cover these actors, and the drugs'
  targets, for the cases to be usable.
- **Recall is limited.** 269 candidates were excluded because the paper's abstract and methods
  name no model, which is common for abstract-only papers (half the corpus). Some of them are
  nerve-injury experiments.
- **The cases are machine-derived.** The extraction and the parsing rules were checked only by
  spot checks of 52 cases while the rules were written; errors found there were fixed. Before
  accuracy figures are reported, a domain expert should adjudicate `adjudication_sample.csv`
  (columns `is_perturbation_experiment`, `actor_correct`, `readout_correct`, `direction_correct`,
  `context_correct`). Their error rate is the error bar on every model score.
