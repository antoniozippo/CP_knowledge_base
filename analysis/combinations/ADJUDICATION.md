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

## Second rater: a local AI model

`analysis/scripts/second_rater.py` asks a model served with an OpenAI-compatible API (llama.cpp, vLLM,
LM Studio, Ollama) to fill the same fields, from the same quote and context. It is **not shown** the
extracted directions or interaction class, so it is not anchored on them. Answers go to
`adjudication_second_rater.csv`, never into the expert's sheet. Standard library only; rows already
answered are skipped on a restart.

    python3 analysis/scripts/second_rater.py --endpoint http://192.168.1.87:8888   # --limit 5 for a trial
    python3 analysis/scripts/second_rater.py --score

It must run on a machine that can reach the model (the address above is on the owner's local network,
not reachable from cloud sessions). It is a second opinion, not an expert: its agreement with the
extraction says how reproducible the labels are; its agreement with the human expert, once the sheet is
filled, says how far an AI rater can stand in for one.
