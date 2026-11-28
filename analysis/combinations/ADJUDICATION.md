# Expert check of the combination records

`adjudication_sample.csv`: 120 of the 635 records, one per row (45 are cases the model was scored on;
every synergy and additive record among those is included, and each interaction class has at least
6). Open it in a spreadsheet, read `quote` and `context` (the paper text around the quote, quote in
the middle), open `pubmed` if you need more, and fill the `expert_*` columns. About 3 minutes a row.
The extracted columns were written by an AI session; treat them as claims to check, not as defaults.

| Column | Fill with |
|---|---|
| `expert_ran_in_paper` | y if the paper itself ran this combination and reports a result; n if it is background, methods, another group's work or a hypothesis. If n, leave the rest blank. |
| `expert_interventions_ok` | y if the listed interventions (agent, action loss/gain/drug, target) are right and given together |
| `expert_readout_ok` | y if the readout is the one the quote reports |
| `expert_direction_combination` | how the readout moved with the combination against the injured, untreated control: `1` rose, `-1` fell, `0` no change. Direction of the *named readout* (a threshold that rose is `1`) |
| `expert_direction_a`, `expert_direction_b` | the same for each intervention alone, in the order listed, `0` if not reported |
| `expert_interaction` | one of `synergy` (more than the sum), `additive`, `sub_additive` (more than either alone, less than the sum), `no_added_effect` (no more than the stronger one), `occlusion` (one intervention abolishes the other's effect, e.g. no effect in knockouts), `antagonism` (combination does less than one alone), `unclear` |
| `expert_in_context` | y if the experiment is in vivo in a rodent nerve-injury model (not cultured cells, human, other injury) |
| `reviewer`, `notes` | your initials; anything odd |

Score the returned sheet with `python3 analysis/scripts/prepare_combination_adjudication.py score`. It
reports how often the paper ran the experiment, how often the interventions and readout are right, and
how often the interaction class and direction agree (exactly and on the three coarse classes: less than
additive, additive, synergy). Those rates bound every figure in `results.md`; in particular, if "less than
additive" labels are often really "unclear", the 84% majority baseline is itself an artefact.
