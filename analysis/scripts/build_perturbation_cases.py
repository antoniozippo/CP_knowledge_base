#!/usr/bin/env python3
"""Build the perturbation validation set for the functional model (scope phase 2).

A test case is one experiment reported in a paper: an actor was perturbed (knocked down,
inhibited, activated, a drug given) and a readout moved. The functional model must reproduce
the direction. Cases are read from the crawler's extractions (crawler/extractions/*.json), whose
relationships already carry a verbatim quote and a sign meaning "more subject -> more (+1) or less
(-1) object". This script

  1. keeps relationships whose quote describes a perturbation,
  2. finds the actor: the subject, or the target named by an agent ("TLR4 siRNA" -> TLR4, loss),
  3. grounds actor and readout to graph nodes with the crawler's matcher,
  4. keeps readouts that are pain behaviour (any pain outcome node, with its modality) or one of
     the configured markers; a withdrawal threshold or latency counts as pain, inverted,
  5. derives the implied sign (raising the actor's activity moves the readout this way) and,
     where the perturbation is known, the observed change,
  6. assigns context from the paper's abstract and methods (nerve-injury model, species) and
     the quote (a quote naming another model is out of context),
  7. drops null results and flags hedged, background and review statements,
  8. merges repeats within a paper and splits cases into build and test sets by PubMed entry
     order (the most recent papers are the test set).

Outputs in analysis/perturbation/: cases.csv (every candidate with its status), summary.md,
adjudication_sample.csv (primary cases for a domain expert to check). See README.md there.

Usage: python3 analysis/scripts/build_perturbation_cases.py [--markers-only]
  --markers-only  print which readout nodes the in-context experiments measure, to choose markers
"""

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_inference as gi  # noqa: E402

OUT_DIR = ROOT / "analysis" / "perturbation"
CONFIG = OUT_DIR / "config.yaml"
EXTRACTIONS = ROOT / "crawler" / "extractions"
CACHE = ROOT / "crawler" / "cache"
METHODS_SECTION = re.compile(r"method|material|animal|experiment|procedure|surgery|model", re.I)
REVIEW_HINT = re.compile(r"\b(?:this|the present|our) review\b|\bwe (?:review|summari[sz]e)\b|\bnarrative review\b|\bsystematic review\b", re.I)
BACKGROUND = re.compile(r"\[\d+(?:[,–-]\d+)*\]|\(\w+ et al\.,? \d{4}\)|\bhas been shown\b|\bhave been shown\b|\bis known to\b|\bprevious(?:ly)? stud", re.I)
FIELDS = ["case_id", "status", "split", "pmid", "actor", "actor_node", "actor_label", "perturbation", "readout",
          "readout_node", "readout_label", "readout_class", "modality", "inverted", "extracted_sign", "implied_sign",
          "observed_change", "context", "models", "other_models", "species", "paper_type", "flags", "subject",
          "predicate", "object", "quote", "repeats"]


def compile_all(d):
    return {k: re.compile(v, re.I) for k, v in d.items()}


class Config:
    def __init__(self, path=CONFIG):
        c = yaml.safe_load(Path(path).read_text())
        ctx, p, r = c["context"], c["perturbation"], c["readouts"]
        self.nerve = compile_all(ctx["nerve_injury_models"])
        self.species = compile_all(ctx["species"])
        self.rodent = set(ctx["rodent"])
        self.non_rodent = re.compile(ctx["non_rodent_quote"], re.I)
        self.in_vitro = re.compile(ctx["in_vitro_quote"], re.I)
        self.other = compile_all(ctx["other_models"])
        self.context_name = ctx["name"]
        self.agent_suffix = re.compile(rf"^(?P<core>.+?)[\s-]*(?P<kind>{p['loss_agent']}|{p['gain_agent']})$", re.I)
        self.agent_prefix = re.compile(rf"^(?P<kind>{p['loss_agent']}|{p['gain_agent']})\s+(?:of\s+)?(?P<core>.+)$", re.I)
        self.anti = re.compile(r"^anti-(?P<core>.+?)(?:\s+(?:antibod(?:y|ies)|mAb|treatment))?$", re.I)
        self.loss_agent = re.compile(rf"^(?:{p['loss_agent']})$", re.I)
        self.any = re.compile(rf"\b(?:{p['any']})", re.I)
        self.loss_words = re.compile(rf"\b(?:{p['loss_words']})", re.I)
        self.gain_words = re.compile(rf"\b(?:{p['gain_words']})", re.I)
        self.modalities = compile_all(r["modalities"])
        self.inverted = re.compile(r["inverted_readout_label"], re.I)
        self.pain_label = re.compile(r["pain_label"], re.I)
        self.not_pain_label = re.compile(r["not_pain_label"], re.I)
        self.markers = {str(k): v for k, v in (r.get("markers") or {}).items()}
        self.target_note = {name: re.compile(rf"\b(?:{sym})\b[\w\s()/-]{{0,30}}?\b(?:antagonists?|inhibitors?|agonists?|blockers?)\b", re.I)
                            for name, sym in (r.get("marker_symbols") or {}).items()}
        self.test_fraction = c["split"]["test_fraction"]
        self.sample_size = c["adjudication"]["sample_size"]
        self.seed = c["adjudication"]["seed"]


