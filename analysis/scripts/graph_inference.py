#!/usr/bin/env python3
"""Signed-path inference over graphify-out/graph_v2.json.

Reads the graph as a signed, weighted, directed causal network (source --sign--> target:
the source raises (+1) or lowers (-1) the target) and answers five questions:

 1. Drug effects: for every drug, the net signed effect on the pain nodes through paths of
    up to MAX_LEN links. A path's sign is the product of its signs, its weight the product of
    its link weights. Drugs with a net analgesic prediction and no direct drug -> pain link are
    reported as novel candidates.
 2. Targets: for every non-drug node, how strongly it drives or suppresses pain, and whether
    any drug in the graph already inhibits it (a "druggable gap" when none does).
 3. Chokepoints: nodes lying on the most pain-promoting paths from nerve-injury models.
 4. Feedback loops: simple cycles up to CYCLE_LEN inside the signed graph. An even number of
    negative links makes a loop self-amplifying.
 5. Calibration: how well does composing signs along paths reproduce known links? Direct
    links are predicted from their two-hop paths, and each drug's direct pain link is predicted
    from paths with that link removed. These two numbers say how far to trust 1-4.

Link weights (0-1): curated links by validation status; crawled links by supporting papers,
lower when the quote is hedged. Excluded: REFUTED links, links the 2026-11 review marked
WRONG (crawler/review/), crawled links whose quote reports a null result.

Everything is deterministic. Usage:
  python3 analysis/scripts/graph_inference.py [--graph PATH] [--review PATH]
         [--json OUT.json] [--markdown OUT.md]
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

DEFAULT_GRAPH = Path("graphify-out/graph_v2.json")
DEFAULT_REVIEW = Path("crawler/review/curated_links_review_2026-11.csv")
MAX_LEN = 4          # links per drug -> pain path
TARGET_LEN = 3       # links per target -> pain path
CHOKE_LEN = 5        # links per injury -> pain path
CYCLE_LEN = 5
PATH_DECAY = 0.7     # a path of n links counts PATH_DECAY ** (n - 1)

PAIN_LABELS = ("allodynia", "hyperalgesia", "pain")
AFFECT_LABELS = ("anxiety", "aversi", "depress", "fear", "affective")
EXCLUDED_LABEL = re.compile(r"^rationale:|\bantibody\b|\bmab\b|antagonist|inhibitor|blocker", re.I)
INJURY_LABEL = re.compile(
    r"nerve injury|constriction injury|\bcci\b|spared nerve|\bsni\b|nerve ligation|\bsnl\b|"
    r"spinal cord injury|axotomy|sciatic nerve", re.I)
NULL_WORDING = re.compile(
    r"\b(not essential|dispensable|did not (?:alter|affect|change|differ|reduce|increase|enhance|show)|"
    r"no (?:significant|obvious|effect|difference|change)|not (?:affected|altered|changed|significantly|"
    r"different)|unchanged|failed to|without (?:affecting|altering)|independent of|no evidence)\b", re.I)
DRUG_LABEL = re.compile(
    r"inhibitor|antagonist|agonist|antibod|\bmab\b|blocker|enhancer|activator|resolvin|maresin|lipoxin|"
    r"rimegepant|fingolimod|chondroitinase|fumarate|pioglitazone|rosiglitazone|capsaicin 8|ketamine|"
    r"resiniferatoxin|suzetrigine|caryophyllene|cannabidiol|infliximab|bevacizumab|galcanezumab|otilimab", re.I)
N_CORE = 20          # pain nodes with the most evidence form the outcome set used for ranking
HEDGE = re.compile(r"\b(may|might|could|suggest|possibl|potential|appear|hypothes|propos|likely|presum)", re.I)
STATUS_WEIGHT = {"CONFIRMED": 0.95, "EXTENDED": 0.9, "MIXED": 0.5, "NO_EVIDENCE_FOUND": 0.4}


def is_crawled_link(link):
    return link.get("origin") == "auto_crawled"


def link_weight(link):
    """Confidence in a link, 0-1 (see module docstring)."""
    extra = len(link.get("crawler_evidence", []))
    if is_crawled_link(link):
        w = min(0.45 + 0.07 * (1 + extra), 0.9)
        if HEDGE.search(link.get("quote", "")):
            w -= 0.15
        return max(w, 0.2)
    status = link.get("validation_status")
    if status in STATUS_WEIGHT:
        w = STATUS_WEIGHT[status]
    elif link.get("confidence") == "INFERRED_CLOSURE" or link.get("origin") == "dynamic_closure":
        w = 0.6
    else:
        w = link.get("confidence_score") or 0.7
    return min(w + 0.02 * extra, 0.97)


def load_wrong_links(review_path):
    """(pmid, quote) of crawled links the review marked WRONG."""
    path = Path(review_path)
    if not path.exists():
        return set()
    with open(path, newline="", encoding="utf-8") as fh:
        return {(r["pmid"], r["quote"]) for r in csv.DictReader(fh) if r["verdict"] == "WRONG"}


class SignedGraph:
    """Signed, weighted, directed view of the graph, with provenance kept per link."""

    def __init__(self, graph, review_path=DEFAULT_REVIEW):
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        wrong = load_wrong_links(review_path)
        best = {}
        self.excluded = Counter()
        for link in graph["links"]:
            if link["sign"] == 0:
                continue
            if link.get("validation_status") == "REFUTED":
                self.excluded["refuted"] += 1
                continue
            if is_crawled_link(link):
                if (str(link.get("source_pmid")), link.get("quote")) in wrong:
                    self.excluded["review_wrong"] += 1
                    continue
                if NULL_WORDING.search(link.get("quote", "")):
                    self.excluded["null_result_wording"] += 1
                    continue
            key = (link["source"], link["target"], link["sign"])
            w = link_weight(link)
            if key not in best or w > best[key][0]:
                best[key] = (w, link)
        self.out = defaultdict(list)
        self.inn = defaultdict(list)
        for (s, t, sign), (w, link) in sorted(best.items(), key=lambda kv: kv[0]):
            edge = (s, t, sign, w, link)
            self.out[s].append(edge)
            self.inn[t].append(edge)
        self.edges = [e for es in self.out.values() for e in es]
        self.pain = self._pain_nodes()
        self.drugs = {n for n, node in self.nodes.items()
                      if node.get("entity_type") == "drug" or DRUG_LABEL.search(node["label"])}
        indeg = Counter({n: len(self.inn.get(n, ())) for n in self.pain})
        self.core = {n for n, _ in sorted(indeg.items(), key=lambda kv: (-kv[1], kv[0]))[:N_CORE]}
        # inducers: nothing in the graph acts on them (an injury model, LPS, a virus), so no drug can
        # "inhibit" them; they are inputs, not targets
        self.inducers = {n for n in self.nodes if n not in self.drugs and n not in self.pain
                         and (INJURY_LABEL.search(self.nodes[n]["label"]) or (self.out.get(n) and not self.inn.get(n)))}

    def label(self, nid):
        return self.nodes[nid]["label"]

    def etype(self, nid):
        return self.nodes[nid].get("entity_type") or ""

    def is_drug(self, nid):
        return nid in self.drugs

    def _pain_nodes(self):
        """Pain outcomes: symptoms with a pain word in the label (the simulator's rule), plus
        concept-typed disease nodes whose name ends in one ("Neuropathic Pain")."""
        ids = set()
        for nid, n in self.nodes.items():
            lab = n["label"].lower()
            head = lab.split("(")[0].strip()
            symptom = self.etype(nid) == "symptom" and any(s in lab for s in PAIN_LABELS)
            disease = self.etype(nid) == "concept" and head.endswith(("pain", "allodynia", "hyperalgesia"))
            if ((symptom or disease) and not any(s in lab for s in AFFECT_LABELS)
                    and not EXCLUDED_LABEL.search(n["label"])):
                ids.add(nid)
        return ids

    def distance_to(self, targets):
        """Fewest links from each node to any of `targets`."""
        dist = {t: 0 for t in targets}
        frontier = list(targets)
        while frontier:
            nxt = []
            for node in frontier:
                for s, _, _, _, _ in self.inn.get(node, ()):
                    if s not in dist:
                        dist[s] = dist[node] + 1
                        nxt.append(s)
            frontier = nxt
        return dist

    def paths(self, start, targets, max_len, dist, skip=None):
        """Simple paths start -> any target (stopping at the first target reached).
        Drugs and targets are never intermediates. `skip(edge)` drops links (leave-one-out)."""
        found = []

        def walk(node, visited, edges):
            for e in self.out.get(node, ()):
                nxt = e[1]
                if nxt in visited or (skip and skip(e)):
                    continue
                if nxt in targets:
                    found.append(edges + [e])
                    continue
                left = max_len - len(edges) - 1
                if left < 1 or self.is_drug(nxt) or dist.get(nxt, 99) > left:
                    continue
                walk(nxt, visited | {nxt}, edges + [e])

        walk(start, {start}, [])
        return found


def path_sign(path):
    sign = 1
    for e in path:
        sign *= e[2]
    return sign


def path_weight(path):
    w = PATH_DECAY ** (len(path) - 1)
    for e in path:
        w *= e[3]
    return w


def effect(paths):
    """Net signed effect from a set of paths: sum of sign * weight."""
    return sum(path_sign(p) * path_weight(p) for p in paths)


def describe_path(sg, path, quotes=True):
    """Human-readable path with the evidence behind each link."""
    parts = [sg.label(path[0][0]).split(" (")[0]]
    steps = []
    for s, t, sign, w, link in path:
        parts.append(("--+-->" if sign > 0 else "--(-)-->") + " " + sg.label(t).split(" (")[0])
        src = (f"PMID {link['source_pmid']}" if is_crawled_link(link)
               else (link.get("source_ref") or link.get("source_file") or "curated"))
        q = (link.get("quote") or "").replace("\n", " ")
        steps.append({"from": sg.label(s), "to": sg.label(t), "sign": sign, "weight": round(w, 2),
                      "source": src, "quote": q[:160] if quotes else ""})
    return " ".join(parts), steps


# ---------------------------------------------------------------------------- analyses


def outcome_effects(paths):
    """{outcome: net sign * weight over its paths}: one number per pain node, so reaching a hub
    that fans out to many pain nodes cannot multiply a score."""
    per = defaultdict(float)
    for p in paths:
        per[p[-1][1]] += path_sign(p) * path_weight(p)
    return per


def summarise(paths, sg):
    per = outcome_effects(paths)
    neg = sum(1 for v in per.values() if v < -0.05)
    pos = sum(1 for v in per.values() if v > 0.05)
    score = sum(math.tanh(v) for v in per.values())          # each outcome counts at most 1
    return per, score, neg, pos


def drug_effects(sg, skip_direct=False):
    """Per drug: effect on the core pain nodes. With skip_direct, the drug's own links to pain
    nodes are ignored (leave-one-out)."""
    dist = sg.distance_to(sg.core)
    results = {}
    for nid in sorted(sg.drugs):
        if nid not in dist:
            continue
        skip = (lambda e, nid=nid: e[0] == nid and e[1] in sg.pain) if skip_direct else None
        paths = sg.paths(nid, sg.core, MAX_LEN, dist, skip)
        if not paths:
            continue
        direct = [e for e in sg.out[nid] if e[1] in sg.pain]
        per, score, neg, pos = summarise(paths, sg)
        dominant = -1 if score < 0 else 1
        mediators = {p[0][1] for p in paths if len(p) > 1 and path_sign(p) == dominant}
        results[nid] = {
            "net": score, "outcomes": len(per), "n_neg": neg, "n_pos": pos, "mediators": len(mediators),
            "direct": sorted({e[2] for e in direct}), "paths": paths,
            "agreement": max(neg, pos) / (neg + pos) if neg + pos else 0.0,
        }
    return results


def double_edged(drugs):
    """Drugs whose direct link to pain has the opposite sign of what their other paths predict."""
    rows = [(n, r) for n, r in drugs.items() if r["mediators"] >= 1 and (
        (r["direct"] == [-1] and r["net"] >= 0.5) or (r["direct"] == [1] and r["net"] <= -0.5))]
    return sorted(rows, key=lambda x: (-abs(x[1]["net"]), x[0]))


def target_effects(sg):
    """Per non-drug node: effect on the core pain nodes, and the drugs that inhibit it."""
    dist = sg.distance_to(sg.core)
    inhibitors = defaultdict(set)
    for s, t, sign, w, link in sg.edges:
        if s in sg.drugs and sign < 0:
            inhibitors[t].add(s)
    rows = {}
    for nid in sorted(sg.nodes):
        if nid in sg.drugs or nid in sg.pain or nid not in dist:
            continue
        paths = sg.paths(nid, sg.core, TARGET_LEN, dist)
        if not paths:
            continue
        per, score, neg, pos = summarise(paths, sg)
        rows[nid] = {"net": score, "drives": pos, "suppresses": neg, "n_paths": len(paths),
                     "inhibitors": sorted(inhibitors.get(nid, ())), "paths": paths}
    return rows


def chokepoints(sg):
    """Share of pain-promoting injury -> pain paths that pass through each node."""
    sources = sorted(n for n, node in sg.nodes.items()
                     if not sg.is_drug(n) and INJURY_LABEL.search(node["label"]) and n not in sg.pain)
    dist = sg.distance_to(sg.core)
    total = 0.0
    through = Counter()
    n_paths = 0
    for src in sources:
        for p in sg.paths(src, sg.core, CHOKE_LEN, dist):
            if path_sign(p) <= 0:
                continue
            w = path_weight(p)
            total += w
            n_paths += 1
            for e in p[:-1]:
                through[e[1]] += w
    ranked = [(nid, share / total) for nid, share in through.most_common() if total]
    return {"sources": sources, "n_paths": n_paths, "ranked": ranked}


def feedback_loops(sg):
    """Simple cycles of up to CYCLE_LEN links in the signed graph, with sign and weight."""
    g = nx.DiGraph()
    for s, t, sign, w, link in sg.edges:
        if not sg.is_drug(s) and not sg.is_drug(t):
            g.add_edge(s, t)
    cycles = []
    edge = {(s, t, sign): (w, link) for s, t, sign, w, link in sg.edges}
    for comp in nx.strongly_connected_components(g):
        if len(comp) < 2:
            continue
        sub = g.subgraph(comp)
        for cyc in nx.simple_cycles(sub, length_bound=CYCLE_LEN):
            i = cyc.index(min(cyc))
            cyc = cyc[i:] + cyc[:i]            # a directed cycle has no start: begin at the smallest id
            # a cycle may use either sign for a pair carrying both; take each combination's best
            steps = [[(cyc[i], cyc[(i + 1) % len(cyc)], sign) for sign in (1, -1)
                      if (cyc[i], cyc[(i + 1) % len(cyc)], sign) in edge] for i in range(len(cyc))]
            combos = [[]]
            for options in steps:
                combos = [c + [o] for c in combos for o in options]
            for combo in combos:
                sign = 1
                w = 1.0
                for key in combo:
                    sign *= key[2]
                    w *= edge[key][0]
                cycles.append({"nodes": list(cyc), "sign": sign, "weight": w, "edges": [edge[k][1] for k in combo]})
    return cycles


def calibration(sg):
    """(a) predict each direct link's sign from its two-hop paths; (b) predict each drug's
    direct pain link from paths with that link removed."""
    two_hop = defaultdict(list)
    for s, t, sign, w, link in sg.edges:
        for s2, t2, sign2, w2, link2 in sg.out.get(t, ()):
            if s2 == t and t2 != s:
                two_hop[(s, t2)].append(sign * sign2 * w * w2)
    direct = defaultdict(set)
    for s, t, sign, w, link in sg.edges:
        direct[(s, t)].add(sign)
    buckets = {"curated": [0, 0], "crawled": [0, 0], "all": [0, 0]}
    by_support = {1: [0, 0], 2: [0, 0], 3: [0, 0]}
    for s, t, sign, w, link in sg.edges:
        if len(direct[(s, t)]) > 1 or (s, t) not in two_hop:
            continue
        scores = two_hop[(s, t)]
        net = sum(scores)
        if net == 0:
            continue
        ok = (net > 0) == (sign > 0)
        for k in ("all", "crawled" if is_crawled_link(link) else "curated"):
            buckets[k][0] += ok
            buckets[k][1] += 1
        for n in by_support:
            if len(scores) >= n:
                by_support[n][0] += ok
                by_support[n][1] += 1
    full = drug_effects(sg)
    loo = drug_effects(sg, skip_direct=True)
    known = {n: r for n, r in full.items() if len(r["direct"]) == 1 and n in loo}
    hits = Counter()
    for n, r in known.items():
        hits[(r["direct"][0], -1 if loo[n]["net"] < 0 else 1)] += 1
    base_neg = sum(1 for r in loo.values() if r["net"] < 0) / max(len(loo), 1)
    # discrimination: P(a known analgesic scores lower than a drug with no direct pain link)
    analgesics = [loo[n]["net"] for n, r in known.items() if r["direct"] == [-1]]
    others = [r["net"] for n, r in loo.items() if not full[n]["direct"]]
    wins = sum((a < o) + 0.5 * (a == o) for a in analgesics for o in others)
    auc = wins / (len(analgesics) * len(others)) if analgesics and others else float("nan")
    raising = sorted(n for n, r in full.items() if r["net"] >= 1.0 and r["mediators"] >= 2 and r["agreement"] >= 0.8)
    return {"two_hop": buckets, "two_hop_by_support": by_support, "loo": dict(hits), "loo_n": len(known),
            "base_rate_negative": base_neg, "auc": auc, "auc_n": (len(analgesics), len(others)),
            "n_pain_raising": len(raising)}


# ---------------------------------------------------------------------------- report


def _dup_keys(label):
    """Normalised spellings of an entity name: its head and each "(...)" group, minus a
    trailing receptor suffix ("P2X7R" -> "p2x7")."""
    out = set()
    head = label.split("(")[0]
    for part in [head] + re.findall(r"\(([^)]*)\)", label):
        key = re.sub(r"[^a-z0-9]", "", part.lower().replace("receptor", "").replace("α", "alpha").replace("β", "beta"))
        key = re.sub(r"(\d[a-z]?)r$", r"\1", key)
        if len(key) >= 4:
            out.add(key)
    return out


def duplicate_nodes(sg):
    """(crawled node, curated node, links) where a crawled node's spelling equals a curated node's."""
    curated = {}
    for nid, node in sg.nodes.items():
        if node.get("file_type") != "crawled":
            for key in sorted(_dup_keys(node["label"])):
                curated.setdefault(key, nid)
    degree = Counter()
    for s_, t, *_ in sg.edges:
        degree[s_] += 1
        degree[t] += 1
    found = []
    for nid, node in sg.nodes.items():
        if node.get("file_type") != "crawled":
            continue
        for key in sorted(_dup_keys(node["label"])):
            if key in curated and curated[key] != nid:
                found.append((nid, curated[key], degree[nid]))
                break
    found.sort(key=lambda x: (-x[2], x[0]))
    return found


def short(sg, nid):
    return sg.label(nid).split(" (")[0]


def build_report(graph, review_path=DEFAULT_REVIEW):
    sg = SignedGraph(graph, review_path)
    drugs = drug_effects(sg)
    targets = target_effects(sg)
    choke = chokepoints(sg)
    loops = feedback_loops(sg)
    cal = calibration(sg)
    return sg, drugs, targets, choke, loops, cal


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "n/a"


def render_markdown(sg, drugs, targets, choke, loops, cal, top=15):
    L = []
    add = L.append
    crawled = sum(1 for e in sg.edges if is_crawled_link(e[4]))
    add("# Signed-path inference over the knowledge graph\n")
    add(f"Signed graph: {len(sg.edges)} links ({crawled} crawled and unreviewed, {len(sg.edges) - crawled} curated) "
        f"over {len({e[0] for e in sg.edges} | {e[1] for e in sg.edges})} nodes; {len(sg.pain)} pain nodes. "
        f"Excluded: {dict(sg.excluded)}.\n")
    add("**Every inference below is a hypothesis built from signs composed along paths; most links are "
        "crawled and unreviewed.** The calibration section says how far to trust them.\n")

    add("## 0. Calibration: does composing signs along paths reproduce known links?\n")
    for k in ("curated", "crawled", "all"):
        a_, n = cal["two_hop"][k]
        add(f"- two-hop paths predict a direct link's sign ({k}): **{pct(a_, n)}** ({a_}/{n})")
    for n, (a_, m) in sorted(cal["two_hop_by_support"].items()):
        add(f"- ... with at least {n} supporting two-hop path(s): {pct(a_, m)} ({a_}/{m})")
    hits, tot = cal["loo"], cal["loo_n"]
    analg = hits.get((-1, -1), 0) + hits.get((-1, 1), 0)
    pro_ = hits.get((1, 1), 0) + hits.get((1, -1), 0)
    na, no = cal["auc_n"]
    add(f"- leave-one-out, {tot} drugs with a known direct effect on pain (that link removed, the effect re-predicted "
        f"from the other paths): known analgesics predicted analgesic {pct(hits.get((-1, -1), 0), analg)} "
        f"({hits.get((-1, -1), 0)}/{analg}), known pain-raising drugs predicted pain-raising "
        f"{pct(hits.get((1, 1), 0), pro_)} ({hits.get((1, 1), 0)}/{pro_}). **But the method calls "
        f"{100 * cal['base_rate_negative']:.0f}% of all drugs analgesic**, so recovering known analgesics is "
        f"almost uninformative: the crawl is selection-biased, since a drug that appears in a pain paper is "
        f"mostly being studied as an analgesic.")
    add(f"- discrimination: a known analgesic scores lower (more analgesic) than a drug with no direct pain link "
        f"with probability **{cal['auc']:.2f}** (AUC; {na} known analgesics vs {no} others; 0.5 is chance, and "
        f"drugs with more links tend to score more extreme, which inflates it)")
    add(f"- the clearest check is the rare opposite call: {cal['n_pain_raising']} drugs are predicted pain-raising "
        f"(section 1 lists them), and they should be known pain inducers\n")
    add(f"Outcome set for ranking: the {len(sg.core)} best-evidenced pain nodes ("
        + ", ".join(sorted(short(sg, n) for n in sg.core)[:12]) + ", ...). Each outcome counts at most 1, so "
        "reaching a hub that fans out to many pain nodes does not inflate a score.\n")

    add(f"## 1. Predicted drug effects on pain (paths up to {MAX_LEN} links)\n")
    cand = [(n, r) for n, r in drugs.items()
            if r["net"] <= -1.0 and not r["direct"] and r["mediators"] >= 2 and r["agreement"] >= 0.8]
    cand.sort(key=lambda x: (x[1]["net"], -x[1]["mediators"], x[0]))
    add(f"{len(drugs)} drugs reach the core pain nodes. **Novel analgesic candidates** (net score <= -1, >=2 "
        f"independent mediators, >=80% of reached pain nodes agree, no direct drug -> pain link in the graph): "
        f"{len(cand)}. *Read this as a literature-weighted ranking, not a prediction: the AUC above is only "
        f"{cal['auc']:.2f}, because most drugs in a pain crawl are analgesics.* Strongest:\n")
    add("| drug | score | pain nodes (-/+) | mediators | shortest strong path |\n|---|---|---|---|---|")
    for n, r in cand[:top]:
        best = min((p for p in r["paths"] if path_sign(p) < 0), key=lambda p: (len(p), -path_weight(p)))
        add(f"| {short(sg, n)} | {r['net']:.2f} | {r['n_neg']}/{r['n_pos']} | {r['mediators']} | {describe_path(sg, best, False)[0]} |")
    pro = [(n, r) for n, r in drugs.items() if r["net"] >= 1.0 and r["mediators"] >= 2 and r["agreement"] >= 0.8]
    pro.sort(key=lambda x: (-x[1]["net"], x[0]))
    add(f"\n**Drugs predicted to worsen pain** (score >= 1, >=2 mediators, >=80% agreement): {len(pro)}. Strongest:\n")
    add("| drug | score | direct link | shortest strong path |\n|---|---|---|---|")
    for n, r in pro[:8]:
        best = min((p for p in r["paths"] if path_sign(p) > 0), key=lambda p: (len(p), -path_weight(p)))
        add(f"| {short(sg, n)} | +{r['net']:.2f} | {r['direct'] or 'none'} | {describe_path(sg, best, False)[0]} |")

    dbl = double_edged(drugs)
    add(f"\n**Double-edged drugs** (the direct link says one thing, the other paths the opposite; {len(dbl)}): a "
        "context-dependent effect, or an off-target liability.\n")
    add("| drug | direct link | score from other paths | shortest opposing path |\n|---|---|---|---|")
    for n, r in dbl[:8]:
        want = 1 if r["direct"] == [-1] else -1
        best = min((p for p in r["paths"] if path_sign(p) == want), key=lambda p: (len(p), -path_weight(p)))
        add(f"| {short(sg, n)} | {'analgesic' if r['direct'] == [-1] else 'pain-raising'} | {r['net']:+.1f} | {describe_path(sg, best, False)[0]} |")

    add("\n## 2. Targets: what drives pain, and what no drug yet hits\n")
    inducers = sorted(((n, r) for n, r in targets.items() if n in sg.inducers and r["net"] > 0 and r["drives"] >= 2),
                      key=lambda x: (-x[1]["net"], x[0]))
    rows = [(n, r) for n, r in targets.items() if n not in sg.inducers and r["net"] > 0 and r["drives"] >= 2]
    rows.sort(key=lambda x: (-x[1]["net"], x[0]))
    add("| target | drives pain (score) | core pain nodes driven | drugs inhibiting it |\n|---|---|---|---|")
    for n, r in rows[:top]:
        add(f"| {short(sg, n)} ({sg.etype(n)}) | {r['net']:.2f} | {r['drives']} | {len(r['inhibitors'])} |")
    gaps = [(n, r) for n, r in rows if not r["inhibitors"] and sg.etype(n) in ("molecule", "receptor", "channel", "pathway")]
    add(f"\n**Druggable gaps** (drives >=2 core pain nodes, no inhibiting drug in the graph): {len(gaps)}. Top:\n")
    for n, r in gaps[:10]:
        add(f"- {short(sg, n)} ({sg.etype(n)}): score {r['net']:.2f}, drives {r['drives']} core pain nodes")
    add("\n**Inducers** (nothing in the graph acts on them, so they are inputs, not targets): " + ", ".join(
        f"{short(sg, n)} ({r['net']:.1f})" for n, r in inducers[:10]) + "\n")
    supp = [(n, r) for n, r in targets.items() if n not in sg.inducers and r["net"] < 0 and r["suppresses"] >= 2]
    supp.sort(key=lambda x: (x[1]["net"], x[0]))
    add("\n**Pain-suppressing nodes** (raising them lowers pain): " + ", ".join(
        f"{short(sg, n)} ({r['net']:.2f})" for n, r in supp[:10]) + "\n")

    add(f"## 3. Chokepoints between nerve-injury models and pain\n")
    add(f"{len(choke['sources'])} injury nodes, {choke['n_paths']} pain-promoting paths (up to {CHOKE_LEN} links). "
        f"Share of the weighted flow passing through each node:\n")
    for nid, share in choke["ranked"][:top]:
        add(f"- {short(sg, nid)} ({sg.etype(nid)}): {100 * share:.0f}%")

    add("\n## 4. Feedback loops\n")
    pairs = [c for c in loops if len(c["nodes"]) == 2]
    longer = [c for c in loops if len(c["nodes"]) > 2]
    pos2 = sorted((c for c in pairs if c["sign"] > 0), key=lambda c: (-round(c["weight"], 9), c["nodes"]))
    pos = [c for c in longer if c["sign"] > 0]
    neg = [c for c in longer if c["sign"] < 0]
    add(f"{len(pairs)} two-node loops (A acts on B and B acts back; {len(pos2)} mutually reinforcing) and "
        f"{len(longer)} loops of 3-{CYCLE_LEN} links: **{len(pos)} self-amplifying** (even number of inhibitory "
        f"links), {len(neg)} self-limiting.\n")
    add("Strongest mutually reinforcing pairs: " + "; ".join(
        f"{short(sg, c['nodes'][0])} <-> {short(sg, c['nodes'][1])} ({c['weight']:.2f})" for c in pos2[:8]) + "\n")
    part = Counter(n for c in pos for n in c["nodes"])
    add("Nodes in the most self-amplifying 3+ node loops (a cut here breaks the most vicious circles): " + ", ".join(
        f"{short(sg, n)} ({k})" for n, k in part.most_common(10)) + "\n")
    pos.sort(key=lambda c: (-round(c["weight"], 9), len(c["nodes"]), c["nodes"]))
    add("Strongest self-amplifying 3+ node loops:\n")
    for c in pos[:8]:
        names = [short(sg, n) for n in c["nodes"]]
        signs = [e["sign"] for e in c["edges"]]
        add(f"- {' -> '.join(names)} -> {names[0]}  (weight {c['weight']:.2f}, {sum(1 for x in signs if x < 0)} inhibitory)")

    add("\n## 5. Graph hygiene: duplicate nodes split the evidence\n")
    dups = duplicate_nodes(sg)
    add(f"{len(dups)} crawled nodes name the same entity as a curated node under another spelling, so their links "
        "never reach the curated node. Largest:\n")
    for crawled, curated, links in dups[:10]:
        add(f"- {sg.label(crawled)} ({links} links) = {short(sg, curated)}")
    return "\n".join(L) + "\n"


def to_json(sg, drugs, targets, choke, loops, cal):
    def ids(rows, key, n=40):
        return [{"node": k, "label": sg.label(k), **{f: round(v, 3) if isinstance(v, float) else v
                                                     for f, v in r.items() if f != "paths"}}
                for k, r in sorted(rows.items(), key=key)[:n]]
    return {
        "excluded": dict(sg.excluded),
        "calibration": {k: v for k, v in cal.items() if k != "loo"} | {"loo": {f"{a}/{b}": v for (a, b), v in cal["loo"].items()}},
        "drug_effects": ids(drugs, lambda kv: kv[1]["net"]),
        "targets": ids(targets, lambda kv: (-kv[1]["net"], kv[0])),
        "chokepoints": [{"node": n, "label": sg.label(n), "share": round(s, 4)} for n, s in choke["ranked"][:40]],
        "loops": {"positive": sum(1 for c in loops if c["sign"] > 0), "negative": sum(1 for c in loops if c["sign"] < 0)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(DEFAULT_GRAPH))
    ap.add_argument("--review", default=str(DEFAULT_REVIEW))
    ap.add_argument("--json")
    ap.add_argument("--markdown")
    args = ap.parse_args(argv)
    graph = json.loads(Path(args.graph).read_text())
    sg, drugs, targets, choke, loops, cal = build_report(graph, args.review)
    md = render_markdown(sg, drugs, targets, choke, loops, cal)
    if args.markdown:
        Path(args.markdown).write_text(md)
    else:
        print(md)
    if args.json:
        Path(args.json).write_text(json.dumps(to_json(sg, drugs, targets, choke, loops, cal), indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
