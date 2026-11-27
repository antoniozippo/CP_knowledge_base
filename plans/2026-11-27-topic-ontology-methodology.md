# Topic ontologies from the literature: method, honest assessment, and plan

*Status: unfinished draft, 2026-11-27. The text stops partway through step 7 of section 4;
sections 5 to 8 and the appendix are not written yet. Purpose: turn what this repository does for chronic pain into a
method that builds an ontology and an evidence graph for any disease or topic, and say plainly
what the current build does and does not achieve. Numbers are from the repository at commit
`91da053`; Appendix A says how to reproduce each one.*

---

## Summary

**What exists.** For chronic pain, an LLM-driven pipeline has turned about 70 dossiers and 3,766
papers into a signed knowledge graph: 3,534 nodes and 6,485 links. Every crawled link points at a
verbatim sentence in its paper. Curation decisions (merges, splits, corrections, conflict
resolutions) are kept as data and applied by tested, idempotent tools. On top sit a signed-path
inference, a web explorer, and an agent simulator.

**What it is not, yet.** It is not an ontology, and some of its quality claims are weaker than they
look:

| Finding | Evidence |
|---|---|
| Nodes are free-text labels, not concepts | 2,978 of 3,534 nodes were made from names in papers; 64% of those have one link. TNF-α is three curated nodes (443, 17 and 5 links), one per dossier. 36 labels contain "microglia". |
| Labels mix things that ontologies keep apart | "mechanical allodynia in female mice" is a phenotype plus a context; 173 of 556 curated nodes are "Rationale" statements, i.e. arguments, not biology. |
| Links say little | A link is a verb and a sign. 80% of evidence quotes name no species or system; only 3% mention humans. 93% of crawled links rest on one paper. |
| Non-causal findings were coerced | Null results, correlations and "loss of X causes Y" were stored as signed causal links; one rule alone flipped 41 relationships. |
| Quality is measured by the producer | The only error estimate for crawled links (4.6% wrong, 18% qualified, 504 links) is an AI triage by the same model family that extracted them, on the easiest subset. |
| The "curated" layer is not expert-validated | Of 262 dossier claims checked in August, 47% were confirmed or extended, 5% refuted or mixed, 21% found no evidence, 26% were not reviewed. |
| The inference's headline check is mostly base rate | "Two-hop paths reproduce a link's sign 90% of the time." Each source node's usual sign alone scores 86% on the same links. With paths from other papers, composition beats that baseline in only 57% of the cases where they disagree (95% CI 49–66%). |

**What to build instead.** Each topic becomes three linked products made from immutable inputs and
curation overlays:

1. a **topic ontology**: classes with IDs, definitions and hierarchy, mostly imported from
   reference ontologies;
2. an **assertion store**: each finding as a grounded subject and object, a typed predicate with
   qualifiers (which aspect changed, in which direction), its context (species, model, anatomy,
   sex, dose), its kind (causal, correlational, null), and its evidence;
3. **views** assembled from the store: graph exports, inference, explorer.

Section 4 defines the method in twelve steps. Section 5 describes the code as configurable "topic
packs". Section 6 lists revisions to the pain build in priority order, and section 7 is a phased
plan with acceptance criteria.

---

## 1. Terms

| Term | Meaning here |
|---|---|
| Topic | A disease, symptom domain or biological theme, bounded by its competency questions. |
| Competency question | A question the ontology and graph must answer ("which interventions reduce mechanical allodynia in rodent nerve-injury models through microglia, and in how many independent labs?"). Used to scope the work and to test it. |
| Ontology | Classes with stable IDs, definitions, synonyms, `is_a`/`part_of` hierarchy and mappings. Says what kinds of things there are. Changes slowly. |
| Assertion | One claim: subject, predicate, object, qualifiers and context ("in male rats after CCI, intrathecal X decreases spinal TNF-α protein"). |
| Evidence | A passage that supports or contradicts an assertion: PMID, section, verbatim quote, study type, extractor and prompt version. |
| Knowledge graph (view) | Assertions aggregated over their evidence, optionally filtered by context, drawn as nodes and edges. A view, not the source of truth. |
| Grounding | Mapping a name in text to an ontology ID. |
| Overlay | A curation decision kept as data (merge, split, correction, verdict, context assignment) and applied at build time. Inputs are never edited. |

The current build has one object, the graph, standing in for all of these. Most problems in
section 3 come from that.

---

## 2. The current approach, as built