# ------------------------------------------------------------------ parsing


def parse_actor(subject, cfg):
    """(actor name, 'loss' | 'gain' | None): the target of an agent named as subject, else the subject."""
    name = subject.strip()
    m = cfg.anti.match(name)
    if m:
        return m.group("core").strip(), "loss"
    for rx in (cfg.agent_suffix, cfg.agent_prefix):
        m = rx.match(name)
        if m and len(m.group("core").strip()) >= 2:
            return m.group("core").strip(" -"), "loss" if cfg.loss_agent.match(m.group("kind")) else "gain"
    return name, None


def perturbation_from_quote(quote, cfg):
    loss, gain = bool(cfg.loss_words.search(quote)), bool(cfg.gain_words.search(quote))
    return "loss" if loss and not gain else "gain" if gain and not loss else None


def modality(label, quote, cfg):
    for text in (label, quote):
        for name, rx in cfg.modalities.items():
            if rx.search(text):
                return name
    return "general"


def paper_context(pmid, cfg, cache_dir=CACHE):
    """Models, other models, species and paper type from a paper's abstract and methods."""
    path = Path(cache_dir) / f"paper_{pmid}.json"
    if not path.exists():
        return {"models": set(), "other": set(), "species": set(), "paper_type": "unknown"}
    d = json.loads(path.read_text())
    abstract = d.get("abstract_text") or ""
    sections = d.get("fulltext_sections") or {}
    methods = " ".join(t for name, t in sections.items() if METHODS_SECTION.search(name))
    text = abstract + " " + methods
    if sections:
        paper_type = "primary" if methods else ("review" if REVIEW_HINT.search(abstract) or len(sections) > 0 else "unknown")
    else:
        paper_type = "review" if REVIEW_HINT.search(abstract) else "primary?"
    return {"models": {k for k, rx in cfg.nerve.items() if rx.search(text)},
            "other": {k for k, rx in cfg.other.items() if rx.search(text)},
            "species": {k for k, rx in cfg.species.items() if rx.search(text)},
            "paper_type": paper_type}


# ------------------------------------------------------------------ building


class Grounder:
    """Names to graph nodes, through the crawler's matcher, memoized."""

    def __init__(self):
        from crawler.matcher import EntityMatcher
        self.m = EntityMatcher()
        self.memo = {}

    def __call__(self, name):
        if name not in self.memo:
            r = self.m.match_entity(name)
            self.memo[name] = (r.matched_node_id, r.matched_label) if r.matched_node_id else (None, None)
        return self.memo[name]


def readout_of(node, label, sg, cfg):
    """(class, inverted) for a readout node, or (None, False) when it is not a readout."""
    if node is None:
        return None, False
    if cfg.inverted.search(label or ""):
        return "pain", True
    if node in sg.pain or (cfg.pain_label.search(label or "") and not cfg.not_pain_label.search(label or "")):
        return "pain", False
    if node in cfg.markers:
        return "marker", False
    return None, False


