#!/usr/bin/env python3
"""Executable models of the canonical network (scope phase 3).

Three ways to predict how perturbing one node moves another, all on the same network
(analysis/canonical/network.json) and the same links:

  NetfluxModel   normalized-Hill ordinary differential equations (Kraeutler, Soltis & Saucerman,
                 BMC Syst Biol 2010). Each node's activity y in [0, 1] relaxes towards
                 f(inputs) = [1 - (1 - basal) * prod(1 - act_k)] * prod(1 - inh_j):
                 activators combine by OR (with a basal input), inhibitors by AND NOT. Each link
                 is a normalized Hill function with weight w, exponent n and half-maximum EC50.
  BooleanModel   the same logic with on/off states, updated synchronously; a node with no
                 activators is on when endogenous; the readout is averaged over the attractor.
  static_effect  the sum over signed paths of sign * product of weights * decay^(length - 1), as
                 graph_inference.py does on the full graph.

Exogenous nodes (drugs, interventions such as electroacupuncture, other diseases) have no basal
input: they are off until a perturbation switches them on. A perturbation clamps a node: loss to
0, gain or drug to 1. The predicted change of a readout is the sign of perturbed minus baseline
steady state.
"""

import math
import re
from collections import defaultdict

import numpy as np

EXOGENOUS_LABEL = re.compile(
    r"acupuncture|stimulation|exercise|endometriosis|arthritis|neuralgia|degeneration|tolerance|injury|"
    r"disease|transplant|diet\b|surgery", re.I)
DEFAULT_TIER_WEIGHTS = {"T1": 1.0, "T2": 1.0, "T3": 1.0, "P": 1.0, "D": 1.0, "L": 1.0}


def link_weight(link, tier_weights):
    """A link's weight: the best of its tiers' weights."""
    return max(tier_weights.get(t, 0.0) for t in link["tiers"])


def usable_for(link, pmid):
    """Can a case from paper pmid use this link? Prior, dossier and drug-target links always; a
    crawled link only with a paper other than the case's own (leave-one-paper-out)."""
    tiers = set(link["tiers"])
    if tiers & {"P", "D", "L", "T2"} or link.get("target_annotation") or link.get("curated"):
        return True
    return any(p != pmid for p in link.get("papers", []))


def select_links(network, pmid=None, tiers=None, tier_weights=None):
    """(source, target, sign, weight) of the links a case may use."""
    tier_weights = tier_weights or DEFAULT_TIER_WEIGHTS
    out = []
    for link in network["links"]:
        if tiers is not None and not (set(link["tiers"]) & tiers):
            continue
        if pmid is not None and not usable_for(link, pmid):
            continue
        w = link_weight(link, tier_weights)
        if w > 0:
            out.append((link["source"], link["target"], link["sign"], w))
    return out


def exogenous_nodes(network):
    return {n["id"] for n in network["nodes"] if n["kind"] == "drug" or EXOGENOUS_LABEL.search(n["label"])}


class NetfluxModel:
    """logic: "or"        Netflux: activators OR (with the basal input), inhibitors AND NOT
              "or-scaled" the same, each input's weight divided by the node's number of inputs of
                          that kind, so that a hub with dozens of activators does not saturate
              "mean"      activity = basal + (1 - basal) * mean(activations), times
                          1 - mean(inhibitions): one input of k moves a node by about 1/k"""

    def __init__(self, nodes, links, exogenous, basal=0.1, n=1.4, ec50=0.5, tau=1.0, logic="or"):
        self.logic = logic
        self.ids = list(nodes)
        self.index = {nid: i for i, nid in enumerate(self.ids)}
        self.basal = np.array([0.0 if nid in exogenous else basal for nid in self.ids])
        self.n, self.ec50, self.tau = n, ec50, tau
        self.B = (ec50 ** n - 1) / (2 * ec50 ** n - 1)
        self.K = (self.B - 1) ** (1 / n)
        act = [(self.index[s], self.index[t], w) for s, t, sign, w in links if sign > 0 and s in self.index and t in self.index]
        inh = [(self.index[s], self.index[t], w) for s, t, sign, w in links if sign < 0 and s in self.index and t in self.index]
        size = len(self.ids)
        self.n_act = np.bincount([t for _, t, _ in act], minlength=size).astype(float)
        self.n_inh = np.bincount([t for _, t, _ in inh], minlength=size).astype(float)
        if logic == "or-scaled":
            act = [(s, t, w / self.n_act[t]) for s, t, w in act]
            inh = [(s, t, w / self.n_inh[t]) for s, t, w in inh]
        self.act = tuple(np.array(c) for c in zip(*act)) if act else (np.array([], int), np.array([], int), np.array([]))
        self.inh = tuple(np.array(c) for c in zip(*inh)) if inh else (np.array([], int), np.array([], int), np.array([]))

    def hill(self, x, w):
        xn = np.power(np.clip(x, 0.0, 1.0), self.n)
        return w * self.B * xn / (self.K ** self.n + xn)

    def target(self, y):
        size = len(self.ids)
        if self.logic == "mean":
            act = self.basal.copy()
            if len(self.act[0]):
                s = np.bincount(self.act[1], self.hill(y[self.act[0]], self.act[2]), size)
                has = self.n_act > 0
                act[has] = self.basal[has] + (1 - self.basal[has]) * s[has] / self.n_act[has]
            inh = np.ones(size)
            if len(self.inh[0]):
                s = np.bincount(self.inh[1], self.hill(y[self.inh[0]], self.inh[2]), size)
                has = self.n_inh > 0
                inh[has] = 1 - s[has] / self.n_inh[has]
            return act * inh
        log_not_act = np.log(np.clip(1.0 - self.basal, 1e-12, 1.0))
        if len(self.act[0]):
            fa = self.hill(y[self.act[0]], self.act[2])
            log_not_act = log_not_act + np.bincount(self.act[1], np.log(np.clip(1.0 - fa, 1e-12, 1.0)), size)
        log_inh = np.zeros(size)
        if len(self.inh[0]):
            fi = self.hill(y[self.inh[0]], self.inh[2])
            log_inh = np.bincount(self.inh[1], np.log(np.clip(1.0 - fi, 1e-12, 1.0)), size)
        return (1.0 - np.exp(log_not_act)) * np.exp(log_inh)

    def steady_state(self, clamp=None, dt=0.1, max_steps=6000, tol=1e-9):
        y = self.basal.copy()
        idx = np.array([self.index[k] for k in (clamp or {})], int)
        val = np.array([v for v in (clamp or {}).values()], float)
        if len(idx):
            y[idx] = val
        for _ in range(max_steps):
            dy = dt * (self.target(y) - y) / self.tau
            if len(idx):
                dy[idx] = 0.0
            y = y + dy
            if np.max(np.abs(dy)) < tol:
                break
        return y

    def effect(self, actor, readout, value, base=None):
        base = self.steady_state() if base is None else base
        pert = self.steady_state({actor: value})
        return float(pert[self.index[readout]] - base[self.index[readout]])


