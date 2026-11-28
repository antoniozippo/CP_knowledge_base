#!/usr/bin/env python3
"""Score the functional model on published combination experiments (scope phase 4).

Input: crawler/extractions/combinations/*.json (the combinations pass). Each record has two or more
interventions given together, one readout, the readout's direction under the combination and under
each intervention alone (`singles`) and an interaction class.

  1. keep in-vivo, non-human records from rodent nerve-injury papers (analysis/perturbation context),
  2. ground the first two interventions to HGNC symbols (analysis/combinations/grounding.yaml, then the
     canonical Mapper) and the readout to PAIN (threshold and latency readouts inverted) or a node,
  3. build a network that contains these actors and readouts (build_canonical.build, with the records
     as pseudo-cases; the canonical network itself is not touched),
  4. predict, with leave-one-paper-out links, the readout's change under A alone, B alone and A+B
     (a loss clamps the actor to 0, a gain or drug to 1), by the Netflux setting of phase 3, by static
     signed paths (additive by construction) and by the actor's usual sign,
  5. score (a) single-intervention directions, (b) the combination's direction where it moved, and
     (c) the interaction class: less than additive (occlusion, antagonism, no added effect,
     sub-additive), additive, synergy. Static paths are additive, so they can only ever say "additive".

Outputs in analysis/combinations/: cases.csv, results.md. Usage: python3 analysis/scripts/evaluate_combinations.py
"""

import csv
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_canonical as bc  # noqa: E402
import build_perturbation_cases as bp  # noqa: E402
import functional_model as fm  # noqa: E402
import graph_inference as gi  # noqa: E402
from evaluate_functional_model import TIER_SETS, WEIGHTS, fmt, wilson  # noqa: E402

OUT = ROOT / "analysis" / "combinations"
SOURCE = ROOT / "crawler" / "extractions" / "combinations"
STRIP = re.compile(r"(?:[- ]?/[-−]|\bknock(?:out|down)\b|\bsi-?rna\b|\bsh-?rna\b|\binhibitors?\b|\bantagonists?\b|\bagonists?\b|"
                   r"\bantibody\b|\bantisense\b|\bc?KO\b|\bmice\b|\bwt\b|\bdeficient\b|\boverexpression\b|\bAAV\w*\b|\brecombinant\b)", re.I)
LOSS_WORDS = re.compile(r"si-?rna|sh-?rna|knock|-/-|inhibitor|antagonist|blocker|antibody|antisense|deficien|\bc?KO\b", re.I)
THRESHOLD = re.compile(r"threshold|latency|\bPW[TL]\b|withdrawal (?:time|duration)|tail.?flick|hot.?plate", re.I)
LESS = {"occlusion", "antagonism", "no_added_effect", "sub_additive"}
EPS = 1e-4


def classes_of(interaction):
    return "less than additive" if interaction in LESS else "synergy" if interaction == "synergy" else "additive" if interaction == "additive" else None


class Grounder:
    def __init__(self, mapper):
        g = yaml.safe_load((OUT / "grounding.yaml").read_text())
        self.targets = [(re.compile(k, re.I), v) for k, v in g["targets"].items()]
        self.agents = [(re.compile(k, re.I), v) for k, v in g["agents"].items()]
        self.mapper = mapper

    def intervention(self, iv):
        """(symbol, 'loss'|'gain') or None."""
        agent, target = (iv.get("agent") or "").strip(), (iv.get("target") or "").strip()
        action = iv.get("action") or "unspecified"
        loss = action == "loss" or (action in ("drug", "unspecified") and bool(LOSS_WORDS.search(agent)))
        for text in (target, agent):
            for rx, v in (self.targets if text is target else self.agents):
                if rx.search(text):
                    if isinstance(v, dict):
                        return v["symbol"], v["action"]
                    return v, "loss" if loss else "gain"
        for text in (target, agent):
            core = STRIP.sub(" ", text).strip(" -+()")
            sym = core and self.mapper.symbol(core)
            if sym:
                return sym, "loss" if loss else "gain"
        return None

    def readout(self, label):
        """(node, inverted) or None."""
        is_pain, inverted = self.mapper.pain_readout(label)
        if is_pain or re.search(r"allodynia|hyperalgesia|nociceptive|pain|hypersensitivity", label, re.I):
            return "PAIN", inverted or bool(THRESHOLD.search(label))
        if THRESHOLD.search(label):                      # "paw withdrawal mechanical threshold"
            return "PAIN", True
        if re.search(r"microgl", label, re.I):
            return "MICROGLIA", False
        sym = self.mapper.symbol(label)
        return (sym, False) if sym else None