| Stage | What it does | Where | Scale |
|---|---|---|---|
| Dossiers | ~70 markdown notes, one per molecule, pathway or mechanism. How they were written and who checked them is not recorded. | `*.md` at the root | ~205,000 words in the 104 files the graph builder read |
| Base graph | `graphify` extracts entities and relations from the notes with an LLM (87% "extracted", 12% "inferred"). Node IDs are scoped by note. | `graphify-out/graph.json` | 678 nodes, 956 links |
| Graph v2 | Label normalization merges same-name nodes; regex rules set entity type, compartment and sign; degree sets tiers. | `analysis/scripts/build_graph_v2.py` | 554 nodes, 914 links |
| Claims and verdicts | 262 claim cards from the dossiers; ten LLM literature sweeps; verdicts written by hand from the sweeps. | `analysis/claims/`, `analysis/literature/`, `build_verdicts.py` | 86 confirmed, 37 extended, 8 refuted, 6 mixed, 56 no evidence, 69 unreviewed |
| Closure and splits | Links added from dossier quotes where paths dead-ended; nodes split where one label carried opposed pools. | `add_closure_edges.py`, `split_nodes.py` | 38 closure links, 1 split |
| Crawler | 10 themes of PubMed queries with a pain filter, 2021 onward; abstract plus PMC full text; one LLM extraction per paper (Claude Code sessions); verbatim-quote check; sign from verb; names matched to nodes; links and evidence added; contradictions logged. | `crawler/` | 5,478 papers retrieved, 50% with full text, 3,766 extracted, 12,993 relationships, 5,568 links |
| Review and curation | AI triage of 504 links; conflicts resolved; nodes merged and split; extraction errors corrected. | `crawler/review/`, `analysis/claims/*.yaml`, `crawler/correct_links.py`, `analysis/scripts/merge_nodes.py` | 23 wrong links fixed, 3 conflicts resolved |
| Inference | Signed paths to 20 core pain nodes; drug and target rankings, chokepoints, loops, calibration. | `analysis/scripts/graph_inference.py` | 5,395 signed links |
| Explorer | Web page with views for different readers and a shared review queue. | `analysis/explorer/` | 800 review rows |
| Simulator | One agent per curated node; rules, plus LLM agents at hubs. | `simulator/` | 374 cards, 19 regression facts |

---

## 3. Honest assessment

### 3.1 What works and should be kept

1. **Verbatim evidence.** Every crawled link points at a sentence that exists in its paper; a
   paraphrased or invented quote is dropped before it reaches the graph.
2. **Evidence accumulates, verdicts are never overwritten.** A new paper adds evidence; a
   contradiction goes to a conflict log for a person (`crawler/conflicts.yaml`).
3. **Curation as data.** Merges, splits, corrections and conflict resolutions are YAML files
   applied by idempotent tools that refuse unsafe changes, with 798 tests behind them.
4. **Review by impact.** Ranking unchecked links by how much inference runs through them found
   the errors that mattered (the sign rule, the AM1241 dose context) quickly.
5. **Context-specific nodes** resolved every contradiction examined so far (BDNF→KCC2 after
   injury vs exercise; ROS→HIF-1α in nerve vs hyperoxic tendon; low-dose AM1241). The idea is
   right; making a new node each time is not (see 3.2c).

### 3.2 What does not work yet

**a) A graph of labels, not an ontology.** A node is whatever string a dossier or paper used.
Consequences in this build:
- Duplicates. TNF-α is three curated nodes because node IDs are scoped by dossier; MCC950 is two;
  PPAR-gamma and PPARγ were two until November. 13 of the 23 wrong links in the review were names
  matched to the wrong node (EP2 to Tie2, MPTP the toxin to mPTP the pore, chondroitin sulfate
  to CSPGs).
- Fragmentation. 64% of crawled nodes have a single link, so most of the graph cannot take part
  in any path; "microglia" appears in 36 labels.
- Mixed kinds. Labels fuse a phenotype with its inducer or sex ("Oxaliplatin-induced mechanical
  allodynia", "mechanical allodynia in female mice"); 173 curated nodes are arguments
  ("Rationale: BDNF has both pro- and anti-nociceptive roles"), and 9 come from images.
- No hierarchy, definitions or IDs, so nothing connects "spinal microglia" to "microglia" or a
  drug to its target class, and nothing can be shared with other resources.

**b) Links say too little.** The schema is a verb and a sign. It cannot say *what* changed
(expression, activity, release, integrity), so "HMGB1 causes [breakdown of] the blood-brain
barrier" became +1; the rule that let the verb override the extracted sign flipped 41
relationships before it was found. Null results ("not essential", "did not differ") and
correlations ("patients with severe pain had lower TNF-α") were stored as causal signs. At least
2% of quotes use correlational wording under a causal verb, and 8% are hedged (regex estimates).

**c) Context is lost.** 80% of evidence quotes name no species or system and only 3% mention
humans; dose, model, sex, tissue and time are not extracted. Every context problem found so far
was fixed by hand, one node at a time.