def candidate_cases(cfg, sg, ground, extractions_dir=EXTRACTIONS, cache_dir=CACHE):
    contexts = {}
    for path in sorted(Path(extractions_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pmid = str(data.get("pmid") or path.stem)
        for rel in data.get("relationships", []):
            quote = rel["evidence_quote"]
            if not cfg.any.search(quote) or rel.get("sign", 0) == 0:
                continue
            obj_node, obj_label = ground(rel["object"])
            rclass, inverted = readout_of(obj_node, obj_label, sg, cfg)
            if rclass is None:
                continue
            if pmid not in contexts:
                contexts[pmid] = paper_context(pmid, cfg, cache_dir)
            yield pmid, rel, obj_node, obj_label, rclass, inverted, contexts[pmid]


def make_case(pmid, rel, obj_node, obj_label, rclass, inverted, ctx, sg, ground, cfg):
    quote, sign = rel["evidence_quote"], int(rel["sign"])
    actor_name, agent = parse_actor(rel["subject"], cfg)
    actor_node, actor_label = ground(actor_name)
    if actor_node is None and agent:
        actor_node, actor_label = ground(rel["subject"])        # an agent with a node of its own
        agent = None if actor_node else agent
        actor_name = rel["subject"] if actor_node else actor_name
    readout_sign = -1 if inverted else 1                         # a threshold rising means less pain
    if agent:
        perturbation = agent
        implied = sign * (-1 if agent == "loss" else 1) * readout_sign
        observed = sign * readout_sign
    elif actor_node in sg.drugs:
        perturbation, implied, observed = "drug", sign * readout_sign, sign * readout_sign
    else:
        perturbation = perturbation_from_quote(quote, cfg) or "unspecified"
        implied = sign * readout_sign
        observed = implied * (-1 if perturbation == "loss" else 1) if perturbation in ("loss", "gain") else ""
    q_models = {k for k, rx in cfg.nerve.items() if rx.search(quote)}
    # a model named in the quote or in the readout's own label ("oxaliplatin-induced mechanical allodynia")
    readout_text = f"{rel['object']} {obj_label or ''}"
    q_other = {k for k, rx in cfg.other.items() if rx.search(quote) or rx.search(readout_text)}
    rodent = bool(ctx["species"] & cfg.rodent) or bool(re.search(r"\brats?\b|\bmice\b", quote, re.I))
    flags = []
    if cfg.non_rodent.search(quote):
        context = "non-rodent organism (quote)"
    elif cfg.in_vitro.search(quote):
        context = "cell culture (quote)"
    elif q_other and not q_models:
        context = "other model (quote)"
    elif (ctx["models"] or q_models) and rodent:
        context = cfg.context_name
        if ctx["other"] and not q_models:
            flags.append("mixed models in paper")
    elif ctx["models"] or q_models:
        context = "nerve injury, species unclear"
    else:
        context = "other or unstated model"
    if re.search(r"\bnaive\b|\bnaïve\b|\bsham\b", quote, re.I):
        flags.append("in naive or sham animals")
    if gi.HEDGE.search(quote):
        flags.append("hedged")
    if BACKGROUND.search(quote):
        flags.append("background statement")
    readout_label = "pain" if rclass == "pain" else cfg.markers[obj_node]
    status = "primary"
    if gi.NULL_WORDING.search(quote):
        status = "excluded: null result"
    elif actor_node is None:
        status = "excluded: actor not in graph"
    elif actor_node == obj_node:
        status = "excluded: actor is the readout"
    elif rclass == "marker" and readout_label in cfg.target_note and cfg.target_note[readout_label].search(quote):
        status = "excluded: drug and its own target"
    elif context != cfg.context_name:
        status = f"excluded: {context}"
    elif ctx["paper_type"] == "review" or "background statement" in flags:
        status = "excluded: review or background statement"
    elif perturbation == "unspecified":
        status = "excluded: perturbation unclear"
    return {
        "status": status, "pmid": pmid, "actor": actor_name, "actor_node": actor_node or "", "actor_label": actor_label or "",
        "perturbation": perturbation, "readout": readout_label if rclass == "marker" else "pain",
        "readout_node": obj_node, "readout_label": obj_label, "readout_class": rclass,
        "modality": modality(obj_label or "", quote, cfg) if rclass == "pain" else "", "inverted": int(inverted),
        "extracted_sign": sign, "implied_sign": implied, "observed_change": observed, "context": context,
        "models": ";".join(sorted(ctx["models"] | q_models)), "other_models": ";".join(sorted(ctx["other"] | q_other)),
        "species": ";".join(sorted(ctx["species"])), "paper_type": ctx["paper_type"], "flags": ";".join(flags),
        "subject": rel["subject"], "predicate": rel["predicate"], "object": rel["object"], "quote": quote,
    }


def merge_repeats(cases):
    """One case per paper, actor, perturbation and readout node; the first quote is kept."""
    out, seen = [], {}
    for c in cases:
        key = (c["pmid"], c["actor_node"] or c["actor"], c["perturbation"], c["readout_node"], c["status"])
        if key in seen:
            first = seen[key]
            first["repeats"] += 1
            if first["implied_sign"] != c["implied_sign"]:
                first["flags"] = ";".join(filter(None, [first["flags"], "paper disagrees with itself"]))
            continue
        c["repeats"] = 1
        seen[key] = c
        out.append(c)
    return out


def assign_split(cases, test_fraction):
    pmids = sorted({int(c["pmid"]) for c in cases if c["status"] == "primary"})
    cut = pmids[int(len(pmids) * (1 - test_fraction))] if pmids else 0
    for c in cases:
        c["split"] = ("test" if int(c["pmid"]) >= cut else "build") if c["status"] == "primary" else ""
    return cut


def consistency(cases):
    """For each actor and readout studied by two or more papers: do the papers agree on the sign?"""
    by = defaultdict(dict)
    for c in cases:
        if c["status"] == "primary":
            key = (c["actor_node"], c["readout"] if c["readout_class"] == "marker" else "pain")
            by[key].setdefault(c["pmid"], c["implied_sign"])
    pairs = agree = 0
    contested = []
    for key, per_paper in by.items():
        signs = list(per_paper.values())
        if len(signs) < 2:
            continue
        for i in range(len(signs)):
            for j in range(i + 1, len(signs)):
                pairs += 1
                agree += signs[i] == signs[j]
        if len(set(signs)) > 1:
            contested.append((key, Counter(signs), len(signs)))
    return pairs, agree, contested


def adjudication_sample(cases, size, seed):
    """Primary cases stratified by readout class, perturbation and split."""
    rnd = random.Random(seed)
    strata = defaultdict(list)
    for c in cases:
        if c["status"] == "primary":
            strata[(c["readout_class"], c["perturbation"], c["split"])].append(c)
    total = sum(len(v) for v in strata.values())
    picked = []
    for key in sorted(strata):
        group = strata[key]
        k = max(1, round(size * len(group) / total)) if total else 0
        picked += rnd.sample(group, min(k, len(group)))
    rnd.shuffle(picked)
    return picked[:size]


# ------------------------------------------------------------------ output


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summary_md(cases, cut, cons, cfg):
    prim = [c for c in cases if c["status"] == "primary"]
    status = Counter(c["status"] for c in cases)
    lines = ["# Perturbation validation set: summary", "",
             f"Context: {cfg.context_name}. Built by `analysis/scripts/build_perturbation_cases.py` from "
             f"`crawler/extractions/`; see `README.md` for the rules.", "",
             f"- candidate cases (a perturbation quote whose readout is pain behaviour or a marker): {len(cases)}",
             f"- primary cases: {len(prim)} from {len({c['pmid'] for c in prim})} papers, "
             f"{len({c['actor_node'] for c in prim})} actors",
             f"- split by PubMed entry order: build {sum(c['split'] == 'build' for c in prim)}, "
             f"test {sum(c['split'] == 'test' for c in prim)} (PMID >= {cut})", "",
             "## Why candidates were excluded", "", "| Status | Cases |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in status.most_common()]
    lines += ["", "## Primary cases by readout", "", "| Readout | Modality | Cases | Papers |", "|---|---|---|---|"]
    by = defaultdict(list)
    for c in prim:
        by[(c["readout"], c["modality"])].append(c)
    for (r, m), cs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {r} | {m or '-'} | {len(cs)} | {len({c['pmid'] for c in cs})} |")
    lines += ["", "## Primary cases by perturbation", "", "| Perturbation | Cases | Readout rose | Readout fell |", "|---|---|---|---|"]
    for p, cs in sorted(defaultdict(list, {k: [c for c in prim if c["perturbation"] == k] for k in {c["perturbation"] for c in prim}}).items()):
        lines.append(f"| {p} | {len(cs)} | {sum(c['observed_change'] == 1 for c in cs)} | {sum(c['observed_change'] == -1 for c in cs)} |")
    sign = Counter(c["implied_sign"] for c in prim)
    lines += ["", "## Implied signs", "",
              f"Raising the actor raises the readout in {sign.get(1, 0)} cases and lowers it in {sign.get(-1, 0)} "
              f"({100 * max(sign.values(), default=0) / max(len(prim), 1):.0f}% share the commoner sign, the majority baseline)."]
    pairs, agree, contested = cons
    lines += ["", "## Do papers agree with each other?", "",
              f"Pairs of papers that studied the same actor and readout: {pairs}; they agree on the sign in {agree} "
              f"({100 * agree / max(pairs, 1):.0f}%). This is a rough ceiling for any model scored on these cases.", ""]
    if contested:
        lines += ["Actor and readout pairs where papers disagree (most-studied first):", ""]
        for (actor, r), cnt, n in sorted(contested, key=lambda x: -x[2])[:15]:
            lines.append(f"- {actor} -> {r}: {n} papers, {cnt.get(1, 0)} say raises, {cnt.get(-1, 0)} say lowers")
    flags = Counter(f for c in prim for f in c["flags"].split(";") if f)
    lines += ["", "## Flags on primary cases", ""] + [f"- {k}: {v}" for k, v in flags.most_common()]
    top = Counter(c["actor_label"] for c in prim).most_common(15)
    lines += ["", "## Most-tested actors", ""] + [f"- {a}: {n}" for a, n in top]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--markers-only", action="store_true")
    args = ap.parse_args(argv)
    cfg = Config()
    sg = gi.SignedGraph(json.loads((ROOT / gi.DEFAULT_GRAPH).read_text()), ROOT / gi.DEFAULT_REVIEW)
    ground = Grounder()
    if args.markers_only:
        cfg.markers = {n: "" for n in sg.nodes}                  # every node may be a readout
        counts = Counter()
        for pmid, rel, node, label, rclass, inv, ctx in candidate_cases(cfg, sg, ground):
            if rclass == "marker" and ctx["models"] and ctx["species"] & cfg.rodent:
                counts[(node, label)] += 1
        for (node, label), n in counts.most_common(40):
            print(f"{n:4d}  {node}  {label}")
        return 0
    cases = [make_case(*c, sg, ground, cfg) for c in candidate_cases(cfg, sg, ground)]
    cases = merge_repeats(cases)
    cut = assign_split(cases, cfg.test_fraction)
    for i, c in enumerate(sorted(cases, key=lambda c: (c["status"] != "primary", int(c["pmid"]), c["actor"])), 1):
        c["case_id"] = f"PC-{i:05d}"
    cases.sort(key=lambda c: c["case_id"])
    cons = consistency(cases)
    write_csv(OUT_DIR / "cases.csv", cases, FIELDS)
    sample = adjudication_sample(cases, cfg.sample_size, cfg.seed)
    review_fields = ["case_id", "pmid", "pubmed", "quote", "actor_label", "perturbation", "readout", "readout_label",
                     "modality", "observed_change", "implied_sign", "models", "species", "flags",
                     "is_perturbation_experiment", "actor_correct", "readout_correct", "direction_correct",
                     "context_correct", "reviewer", "notes"]
    for c in sample:
        c["pubmed"] = f"https://pubmed.ncbi.nlm.nih.gov/{c['pmid']}/"
    write_csv(OUT_DIR / "adjudication_sample.csv", sample, review_fields)
    (OUT_DIR / "summary.md").write_text(summary_md(cases, cut, cons, cfg))
    prim = sum(c["status"] == "primary" for c in cases)
    print(f"{len(cases)} candidate cases, {prim} primary; adjudication sample {len(sample)} -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
