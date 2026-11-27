#!/usr/bin/env python3
"""Build the canonical network for the functional model (scope phase 1).

The canonical network is the part of the knowledge graph an executable model will run on, for one
context (rodent peripheral nerve injury). It is built so that it can be scored on the validation
set (analysis/perturbation/) without leaking it:

  1. Nodes are consolidated: a graph node whose label names one gene becomes that HGNC symbol
     (duplicates such as the three TNF-alpha nodes collapse); every pain-behaviour node becomes
     PAIN (a withdrawal threshold, latency, antinociception or analgesia node flips the sign of its
     links); microglia nodes become MICROGLIA; node_map.yaml holds explicit assignments. Drugs keep
     their own nodes and act through their target links.
  2. Literature links lose every paper of the test era (PMID at or after the validation set's test
     cut). A crawled link left with no paper is dropped. Each link gets an evidence tier: T1 a
     crawled link with a paper in context, T2 a dossier link, T3 a crawled link without one.
     Refuted links, null results and review-wrong links stay out.
  3. Prior knowledge: OmniPath's consensus-signed, directed interactions with enough curation
     (tier P) connect gene nodes. By default they may only join nodes already in the literature
     graph, so the prior fills gaps between known actors and does not import new biology.
  4. Nodes kept: those on a signed path of at most max_path_len links from a validation-set actor
     to its readout. For a build case the case's own paper is left out when this is computed, so
     the network does not contain a case only because of the case.
  5. Every node gets the default combination rule (activators OR, inhibitors AND NOT) unless
     rules.yaml overrides it.

Outputs in analysis/canonical/: network.json and summary.md (coverage of the validation set by
evidence tier, the drugs that lack targets, the largest hubs).

Usage: python3 analysis/scripts/build_canonical.py
"""

import csv
import gzip
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_perturbation_cases as bp  # noqa: E402
import graph_inference as gi  # noqa: E402

CANON = ROOT / "analysis" / "canonical"
CASES = ROOT / "analysis" / "perturbation" / "cases.csv"
GREEK = {"α": "A", "β": "B", "γ": "G", "δ": "D", "κ": "K", "ε": "E", "μ": "M"}
NOT_A_GENE = re.compile(
    r"pathway|signal(?:l)?ing|axis|cascade|inhibitor|antagonist|agonist|si-?rna|sh-?rna|antibod|knock|mimic|"
    r"polymorphism|variant|mutation|-/-|deficien|inhibition|blockade|loop|program|module|network|paradigm|"
    r"rationale|pillar|strategy|therapy|treatment|neuron|interneuron|\bcells?\b|microgli|astrocyt|terminal|"
    r"synap|fiber|fibre|afferent|ganglion|nucleus|cortex|horn|layer|lamina|population|phenotype|polarization|"
    r"\bvs\.?\b|versus|ratio|level|expression|activity|activation|release|secretion|signal\b|"
    # variants, isoforms, modified forms and agents are not the gene itself
    r"\bp\.[A-Z]|\b[A-Z]\d{2,4}[A-Z]\b|\brs\d+|exon|skipping|splic|\bmrna\b|stabili|isoform|truncated|\.t1\b|\bslip\b|"
    r"ubiquitinat|phosphorylation|glycosylat|lactylat|methylat|acetylat|disulfide|thiol|redox|aptamer|chimera|-fc\b|"
    r"sequester|antisense|oligonucleotide|\baso\b|sensiti[sz]|membrane|trafficking|formation|amplification|pore|"
    r"transrepression|\bhub\b|biomarker|nexus|macrophage|monocyte|lymphocyte|nociceptor|\+|biogenesis|"
    r"mitochondrial|ligand|regulat|production|loss-of-function|gain-of-function", re.I)
GENERIC_WORDS = {"RECEPTOR", "RECEPTORS", "CHANNEL", "PROTEIN", "GENE", "CYTOKINE", "KINASE", "TRANSPORTER", "FACTOR",
                 "GTPASE", "ENZYME", "PURINERGIC", "ADAPTOR", "COTRANSPORTER", "TRANSCRIPTION", "SUBUNIT"}