**d) Evidence is shallow and selected.** 93% of crawled links rest on one paper. The crawl covers
2021 onward, so older foundational findings come only from the dossiers; half the papers were
read from the abstract alone; 1,712 retrieved papers have no extraction yet. Discarding null
results biases the graph toward effects.

**e) Quality is measured by the producer.** The review of 504 links was Claude reading Claude's
extractions, so shared blind spots are invisible to it. The sample was links between two
curated nodes, probably the easiest case. There is no human-adjudicated gold standard, so the
4.6% "wrong" rate is a floor, not an estimate.

**f) The "curated" layer is not expert-validated.** The dossiers' provenance is not recorded,
and the August check found independent support for under half of their claims. In code and in
the explorer they are nonetheless called "curated" and weighted 0.6–0.95, above any crawled link.

**g) The inference's validation is weaker than reported.** Measured on the same links
(Appendix A):

| Predictor of a direct link's sign | Accuracy |
|---|---|
| Majority sign | 59.7% |
| Composition with signs shuffled across links | 49.9% |
| Composition with signs shuffled within each source's out-links | 73.6% |
| The source node's usual sign (its other out-links) | 86.2% |
| Two-hop composition, all paths | 90.9% |
| Two-hop composition, paths from other papers only | 87.0% (source baseline 84.6% on the same 747 links) |
| Where composition and the source baseline disagree, composition is right | 68% (all paths); **57%, 95% CI 49–66%, with paths from other papers** |

Composition adds a little beyond "drugs usually inhibit, cytokines usually raise", and almost
nothing once same-paper co-reporting is removed. The drug ranking separates known analgesics from
other drugs with AUC 0.61. Link weights (0.45 + 0.07 per paper, 0.6–0.95 by verdict), the path
decay of 0.7 and the tanh cap were chosen, not fitted. Pain outcomes and pain types are defined
by regular expressions on labels, which once counted "Calpain" as pain.

**h) Engineering debt.** The graph file is mutable state; conflicts point at links by list
position, so every tool must guard positions. Some corrections edit the raw extraction files.
The rebuild order (base graph, splits, closure, crawl, merges, corrections) lives in a runbook,
not a build. Pain is hard-coded in search filters, entity and compartment rules, inference
patterns and explorer text.

**i) The simulator is downstream and unvalidated as biology.** Its README reports that LLM hub
agents add +0.12 to pain in every injury model and that a naive animal drifts from 0.05 to 0.25
over 180 days. It passes 19 regression facts. It should not feed back into the ontology.

### 3.3 What this means

The pipeline is good at **finding and tracing** claims. It is weak at saying **what a claim is
about** (grounding), **under which conditions it holds** (context), and **how much to believe it**
(calibrated evidence). An ontology-backed design supplies exactly those three.

---

## 4. The method in twelve steps

Each step lists its purpose, method, outputs, a quality gate that must pass before the next step
relies on it, and a remark drawn from the pain build.

### Step 1. Scope the topic with competency questions

- **Purpose.** Decide what the ontology and graph are for, so that everything else can be judged
  against it.
- **Method.** With two or three domain experts, write 20–40 competency questions covering
  mechanisms, interventions, outcomes and contradictions. Fix inclusion rules: species, study
  types, years, languages, and whether reviews count as evidence.
- **Outputs.** `scope.md`, `competency_questions.md` (each with an expected answer shape), and
  the evaluation plan.
- **Gate.** Every later artifact names the questions it serves.
- **Remark.** The pain build started from dossiers and themes, not questions. That is why
  "pain" ended up defined by a regex, and why nothing records whether a rat model or a human
  study answers a given question.

### Step 2. Reuse reference ontologies and fix the schema

- **Purpose.** Never invent a class or relation that already exists.
- **Method.**
  - Choose a source per entity kind: genes and proteins (HGNC, NCBI Gene, UniProt), chemicals
    and drugs (ChEBI, ChEMBL), diseases (MONDO, MeSH), phenotypes and symptoms (HPO), anatomy
    (UBERON), cell types (CL), processes (GO), pathways (Reactome), species (NCBITaxon),
    evidence types (ECO), assays and models (OBI, plus a small local list of animal models).
  - For assertions, adopt the Biolink Model: categories, predicates, and qualifiers (for
    example `object_aspect_qualifier`, `object_direction_qualifier`, `qualified_predicate`,
    `species_context_qualifier`, `anatomical_context_qualifier`).
  - Write the schema in LinkML so that one file generates the validators, the JSON Schema for
    LLM extraction, and the export formats.
- **Outputs.** `schema.yaml` (LinkML), an ID policy (CURIE prefixes, how local IDs are minted),
  the list of imported ontology subsets.
