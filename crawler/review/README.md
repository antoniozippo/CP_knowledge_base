# Review of auto-crawled links between two curated nodes (2026-11)

`curated_links_review_2026-11.csv`: one row per auto-crawled link whose two endpoints are both
curated nodes (504 links in `graphify-out/graph_v2.json` at the commit that added this file;
`graph_link_index` is the position in `links`). Read by Claude, not by a domain expert: every
link was judged from its verbatim quote alone (the paper text was consulted only for matching
checks), so treat the verdicts as a triage, not a ruling. The graph itself is unchanged:
all these links are still `UNREVIEWED`.

Verdicts
- `OK`: the quote states, or through loss/gain of function clearly implies, the stated effect and direction.
- `CONTEXT`: supported, but only in a narrow setting (disc, endometriosis, stem cells, one brain region...) or contradicted by another link on the same pair in another setting.
- `OVERSTATED`: direction right, predicate stronger than the evidence (hedged, correlation coded as causal, "contributes" coded as "causes").
- `WEAK`: the quote does not name an endpoint, is a hypothesis, or cannot be checked from the quote.
- `WRONG`: wrong sign or direction, an entity merged into the wrong node, or a null result recorded as a relation.

## After the matcher fixes
The review found 23 `WRONG` links: 13 were entities merged into the wrong node and 10 were
extraction errors. The matcher fixes (stricter fuzzy and parenthetical matching, `crawler/no_merge.yaml`)
and the re-merge that followed removed all 13 entity-merge errors: each of those quotes now sits on
a link between the right nodes.

## Extraction errors fixed
The 10 extraction errors are fixed; the `fixed` column says how, and `graph_inference.py` stops
excluding a row once it is filled in.
- 8 were the extractor's own mistakes, corrected in `extraction_corrections_2026-11.yaml`:
  4 null results and 1 co-regulation dropped (SP and CGRP "dispensable" or "not essential", B1R
  "not affected", alpha-CGRP knockouts "not different", NKCC1 and KCC2 changing together), and
  3 reversed (TNF-alpha acts through TRPV1; spinal microglia express TLR4; CGRP+ DRG neurons
  express Nav1.7).
- 2 (Nav1.7 -> congenital insensitivity to pain, resiniferatoxin -> CGRP) had the right sign in
  the extraction (-1); the fixed sign of the verb ("causes", "releases") overrode it. That rule
  is changed (`crawler/extractor.py:normalize_sign`): a sign that contradicts its verb is kept and
  the verb becomes "modulates". The same override had flipped 14 more papers on 10 other links
  (for example "HMGB1 destroys the blood-brain barrier" stored as +1, "P2X7 inhibitors prevented
  muscle pain" stored as P2X7 preventing pain); they are corrected too.

`crawler/correct_links.py` applies both to `crawler/extractions/` and the graph, and is idempotent.

`graph_link_index` refers to the graph at the commit that added the CSV. The re-merge re-ordered
the crawled links, so find a row in the current graph by `pmid` + `quote` + endpoint labels, not by index.