# symbols that collide with common abbreviations of other things (cAMP is not cathelicidin)
AMBIGUOUS_SYMBOLS = {"CAMP", "CO", "NO", "ROS", "PAIN", "ACC", "SET", "MAX", "REST"}
PAIN_HEAD = re.compile(r"\b(?:pain|allodynia|hyperalgesia|hypersensitivity|nociception|pain behaviou?rs?|pain sensation)$", re.I)
# a pain readout measured the other way round: its rise means less pain
INVERTED_HEAD = re.compile(r"\b(?:withdrawal threshold|withdrawal latency|nociceptive threshold|pain threshold|"
                           r"antinociception|analgesia)s?$", re.I)
NOT_PAIN_BEHAVIOUR = re.compile(r"^rationale|^skill|signal|pathway|mechanism|\brole\b|\bvia\b|through|transition|chronific|"
                                r"phase|gate|matrix|paradigm|model|insight|branch|dissection|circuit|strategy|"
                                r"stratification|precision|\bfor\b|therapy|treatment|antagonist|inhibitor|agonist|"
                                # "TREM2 in Neuropathic Pain" is a topic, not a measurement
                                r"\S+\s+in\s+(?:[\w-]+\s+){0,3}(?:pain|allodynia|hyperalgesia|hypersensitivity)$", re.I)
PAIN_IN_ANIMALS = re.compile(r"\b(?:pain|allodynia|hyperalgesia|hypersensitivity)\s+in\s+(?:[\w-]+\s+){0,2}(?:male|female|mice|rats?|animals?)\b", re.I)
LOCATION_PREFIX = re.compile(
    r"^(?:(?:spinal|microglial|astrocytic|astroglial|neuronal|drg|dorsal horn|dorsal root ganglion|acc|hippocampal|"
    r"cortical|peripheral|central|satellite glial|schwann cell|sdh|plasma|serum)\s+)+", re.I)
AGENT_WORD = re.compile(r"\s*\b(antagonists?|inhibitors?|blockers?|agonists?|activators?|zinc finger repressor|repressor)\b\s*", re.I)
AGENT_ROLE = r"(?:inhibitors?|antagonists?|agonists?|blockers?|activators?)"


def names_target_role(quote, target_label, symbol):
    """True when the quote names the target as what the agent acts on ("TRPV1 antagonist",
    "inhibitor of TRPV1"): a statement of the drug's target, not of a downstream outcome."""
    names = {symbol} if symbol else set()
    head = target_label.split("(")[0].strip()
    names |= {head} | set(re.findall(r"\(([^)]*)\)", target_label))
    for name in filter(None, (n.strip() for n in names)):
        tok = re.escape(name)
        if re.search(rf"\b{tok}\b[\w\s()/-]{{0,25}}?\b{AGENT_ROLE}\b", quote, re.I) or \
                re.search(rf"\b{AGENT_ROLE}\s+(?:of\s+)?(?:the\s+)?{tok}\b", quote, re.I):
            return True
    return False
MICROGLIA_LABEL = re.compile(r"^(?:spinal |activated |m1 |reactive )?microglia(?:l activation)?\b|^microglial (?:activation|reactivity)", re.I)


def norm_token(t):
    return re.sub(r"[^A-Z0-9]", "", "".join(GREEK.get(c, c) for c in t).upper())