- **Gate.** Every node kind and every predicate in the topic maps to the schema.
- **Remark.** The missing qualifier explains the sign-rule bug. "X causes [loss of] Y" needs an
  object aspect and a direction, not a verb with a fixed sign.

### Step 3. Seed the topic

- **Purpose.** Know the core concepts before reading papers, so extraction and grounding have
  targets.
- **Method.** Take the relevant ontology subtrees (for pain: the HPO pain branch, MONDO
  neuropathy and pain conditions, GO terms for neuroinflammation and synaptic plasticity, CL glia
  and neuron types, UBERON nervous system, ChEBI analgesics), using OAK or OLS. Add expert seed
  lists, and dossiers if any, as *candidate* concepts. Then add terms discovered from the
  literature (MeSH co-occurrence, as the crawler already does).
- **Outputs.** A seed concept table (ID, label, synonyms, source, why included).
- **Gate.** Experts sign off on the seed list and its boundary.
- **Remark.** Dossiers are useful seeds, but here they became the "curated" truth layer without
  validation. Seeds should go through the same evidence pipeline as everything else.

### Step 4. Retrieve the literature systematically

- **Purpose.** Know what was searched and what was missed.
- **Method.**
  - Build queries from seed concepts and synonyms, combining MeSH and free text, with the
    topic filter as configuration.
  - Log every query, date and count, PRISMA-style.
  - Measure recall against a known-item set: 50–100 papers experts say must be found.
  - Include foundational older work, not only recent years.
  - Prefer full text (PMC open access, Europe PMC) and record licences.
- **Outputs.** A corpus manifest (PMID, source, full text or abstract, licence, query) and a
  recall report.
- **Gate.** Recall on the known-item set reaches the target, for example 90%.
- **Remark.** The crawl starts in 2021 and has no recall measurement. Half of it is abstract-only,
  where context such as dose and species is least likely to appear.

### Step 5. Extract assertions with context

- **Purpose.** Capture what each paper reports, in the schema, with what it needs to be judged.
- **Method.**
  - Generate the extraction schema from LinkML; tools such as OntoGPT/SPIRES do this.
  - Per finding, extract: subject and object mentions; predicate; object aspect and direction;
    claim kind (`causal_intervention`, `causal_genetic`, `correlation`, `null`,
    `background_statement`); context (species, strain, sex, model, tissue or cell, dose, route,
    time); and the verbatim quote with its section.
  - Keep the quote check.
  - Never coerce: a null result is stored as a null assertion, a correlation as a correlation.
  - Pin and record model, prompt and schema versions; store raw output unchanged.
- **Outputs.** Raw extraction files (immutable) and an extraction log.
- **Gate.** Field-level precision on the gold set (step 10) at or above the agreed threshold, for
  example 0.85 for predicate, direction and claim kind, before the run is scaled up.
- **Remark.**
  - The AM1241 error came from a context field that did not exist: 0.03 µg intrathecal, with
    morphine, in a cancer-pain model.
  - The pancreatitis error came from a claim kind that did not exist (correlation).
  - The NKCC1/KCC2 error was co-regulation recorded as cause.

### Step 6. Ground every name

- **Purpose.** One concept, one ID.
- **Method.**
  - Use precomputed normalizations where they exist. PubTator3 covers genes, chemicals,
    diseases, species, variants and cell lines in PubMed.
  - Ground the rest with dictionary and synonym matching from the seed ontologies (OAK, Gilda),
    then embedding retrieval, then LLM adjudication between the top candidates.
  - Never match on fuzzy string distance alone.
  - Unresolved mentions go to a staging namespace with a review queue.
  - Express states and contexts by post-coordination, not as new classes: "microglial
    activation" is the GO process on the CL cell type; "oxaliplatin-induced mechanical
    allodynia" is the HPO phenotype with an inducer qualifier.
- **Outputs.** A mention-to-ID table with method and score, plus a staging list.
- **Gate.** Grounding precision on a sample of 300 mentions of at least 0.95 for genes and
  chemicals and at least 0.85 for processes and cell states; under 10% of mentions in staging.
- **Remark.** Label matching produced 13 merge errors and dozens of duplicates, and needed a
  growing list of special cases (`no_merge.yaml`, symbol-owner rules, class qualifiers). Grounding
  replaces that list with IDs.

### Step 7. Store evidence and assemble assertions

- **Purpose.** Separate what each paper says from what the topic concludes.
- **Method.**
  - Each extracted finding becomes an evidence row.
  - Evidence with the same grounded subject, predicate, object, qualifiers and compatible
    context is aggregated into an

*[Draft ends here. The rest of step 7 and sections 5 to 8 are not written yet.]*
