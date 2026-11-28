# Second rater (local Qwen) against the extraction: results

Rater: `qwen/qwen3.8-27b` on LM Studio, all 120 rows of `adjudication_sample.csv`, no errors, thinking
off, blind to the extracted directions and classes (`analysis/scripts/second_rater.py`, answers in
`adjudication_second_rater.csv`). Both raters are AI models; neither is an expert. The human sheet is
still blank.

## Agreement on the interaction class

| | Rows | Exact agreement | Cohen's kappa | Coarse (less than additive / additive / synergy / unclear) |
|---|---|---|---|---|
| All | 120 | 68% | 0.59 | 75% (kappa 0.53) |
| Paper states the interaction | 83 | 81% | 0.71 | 89% |
| Extraction inferred it | 37 | 38% | 0.21 | 43% |
| Cases the model was scored on | 45 | 78% | | 82% |

Confusion (rows extraction, columns Qwen):

| | synergy | additive | sub_additive | no_added_effect | occlusion | antagonism | unclear |
|---|---|---|---|---|---|---|---|
| synergy | 11 | 0 | 0 | 0 | 0 | 1 | 3 |
| additive | 2 | 3 | 1 | 0 | 0 | 0 | 0 |
| sub_additive | 5 | 1 | 0 | 0 | 0 | 0 | 6 |
| no_added_effect | 0 | 0 | 0 | 12 | 0 | 0 | 3 |
| occlusion | 0 | 0 | 0 | 0 | 42 | 1 | 2 |
| antagonism | 0 | 0 | 2 | 1 | 5 | 5 | 2 |
| unclear | 4 | 0 | 0 | 0 | 0 | 0 | 8 |

## What it says

- **Occlusion and no added effect are reproducible** (42/45 and 12/15). These are most of the "less than
  additive" labels, and they are usually stated in the paper ("abolished in knockouts").
- **The synergy / sub-additive / additive boundary is not.** No sub-additive label survives (0/12); Qwen
  calls 5 of them synergy and 6 unclear. Reading its reasons, it often calls "better than either alone"
  synergy, which by the definition is sub-additive unless the effect exceeds the sum. The extraction may
  also be wrong there; only a human can settle it. Antagonism is shaky too (5/15; 5 become occlusion).
- **Inferred labels are unreliable** (kappa 0.21). Labels stated by the paper are good (kappa 0.71).
- **The 84% majority baseline mostly holds.** Of 87 extracted "less than additive" labels, Qwen keeps 68
  (78%), turns 13 into unclear, 5 into synergy and 1 into additive.
- **The phase-4 verdict does not change.** On the 32 scored cases where both raters agree on the coarse
  class, Netflux is right on 1 and the structural rule on 4; the majority class holds 25.
- **Qwen is uninformative on the yes/no checks.** It says every row was run in the paper (120/120) and
  every readout is right. A rater that never says no cannot catch background mentions, so the "paper ran
  it" rate still needs the human. It flags 13 rows as out of context, mostly cultured neurons, which the
  in-context filter of the evaluation also drops.
- **Combination direction agrees on 74/120 (62%).** Most disagreements are the extraction's 0 against
  Qwen's +/-1 (31 rows): the extraction often wrote 0 for "occlusion" (no change against control) where
  Qwen recorded the change.

## Consequences

1. Use stated labels only, or collapse to occlusion / no added effect versus the rest, for any further
   modelling; drop inferred labels and the sub-additive class until a human has checked them.
2. The human check is still needed, now focused: the 37 inferred rows, the synergy / sub-additive rows,
   and the "paper ran it" question, where the AI rater gives no information.

## Second run on the focused sheet (thinking on, clearer synergy definition)

Same model, `qwen/qwen3.8-27b`, on the 60 rows of `adjudication_focused.csv`, with thinking on and a
prompt (v2) that says "better than either alone" is synergy only when it exceeds the sum of the single
effects (`second_rater.py --focused`, answers in `adjudication_focused_rater.csv`).

- **Most hard rows cannot be decided from the text: 28 of 60 are now "unclear".** By selection reason:
  inferred labels 12/16, inferred and on the boundary 13/21, boundary with a stated label 3/18, random
  check 0/5. The papers do not report both single effects well enough to compare with their sum.
- **The first run's synergy calls were mostly loose wording.** 16 classes changed; 11 of them were
  synergy and became unclear (7) or sub-additive (4). The rest changed in both directions by one row.
- **Extracted classes on these rows:** synergy 15 -> synergy 8, unclear 6, sub-additive 1; sub-additive
  12 -> sub-additive 4, unclear 7, synergy 1; additive 6 -> additive 3, synergy 2, sub-additive 1;
  occlusion 4/4 and no added effect 4/6 kept; antagonism 5 -> 1 kept.
- **All three (extraction, run 1, run 2) agree on 27 rows**: unclear 8, synergy 8, occlusion 4, no added
  effect 4, additive 3.
- **Still uninformative on whether the paper ran the experiment** (0 of 60 "no" in both runs).

So the stated synergy labels are about half right and inferred labels mostly cannot be checked from the
text; the decision to model on stated labels without sub-additive stands, and synergy should be treated
as provisional too. The focused sheet now has a `priority` column for the human reviewer: 1 for the 19
rows where the raters split three ways or the second run found the text insufficient, 2 for the 14 with
a partial split, 3 for the 27 where all three agree (lowest value to check, except for whether the paper
ran it). The AI answers themselves are still not shown.