class Mapper:
    """Graph node id -> (canonical id, inverted?)."""

    def __init__(self, graph, sg, pcfg, symbols, node_map):
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        self.sg, self.pcfg = sg, pcfg
        self.sym_up = {s.upper(): s for s in symbols}
        self.explicit = node_map.get("map") or {}
        self.unmapped = set(node_map.get("unmapped") or [])
        # context-specific nodes (crawler/context_nodes.yaml, e.g. the Kalirin-7 splits) are never merged
        ctx = yaml.safe_load((ROOT / "crawler" / "context_nodes.yaml").read_text()) or {}
        self.context_nodes = {e["id"] if isinstance(e, dict) else e for e in ctx.get("context_nodes", [])}
        syn = {norm_token(k): v for k, v in (node_map.get("synonyms") or {}).items()}
        aliases = yaml.safe_load((ROOT / "crawler" / "aliases.yaml").read_text()) or {}
        for sym, names in aliases.items():
            if str(sym).upper() in self.sym_up:
                for n in (names if isinstance(names, list) else [names]):
                    syn.setdefault(norm_token(str(n)), self.sym_up[str(sym).upper()])
        self.syn = syn
        self.memo = {}

    def resolve(self, token):
        n = norm_token(token)
        if len(n) < 2 or n in AMBIGUOUS_SYMBOLS:
            return None
        return self.sym_up.get(n) or self.syn.get(n)

    def symbol(self, label):
        """The one gene a label names, or None. The head (before any bracket) must have at most two
        content words and name exactly one gene; a bracket counts only when it holds a single token
        ("Tumor Necrosis Factor Alpha (TNF-α)"); a slash means several things ("TLR2/4")."""
        head = label.split("(")[0].strip()
        if "/" in head:
            return None
        words = [w for w in re.split(r"[\s,;:]+", head) if w]
        content = [w for w in words if norm_token(w) not in GENERIC_WORDS]
        whole = self.resolve(head)                          # a full name: "Tumor Necrosis Factor Alpha"
        if whole:
            return whole
        found = {s for t in words if (s := self.resolve(t))}
        if len(found) == 1 and len(content) <= 2:
            return found.pop()
        if found:
            return None
        for inner in re.findall(r"\(([^)]*)\)", label):
            if len(inner.split()) == 1 and "/" not in inner and (s := self.resolve(inner)):
                return s
        return None

    def pain_readout(self, label):
        """(is a pain-behaviour node, measured inverted): the name must end in a pain word (or a
        threshold, latency or analgesia measure), be short, and not be an argument or a mechanism."""
        head = label.split("(")[0].strip()
        if NOT_PAIN_BEHAVIOUR.search(head) or self.pcfg.not_pain_label.search(head) or len(head.split()) > 8:
            return False, False
        if INVERTED_HEAD.search(head):
            return True, True
        return PAIN_HEAD.search(head) is not None or PAIN_IN_ANIMALS.search(head) is not None, False

    def __call__(self, nid):
        if nid in self.memo:
            return self.memo[nid]
        node = self.nodes.get(nid, {"label": nid})
        label = LOCATION_PREFIX.sub("", node.get("label", nid)) or node.get("label", nid)
        is_pain, inverted = self.pain_readout(label)
        if nid in self.explicit:
            out = (self.explicit[nid], False)
        elif nid in self.context_nodes:
            out = (nid, False)
        elif is_pain:
            out = ("PAIN", inverted)
        elif MICROGLIA_LABEL.search(label):
            out = ("MICROGLIA", False)
        elif nid in self.unmapped or nid in self.sg.drugs or NOT_A_GENE.search(label):
            out = (nid, False)
        else:
            out = (self.symbol(label) or nid, False)
        self.memo[nid] = out
        return out


def read_cases(path=CASES):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["status"] == "primary"]
    test = [int(r["pmid"]) for r in rows if r["split"] == "test"]
    return rows, (min(test) if test else 10 ** 12)


def literature_edges(graph, mapper, cutoff, in_context, review_path=gi.DEFAULT_REVIEW):
    """(canonical source, target, sign) -> evidence: papers (pmid -> in context?), tiers, graph links."""
    wrong = gi.load_wrong_links(review_path)
    edges = defaultdict(lambda: {"papers": {}, "tiers": set(), "curated": False, "verdicts": set(), "links": 0,
                                 "quotes_flag": False, "target_annotation": False})
    dropped = Counter()
    for link in graph["links"]:
        sign = link.get("sign", 0)
        if sign == 0:
            continue
        if link.get("validation_status") == "REFUTED":
            dropped["refuted"] += 1
            continue
        crawled = gi.is_crawled_link(link)
        if crawled and ((str(link.get("source_pmid")), link.get("quote")) in wrong or gi.NULL_WORDING.search(link.get("quote", ""))):
            dropped["review wrong or null result"] += 1
            continue
        papers = {str(e.get("pmid")) for e in link.get("crawler_evidence", [])}
        if crawled:
            papers.add(str(link.get("source_pmid")))
        papers = {p for p in papers if p.isdigit() and int(p) < cutoff}
        if crawled and not papers:
            dropped["only test-era papers"] += 1
            continue
        (s, inv_s), (t, inv_t) = mapper(link["source"]), mapper(link["target"])
        sign = sign * (-1 if inv_s else 1) * (-1 if inv_t else 1)
        if s == t:
            dropped["self-loop after merging"] += 1
            continue
        e = edges[(s, t, sign)]
        if link["source"] in mapper.sg.drugs and names_target_role(
                link.get("quote") or "", mapper.nodes.get(link["target"], {}).get("label", ""), t if t in mapper.sym_up.values() else None):
            e["quotes_flag"] = True
        ctx = {p: in_context(p) for p in papers}
        e["papers"].update(ctx)
        e["links"] += 1
        if crawled:
            e["tiers"].add("T1" if any(ctx.values()) else "T3")
        else:
            e["tiers"].add("T2")
            e["curated"] = True
            if link.get("validation_status"):
                e["verdicts"].add(link["validation_status"])
    return edges, dropped