def load_records():
    out = []
    for f in sorted(SOURCE.glob("*.json")):
        d = json.loads(f.read_text())
        for i, c in enumerate(d.get("combinations") or []):
            out.append({**c, "pmid": d["pmid"], "rec": f"{d['pmid']}-{i}"})
    return out


def sgn(x):
    return fm.sign_of(x, EPS)


def predict(network, nodes, exo, links_cache, pmid, cfg, a, b, readout):
    """Effects of A, B and A+B on the readout under the Netflux setting, and the static additive sum."""
    links = links_cache.get(pmid)
    if links is None:
        links = links_cache[pmid] = fm.select_links(network, pmid, TIER_SETS[cfg["tiers"]], WEIGHTS[cfg["weights"]])
    nf = fm.NetfluxModel(nodes, links, exo, basal=cfg["basal"], n=cfg["n"], ec50=cfg["ec50"], logic=cfg["logic"])
    base = nf.steady_state()
    r = nf.index[readout]
    clamp = lambda items: {sym: (0.0 if act == "loss" else 1.0) for sym, act in items}
    e = {}
    for name, items in (("a", [a]), ("b", [b]), ("ab", [a, b])):
        e[name] = float(nf.steady_state(clamp(items))[r] - base[r])
    d = lambda act: -1 if act == "loss" else 1
    st = {k: fm.static_effect(links, s, readout, avoid=exo - {s}) * d(act) for k, (s, act) in (("a", a), ("b", b))}
    src = {k: fm.sign_of(fm.source_tendency(links, s)) * d(act) for k, (s, act) in (("a", a), ("b", b))}
    alt = {}
    for name, extra in VARIANTS.items():
        m = fm.NetfluxModel(nodes, links, exo, **{**{k: cfg[k] for k in ("basal", "n", "ec50", "logic")}, **extra})
        b0 = m.steady_state()
        ev = {k: float(m.steady_state(clamp(it))[r] - b0[r]) for k, it in (("a", [a]), ("b", [b]), ("ab", [a, b]))}
        alt[name] = interaction_class(ev)
    alt["mediation"] = mediation_class(links, a[0], b[0])
    return e, st, src, alt


VARIANTS = {"mean": {}, "or": {"logic": "or"}, "or-scaled": {"logic": "or-scaled"}}


def reaches(links, source, target, max_len=3):
    """Is there a directed path of at most max_len links from source to target?"""
    out = {}
    for s_, t, _, _ in links:
        out.setdefault(s_, []).append(t)
    frontier, seen = {source}, {source}
    for _ in range(max_len):
        frontier = {t for n in frontier for t in out.get(n, ()) if t not in seen}
        if target in frontier:
            return True
        seen |= frontier
    return False


def mediation_class(links, a, b):
    """Structural rule: when one intervention sits upstream of the other, the second can carry (or
    cancel) the first's effect, so the pair is less than additive; independent actors add."""
    return "less than additive" if reaches(links, a, b) or reaches(links, b, a) else "additive"


def interaction_class(e):
    s = e["a"] + e["b"]
    if abs(e["ab"]) < EPS and abs(s) < EPS:
        return None
    if abs(s) < EPS:
        return "synergy"
    r = e["ab"] / s
    return "synergy" if r > 1.25 else "additive" if r >= 0.75 else "less than additive"