class BooleanModel:
    """logic: "or"         on when any activator is on (an endogenous node without activators is on),
                           and no inhibitor is on
              "threshold"  on when more activators than inhibitors are on (an endogenous node without
                           activators counts one activation)"""

    def __init__(self, nodes, links, exogenous, logic="or"):
        self.logic = logic
        self.ids = list(nodes)
        self.index = {nid: i for i, nid in enumerate(self.ids)}
        self.exo = np.array([nid in exogenous for nid in self.ids])
        self.act = defaultdict(list)
        self.inh = defaultdict(list)
        for s, t, sign, w in links:
            if s in self.index and t in self.index:
                (self.act if sign > 0 else self.inh)[self.index[t]].append(self.index[s])
        self.has_act = np.array([bool(self.act[i]) for i in range(len(self.ids))])

    def step(self, s):
        new = np.zeros_like(s)
        for i in range(len(s)):
            if self.logic == "threshold":
                a = sum(1 for j in self.act[i] if s[j]) if self.has_act[i] else (0 if self.exo[i] else 1)
                new[i] = a > sum(1 for j in self.inh[i] if s[j])
            else:
                on = any(s[j] for j in self.act[i]) if self.has_act[i] else not self.exo[i]
                new[i] = on and not any(s[j] for j in self.inh[i])
        return new

    def attractor_mean(self, clamp=None, max_steps=300):
        s = ~self.exo
        clamp = {self.index[k]: bool(v) for k, v in (clamp or {}).items()}
        for i, v in clamp.items():
            s[i] = v
        seen = {}
        history = []
        for t in range(max_steps):
            key = s.tobytes()
            if key in seen:
                cycle = history[seen[key]:]
                return np.mean(cycle, axis=0)
            seen[key] = t
            history.append(s.astype(float))
            s = self.step(s)
            for i, v in clamp.items():
                s[i] = v
        return np.mean(history[-20:], axis=0)

    def effect(self, actor, readout, value, base=None):
        base = self.attractor_mean() if base is None else base
        pert = self.attractor_mean({actor: value})
        return float(pert[self.index[readout]] - base[self.index[readout]])


def static_effect(links, actor, readout, max_len=3, decay=0.7, avoid=frozenset()):
    """Sum over simple signed paths actor -> readout of sign * product(weights) * decay^(len - 1);
    nodes in `avoid` (drugs) are never intermediate steps."""
    out = defaultdict(list)
    for s, t, sign, w in links:
        out[s].append((t, sign, w))
    total = 0.0

    def walk(node, depth, sign, weight, visited):
        nonlocal total
        for t, sg, w in out.get(node, ()):
            if t in visited:
                continue
            if t == readout:
                total += sign * sg * weight * w * decay ** depth
            elif depth + 1 < max_len and t not in avoid:
                walk(t, depth + 1, sign * sg, weight * w, visited | {t})

    walk(actor, 0, 1, 1.0, {actor})
    return total


def source_tendency(links, actor):
    """The actor's usual sign: the sum of its out-links' signs."""
    return sum(sign for s, t, sign, w in links if s == actor)


def sign_of(x, eps=1e-6):
    return 0 if abs(x) <= eps else (1 if x > 0 else -1)