def prior_edges(path, min_effort):
    out = {}
    with gzip.open(path, "rt") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if int(r["curation_effort"] or 0) >= min_effort and r["source_genesymbol"] != r["target_genesymbol"]:
                out[(r["source_genesymbol"], r["target_genesymbol"], int(r["sign"]))] = {
                    "sources": r["sources"], "curation_effort": int(r["curation_effort"] or 0)}
    return out


class Network:
    """Literature and prior edges with per-case filtering."""

    def __init__(self, lit, prior, tiers, allow_prior_only):
        self.lit = {k: v for k, v in lit.items() if v["tiers"] & tiers}
        lit_nodes = {x for (s, t, _) in self.lit for x in (s, t)}
        self.prior = {k: v for k, v in prior.items()
                      if "P" in tiers and (allow_prior_only or (k[0] in lit_nodes and k[1] in lit_nodes))}
        self.out, self.inn = defaultdict(list), defaultdict(list)
        for (s, t, sign), ev in self.lit.items():
            self.out[s].append((t, sign, ev))
            self.inn[t].append((s, sign, ev))
        for (s, t, sign), ev in self.prior.items():
            self.out[s].append((t, sign, None))
            self.inn[t].append((s, sign, None))

    @staticmethod
    def usable(ev, pmid):
        """A link the case can use: prior, dossier, or with a paper other than the case's own."""
        return ev is None or ev["curated"] or ev.get("target_annotation") or any(p != pmid for p in ev["papers"])

    def dist(self, start, pmid, max_len, forward=True):
        adj = self.out if forward else self.inn
        d, q = {start: 0}, deque([start])
        while q:
            u = q.popleft()
            if d[u] == max_len:
                continue
            for v, _, ev in adj.get(u, ()):
                if v not in d and self.usable(ev, pmid):
                    d[v] = d[u] + 1
                    q.append(v)
        return d