def main():
    cfg = yaml.safe_load((ROOT / "analysis/canonical/config.yaml").read_text())
    model = yaml.safe_load((ROOT / "analysis/functional/model.yaml").read_text())
    node_map = yaml.safe_load((ROOT / "analysis/canonical/node_map.yaml").read_text()) or {}
    graph = json.loads((ROOT / gi.DEFAULT_GRAPH).read_text())
    pcfg = bp.Config()
    sg = gi.SignedGraph(graph)
    symbols = set()
    with gzip.open(ROOT / cfg["prior"]["path"], "rt") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            symbols |= {r["source_genesymbol"], r["target_genesymbol"]}
    mapper = bc.Mapper(graph, sg, pcfg, symbols, node_map)
    grounder = Grounder(mapper)
    ctx = {}

    def in_context(pmid):
        if pmid not in ctx:
            c = bp.paper_context(pmid, pcfg)
            ctx[pmid] = bool(c["models"]) and bool(c["species"] & pcfg.rodent)
        return ctx[pmid]

    records = load_records()
    funnel = Counter(total=len(records))
    cases = []
    for rec in records:
        text = " ".join([rec.get("model", ""), rec["readout"], rec["evidence_quote"]])
        if pcfg.in_vitro.search(text) or (rec.get("species") or "").lower().startswith("human") or not in_context(rec["pmid"]):
            continue
        funnel["in vivo, rodent nerve injury"] += 1
        ivs = [grounder.intervention(i) for i in rec["interventions"][:2]]
        ro = grounder.readout(rec["readout"])
        if len(rec["interventions"]) < 2 or not all(ivs) or not ro:
            continue
        funnel["interventions and readout grounded"] += 1
        (a, b), (readout, inverted) = ivs, ro
        if a[0] == b[0]:
            funnel["same node twice (not testable)"] += 1
            continue
        cases.append({"rec": rec, "a": a, "b": b, "readout": readout, "inverted": inverted})
    funnel["distinct-node pairs"] = len(cases)

    pseudo = []
    for c in cases:
        for sym, act in (c["a"], c["b"]):
            pseudo.append({"actor_node": sym, "readout_class": "pain" if c["readout"] == "PAIN" else "marker",
                           "readout_node": c["readout"], "pmid": c["rec"]["pmid"], "perturbation": act})
    base_cases, cutoff = bc.read_cases()
    network, _, _, _, _ = bc.build(cfg, graph, pcfg, node_map, base_cases + pseudo, cutoff)
    # an actor or readout with no path to the other within three links is not on the network's paths;
    # it is added as an isolated node, so the model's answer for it is "no change", which scores as wrong
    present = {n["id"] for n in network["nodes"]}
    for c in cases:
        for sym in (c["a"][0], c["b"][0], c["readout"]):
            if sym not in present:
                network["nodes"].append({"id": sym, "label": sym, "kind": "gene", "members": [], "validation_actor": False})
                present.add(sym)
    nodes = [n["id"] for n in network["nodes"]]
    nodeset = set(nodes)
    exo = fm.exogenous_nodes(network)
    cache = {}
    rows = []
    for c in cases:
        rec = c["rec"]
        (sa, aa), (sb, ab_), ro = c["a"], c["b"], c["readout"]
        if not {sa, sb, ro} <= nodeset:
            continue
        e, st, src, alt = predict(network, nodes, exo, cache, rec["pmid"], model, c["a"], c["b"], ro)
        flip = -1 if c["inverted"] else 1
        singles = rec.get("singles") or []
        row = {"rec": rec["rec"], "pmid": rec["pmid"], "a": f"{aa} {sa}", "b": f"{ab_} {sb}", "readout": ro,
               "readout_label": rec["readout"], "inverted": int(c["inverted"]), "interaction": rec.get("interaction"),
               "basis": rec.get("interaction_basis"), "class": classes_of(rec.get("interaction")),
               "obs_a": flip * singles[0] if len(singles) > 0 else 0, "obs_b": flip * singles[1] if len(singles) > 1 else 0,
               "obs_ab": flip * int(rec.get("readout_direction") or 0),
               "net_a": sgn(e["a"]), "net_b": sgn(e["b"]), "net_ab": sgn(e["ab"]),
               "static_a": sgn(st["a"]), "static_b": sgn(st["b"]), "static_ab": sgn(st["a"] + st["b"]),
               "source_a": src["a"], "source_b": src["b"], "source_ab": src["a"] + src["b"] and (1 if src["a"] + src["b"] > 0 else -1),
               "net_class": interaction_class(e), **{f"class_{k}": v for k, v in alt.items()}, "static_class": "additive", "e_a": round(e["a"], 5),
               "e_b": round(e["b"], 5), "e_ab": round(e["ab"], 5), "quote": rec["evidence_quote"]}
        rows.append(row)
    funnel["scored (isolated nodes included; no path means no call)"] = len(rows)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "cases.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["rec"])
        w.writeheader()
        w.writerows(rows)

    L = ["# Functional model on combination experiments: results (scope phase 4)", "",
         "Built by `analysis/scripts/evaluate_combinations.py` from `crawler/extractions/combinations/`. Links are "
         "leave-one-paper-out; the model is the Netflux setting chosen in phase 3 (`analysis/functional/model.yaml`). "
         "Interaction labels are the extracting session's judgement (stated in the paper for most, inferred for the rest); "
         "none has been checked by an expert.", "", "## Funnel", ""]
    L += [f"- {k}: {v}" for k, v in funnel.items()]

    def acc(method, key_obs, keys):
        k = n = none = 0
        for r in rows:
            for key in keys:
                o = r[f"obs_{key}"]
                if o == 0:
                    continue
                n += 1
                p = r[f"{method}_{key}"]
                k += p == o
                none += p == 0
        return k, n, none

    L += ["", "## Direction of the readout", "",
          "Observed direction is the paper's, expressed as pain (threshold readouts flipped). A prediction of no change "
          "counts as wrong. `source` is the actor's usual sign.", "",
          "| Method | One intervention alone | The combination (where the readout moved) |", "|---|---|---|"]
    for m in ("net", "static", "source"):
        L.append(f"| {m} | {fmt(*acc(m, None, ('a', 'b')))} | {fmt(*acc(m, None, ('ab',)))} |")
    majority = Counter(r[f"obs_{k}"] for r in rows for k in ("a", "b", "ab") if r[f"obs_{k}"]).most_common(1)
    if majority:
        sgn_m = majority[0][0]
        for label, keys in (("one alone", ("a", "b")), ("combination", ("ab",))):
            vals = [r[f"obs_{k}"] for r in rows for k in keys if r[f"obs_{k}"]]
            L.append(f"\nMajority direction ({sgn_m:+d}) would be right on {sum(v == sgn_m for v in vals)}/{len(vals)} ({label}).")

    classed = [r for r in rows if r["class"]]
    dist = Counter(r["class"] for r in classed)
    L += ["", "## Interaction class", "",
          f"{len(classed)} cases have a class. Observed: " + ", ".join(f"{k} {v}" for k, v in dist.most_common()) + ".", "",
          "| Method | Right | Calls |", "|---|---|---|"]
    for name, key in (("netflux", "net_class"), ("static paths (always additive)", "static_class")):
        called = [r for r in classed if r[key]]
        L.append(f"| {name} | {fmt(sum(r[key] == r['class'] for r in classed), len(classed))} | made a call on {len(called)} |")
    top = dist.most_common(1)[0] if dist else (None, 0)
    if top[0]:
        L.append(f"| always \"{top[0]}\" (majority) | {fmt(top[1], len(classed))} | all |")
    both = [r for r in classed if r["net_class"]]
    L += ["", "Where netflux made a call: " + (", ".join(f"{k} {v}" for k, v in Counter((r['net_class'], r['class']) for r in both).most_common()) or "none") +
          " (predicted, observed).", ""]
    L += ["", "### Other combination rules and a structural rule", "",
          "`or`: activators OR-ed (saturates); `or-scaled`: OR with inputs scaled by their number; `mediation`: less than "
          "additive when one intervention reaches the other within three links, else additive. Declared before scoring; "
          "no rule was selected on these cases.", "", "| Rule | Right | Calls | Per class (right/observed) |", "|---|---|---|---|"]
    for key in ("class_mean", "class_or", "class_or-scaled", "class_mediation"):
        called = [r for r in classed if r[key]]
        per = ", ".join(f"{c} {sum(r[key] == c for r in classed if r['class'] == c)}/{n}" for c, n in dist.most_common())
        L.append(f"| {key[6:]} | {fmt(sum(r[key] == r['class'] for r in classed), len(classed))} | {len(called)} | {per} |")
    related = [r for r in classed if r["class_mediation"] == "less than additive"]
    L.append(f"\nMediation: {len(related)} of {len(classed)} classed pairs have one intervention upstream of the other.")
    stated = [r for r in classed if r["basis"] == "stated"]
    L.append(f"On the {len(stated)} cases whose interaction the paper states: netflux right on "
             f"{sum(r['net_class'] == r['class'] for r in stated)}, majority right on {sum(r['class'] == top[0] for r in stated)}.")
    (OUT / "results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