def build(cfg, graph, pcfg, node_map, cases, cutoff):
    sg = gi.SignedGraph(graph)
    prior = prior_edges(ROOT / cfg["prior"]["path"], cfg["prior"]["min_curation_effort"])
    symbols = {x for (s, t, _) in prior for x in (s, t)}
    with gzip.open(ROOT / cfg["prior"]["path"], "rt") as fh:            # every symbol, not only the curated ones
        symbols |= {x for r in csv.DictReader(fh, delimiter="\t") for x in (r["source_genesymbol"], r["target_genesymbol"])}
    mapper = Mapper(graph, sg, pcfg, symbols, node_map)
    contexts = {}

    def in_context(pmid):
        if pmid not in contexts:
            c = bp.paper_context(pmid, pcfg)
            contexts[pmid] = bool(c["models"]) and bool(c["species"] & pcfg.rodent)
        return contexts[pmid]

    lit, dropped = literature_edges(graph, mapper, cutoff, in_context)
    # a drug's link to its target defines the perturbation: usable even when its paper is the case's
    drug_nodes = {mapper(n)[0] for n in sg.drugs}
    for (s, t, sign), ev in lit.items():
        if s in drug_nodes and t != "PAIN" and ev["quotes_flag"]:
            ev["target_annotation"] = True
    curated_targets = yaml.safe_load((CANON / "drug_targets.yaml").read_text()) or {}
    for nid in sg.drugs:
        s = mapper(nid)[0]
        targets = []
        for entry in curated_targets.get(nid, []):
            targets.append((entry["target"], int(entry["sign"]), "D"))
        label = mapper.nodes.get(nid, {}).get("label", "")
        m = AGENT_WORD.search(label.split("(")[0])
        if m and not targets:
            core = AGENT_WORD.sub(" ", label.split("(")[0]).strip()
            sym = mapper.symbol(core)
            if sym:
                word = m.group(1).lower()
                targets.append((sym, 1 if word.startswith(("agonist", "activator")) else -1, "L"))
        for target, sign, tier in targets:
            t = target if target in mapper.sym_up.values() or target not in mapper.nodes else mapper(target)[0]
            e = lit[(s, t, sign)]
            e["tiers"].add(tier)
            e["curated"] = True
            e["target_annotation"] = True
    L = cfg["network"]["max_path_len"]
    allow = cfg["network"]["allow_prior_only_nodes"]
    for c in cases:
        c["actor_canon"] = mapper(c["actor_node"])[0]
        c["readout_canon"] = "PAIN" if c["readout_class"] == "pain" else mapper(c["readout_node"])[0]

    def coverage(tiers):
        net = Network(lit, prior, tiers, allow)
        covered, nodes = [], set()
        for c in cases:
            a, r, pm = c["actor_canon"], c["readout_canon"], c["pmid"]
            fwd = net.dist(a, pm, L, True)
            if r not in fwd:
                continue
            bwd = net.dist(r, pm, L, False)
            covered.append(c)
            nodes |= {v for v, dv in fwd.items() if dv + bwd.get(v, 99) <= L}
        return net, covered, nodes

    modes = [("T1", {"T1", "D", "L"}), ("T1+T2", {"T1", "T2", "D", "L"}), ("T1+T2+T3", {"T1", "T2", "T3", "D", "L"}),
             ("T1+T2+T3+P", {"T1", "T2", "T3", "P", "D", "L"})]
    results = {name: coverage(tiers) for name, tiers in modes}
    net, covered, nodes = results["T1+T2+T3+P"]
    nodes |= set(cfg["readouts"])
    labels = defaultdict(list)
    for nid in mapper.nodes:
        labels[mapper(nid)[0]].append(nid)
    readouts = set(cfg["readouts"])
    actors = {c["actor_canon"] for c in cases}
    node_rows = []
    for n in sorted(nodes):
        members = labels.get(n, [])
        node_rows.append({
            "id": n, "label": cfg["readouts"].get(n) or (mapper.nodes[members[0]]["label"] if members else n),
            "kind": "readout" if n in readouts else "drug" if any(m in sg.drugs for m in members) else
                    "gene" if n in symbols else "literature node",
            "members": members, "validation_actor": n in actors,
        })
    link_rows = []
    for (s, t, sign), ev in sorted(net.lit.items()):
        if s in nodes and t in nodes:
            link_rows.append({"source": s, "target": t, "sign": sign, "tiers": sorted(ev["tiers"]),
                              "papers": sorted(ev["papers"]), "papers_in_context": sorted(p for p, c in ev["papers"].items() if c),
                              "curated": ev["curated"], "verdicts": sorted(ev["verdicts"]), "graph_links": ev["links"],
                              "target_annotation": bool(ev.get("target_annotation"))})
    for (s, t, sign), ev in sorted(net.prior.items()):
        if s in nodes and t in nodes:
            link_rows.append({"source": s, "target": t, "sign": sign, "tiers": ["P"], "prior_sources": ev["sources"],
                              "curation_effort": ev["curation_effort"]})
    rules = yaml.safe_load((CANON / "rules.yaml").read_text()) or {}
    network = {
        "meta": {"context": "rodent peripheral nerve injury", "test_cutoff_pmid": cutoff, "max_path_len": L,
                 "allow_prior_only_nodes": allow, "prior": cfg["prior"], "default_rule": cfg["default_rule"],
                 "dropped_links": dict(dropped)},
        "nodes": node_rows, "links": link_rows,
        "rules": {n["id"]: rules.get(n["id"], {"rule": "default"}) for n in node_rows},
    }
    return network, results, cases, mapper, sg


def summary(network, results, cases, sg):
    lines = ["# Canonical network: summary", "",
             "Built by `analysis/scripts/build_canonical.py`; rules in `analysis/canonical/config.yaml`, "
             "explicit node assignments in `node_map.yaml`. See `README.md`.", "",
             f"- nodes: {len(network['nodes'])} ({Counter(n['kind'] for n in network['nodes']).most_common()})",
             f"- links: {len(network['links'])} ({Counter(','.join(l['tiers']) for l in network['links']).most_common(6)})",
             f"- test-era cut: papers with PMID >= {network['meta']['test_cutoff_pmid']} are left out",
             f"- links left out: {network['meta']['dropped_links']}", "",
             "## Coverage of the validation set", "",
             "A case is covered when a signed path of at most "
             f"{network['meta']['max_path_len']} links joins its actor to its readout without the case's own paper.", "",
             "| Evidence used | Build cases covered | Test cases covered | Nodes on those paths |", "|---|---|---|---|"]
    nb = sum(c["split"] == "build" for c in cases)
    nt = sum(c["split"] == "test" for c in cases)
    for name, (net, covered, nodes) in results.items():
        cb = sum(c["split"] == "build" for c in covered)
        ct = sum(c["split"] == "test" for c in covered)
        lines.append(f"| {name} | {cb} of {nb} ({100 * cb / max(nb, 1):.0f}%) | {ct} of {nt} ({100 * ct / max(nt, 1):.0f}%) | {len(nodes)} |")
    net, covered, _ = results["T1+T2+T3+P"]
    cov_ids = {id(c) for c in covered}
    missing = [c for c in cases if id(c) not in cov_ids]
    known = {x for (s, t, _) in list(net.lit) + list(net.prior) for x in (s, t)}
    reasons = Counter()
    drug_gap = Counter()
    for c in missing:
        a = c["actor_canon"]
        if a not in known:
            reasons["actor has no link besides its own paper"] += 1
        elif not any(net.usable(ev, c["pmid"]) for _, _, ev in net.out.get(a, ())):
            reasons["actor has no outgoing link besides its own paper"] += 1
        else:
            reasons[f"no path within {network['meta']['max_path_len']} links"] += 1
        if c["perturbation"] == "drug":
            drug_gap[c["actor_label"]] += 1
    lines += ["", "## Cases still not covered (all tiers)", ""] + [f"- {k}: {v}" for k, v in reasons.most_common()]
    lines += ["", f"Drug cases not covered: {sum(drug_gap.values())} ({len(drug_gap)} drugs). Most need their targets: "
              "a compound named only in the paper that tests it has no other link. Examples: "
              + ", ".join(f"{d}" for d, _ in drug_gap.most_common(12)) + "."]
    by_kind = Counter((c["perturbation"] == "drug", id(c) in cov_ids) for c in cases)
    lines += ["", "## Covered cases by kind", "",
              f"- knockdown or overexpression: {by_kind[(False, True)]} of {by_kind[(False, True)] + by_kind[(False, False)]}",
              f"- drug: {by_kind[(True, True)]} of {by_kind[(True, True)] + by_kind[(True, False)]}"]
    deg = Counter()
    for l in network["links"]:
        deg[l["source"]] += 1
        deg[l["target"]] += 1
    lines += ["", "## Largest hubs in the canonical network", ""] + [f"- {n}: {d} links" for n, d in deg.most_common(12)]
    return "\n".join(lines) + "\n"


def main(argv=None):
    cfg = yaml.safe_load((CANON / "config.yaml").read_text())
    node_map = yaml.safe_load((CANON / "node_map.yaml").read_text()) or {}
    graph = json.loads((ROOT / gi.DEFAULT_GRAPH).read_text())
    cases, cutoff = read_cases()
    network, results, cases, mapper, sg = build(cfg, graph, bp.Config(), node_map, cases, cutoff)
    (CANON / "network.json").write_text(json.dumps(network, indent=1, ensure_ascii=False) + "\n")
    (CANON / "summary.md").write_text(summary(network, results, cases, sg))
    # the cases phase 3 can score: covered with every tier
    covered = {id(c) for c in results["T1+T2+T3+P"][1]}
    tiers_needed = {}
    for name in ("T1", "T1+T2", "T1+T2+T3", "T1+T2+T3+P"):
        for c in results[name][1]:
            tiers_needed.setdefault(id(c), name)
    fields = ["case_id", "split", "pmid", "perturbation", "actor_canon", "readout_canon", "implied_sign",
              "observed_change", "modality", "flags", "covered_with"]
    with open(CANON / "scorable_cases.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for c in cases:
            if id(c) in covered:
                w.writerow({**c, "covered_with": tiers_needed[id(c)]})
    print(f"{len(network['nodes'])} nodes, {len(network['links'])} links -> {CANON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
