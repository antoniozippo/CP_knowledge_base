#!/usr/bin/env python3
"""Score the executable models on the validation set (scope phase 3).

For every scorable case (analysis/canonical/scorable_cases.csv) the network is cut to the links the
case may use: a build case loses the links whose only evidence is its own paper (leave-one-paper-out);
a test case's papers were never in the network. Each method then predicts how the readout moved
under the case's perturbation (loss clamps the actor to 0, gain or a drug to 1):

  netflux    normalized-Hill ODE, default parameters fixed before scoring (basal 0.1, n 1.4,
             EC50 0.5, every tier weight 1)
  boolean    the same logic, on/off, synchronous update
  static     sign of the summed signed paths of up to 3 links
  source     the actor's usual sign (its out-links), the baseline that explained most of the
             graph's sign agreement (analysis/scripts/calibration_baselines.py)
  majority   the commoner implied sign of the build cases

A prediction of no change counts as wrong. A Netflux parameter sweep is scored on build cases only;
the setting that does best there is then read once on the test cases, beside the default.

Outputs in analysis/functional/: predictions.csv, results.md.
Usage: python3 analysis/scripts/evaluate_functional_model.py
"""

import csv
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import functional_model as fm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NETWORK = ROOT / "analysis" / "canonical" / "network.json"
CASES = ROOT / "analysis" / "canonical" / "scorable_cases.csv"
OUT = ROOT / "analysis" / "functional"
# fixed before scoring; it saturates (see README), and stays in the report as the pre-registered result
DEFAULT = {"basal": 0.1, "n": 1.4, "ec50": 0.5, "weights": "uniform", "tiers": "all", "logic": "or"}
TIER_SETS = {"all": None, "no T3": {"T1", "T2", "P", "D", "L"}, "no prior": {"T1", "T2", "T3", "D", "L"}}
WEIGHTS = {"uniform": fm.DEFAULT_TIER_WEIGHTS,
           "tiered": {"T1": 1.0, "T2": 0.8, "T3": 0.5, "P": 0.6, "D": 1.0, "L": 1.0}}


def wilson(k, n, z=1.96):
    if not n:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def direction(perturbation):
    return -1 if perturbation == "loss" else 1


def predict_case(network, case, majority, cfg, exo, with_baselines=True):
    links = fm.select_links(network, case["pmid"], TIER_SETS[cfg["tiers"]], WEIGHTS[cfg["weights"]])
    nodes = [n["id"] for n in network["nodes"]]
    actor, readout, d = case["actor_canon"], case["readout_canon"], direction(case["perturbation"])
    value = 0.0 if case["perturbation"] == "loss" else 1.0
    nf = fm.NetfluxModel(nodes, links, exo, basal=cfg["basal"], n=cfg["n"], ec50=cfg["ec50"], logic=cfg.get("logic", "or"))
    out = {"netflux": fm.sign_of(nf.effect(actor, readout, value))}
    if with_baselines:
        out["boolean"] = fm.sign_of(fm.BooleanModel(nodes, links, exo).effect(actor, readout, value))
        out["boolean_threshold"] = fm.sign_of(fm.BooleanModel(nodes, links, exo, "threshold").effect(actor, readout, value))
        out["static"] = fm.sign_of(fm.static_effect(links, actor, readout, avoid=exo - {actor})) * d
        out["source"] = fm.sign_of(fm.source_tendency(links, actor)) * d
        out["majority"] = majority * d
    return out


def score(rows, method, subset=lambda r: True):
    sel = [r for r in rows if subset(r)]
    k = sum(r[method] == r["observed"] for r in sel)
    none = sum(r[method] == 0 for r in sel)
    return k, len(sel), none


def fmt(k, n, none=None):
    lo, hi = wilson(k, n)
    s = f"{k}/{n} = {100 * k / n:.0f}% (95% CI {100 * lo:.0f}-{100 * hi:.0f})" if n else "-"
    return s + (f", {none} no call" if none else "")


def main():
    network = json.loads(NETWORK.read_text())
    cases = list(csv.DictReader(open(CASES, encoding="utf-8")))
    exo = fm.exogenous_nodes(network)
    implied = Counter(int(c["implied_sign"]) for c in cases if c["split"] == "build")
    majority = implied.most_common(1)[0][0]
    rows = []
    for c in cases:
        p = predict_case(network, c, majority, DEFAULT, exo)
        rows.append({**c, **p, "observed": int(c["observed_change"]), "kind": "drug" if c["perturbation"] == "drug" else "knockdown or overexpression"})
    methods = ["netflux", "boolean", "boolean_threshold", "static", "source", "majority"]
    # parameter sweep on build cases only
    grid = [dict(zip(["logic", "basal", "n", "ec50", "weights", "tiers"], v)) for v in itertools.product(
        ["or", "or-scaled", "mean"], [0.05, 0.1, 0.25], [1.4], [0.5], ["uniform", "tiered"], ["all", "no T3", "no prior"])]
    build = [c for c in cases if c["split"] == "build"]
    sweep = []
    for cfg in grid:
        k = sum(predict_case(network, c, majority, cfg, exo, False)["netflux"] == int(c["observed_change"]) for c in build)
        sweep.append((k, cfg))
    sweep.sort(key=lambda x: -x[0])
    best_k, best = sweep[0]
    test = [c for c in cases if c["split"] == "test"]
    by_id = {r["case_id"]: r for r in rows}
    for c in cases:                      # the build-chosen setting, on every case (test read once, here)
        by_id[c["case_id"]]["netflux_best"] = predict_case(network, c, majority, best, exo, False)["netflux"]
    methods = ["netflux", "netflux_best"] + methods[1:]

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "predictions.csv", "w", newline="", encoding="utf-8") as fh:
        fields = ["case_id", "split", "pmid", "perturbation", "actor_canon", "readout_canon", "observed"] + methods
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    L = ["# Functional model: results (scope phase 3)", "",
         "Built by `analysis/scripts/evaluate_functional_model.py` on `analysis/canonical/network.json` and the "
         f"{len(cases)} scorable cases. See `README.md` for the methods and caveats.", "",
         f"Majority implied sign among build cases: {majority:+d} ({implied[majority]} of {sum(implied.values())}).", "",
         "## Accuracy: did the method predict the direction the readout moved?", "",
         "Build cases: leave-one-paper-out. Test cases: papers after the test cut, never in the network. "
         "A prediction of no change counts as wrong.", "",
         "`netflux` is the default fixed before scoring; `netflux_best` the setting chosen on build cases only "
         "(sweep below).", "",
         "| Method | Build (leave one paper out) | Test (held out) |", "|---|---|---|"]
    for m in methods:
        L.append(f"| {m} | {fmt(*score(rows, m, lambda r: r['split'] == 'build'))} | {fmt(*score(rows, m, lambda r: r['split'] == 'test'))} |")
    for kind in ("drug", "knockdown or overexpression"):
        L += ["", f"### {kind.capitalize()} cases", "", "| Method | Build | Test |", "|---|---|---|"]
        for m in methods:
            L.append(f"| {m} | {fmt(*score(rows, m, lambda r: r['split'] == 'build' and r['kind'] == kind))} | "
                     f"{fmt(*score(rows, m, lambda r: r['split'] == 'test' and r['kind'] == kind))} |")
    L += ["", "## Where the model and the majority baseline disagree", "",
          "Agreement with a baseline earns nothing; these cases are where a model has to show what it adds.", ""]
    for m in ("netflux", "netflux_best", "boolean", "boolean_threshold", "static", "source"):
        dis = [r for r in rows if r[m] != r["majority"]]
        k = sum(r[m] == r["observed"] for r in dis)
        kb = sum(r["majority"] == r["observed"] for r in dis)
        L.append(f"- {m}: disagrees on {len(dis)} cases; right on {k}, the majority baseline right on {kb}")
    # head to head, and the cases a direct link from another paper already answers
    for r, c in zip(rows, cases):
        links = fm.select_links(network, c["pmid"], None, WEIGHTS["uniform"])
        direct = sum(sign for s_, t, sign, w in links if s_ == c["actor_canon"] and t == c["readout_canon"])
        r["direct"] = fm.sign_of(direct) * direction(c["perturbation"])
        r["has_direct"] = direct != 0
    L += ["", "## Head to head", ""]
    for a_, b_ in (("netflux_best", "static"), ("netflux_best", "source"), ("static", "source")):
        dis = [r for r in rows if r[a_] != r[b_]]
        L.append(f"- {a_} vs {b_}: disagree on {len(dis)} cases; {a_} right on {sum(r[a_] == r['observed'] for r in dis)}, "
                 f"{b_} right on {sum(r[b_] == r['observed'] for r in dis)}")
    nd = [r for r in rows if r["has_direct"]]
    L += ["", "## Cases a direct link already answers", "",
          f"{len(nd)} of {len(rows)} scorable cases have a direct actor -> readout link from another paper (or the "
          f"dossiers). Its sign alone is right on {sum(r['direct'] == r['observed'] for r in nd)} of them. Only the "
          f"{len(rows) - len(nd)} cases without one test reasoning over the network:", "",
          "| Method | Cases with a direct link | Cases without one |", "|---|---|---|"]
    for m in methods:
        L.append(f"| {m} | {fmt(*score(rows, m, lambda r: r['has_direct']))} | {fmt(*score(rows, m, lambda r: not r['has_direct']))} |")
    L += ["", "## Netflux parameter sweep (build cases only)", "",
          f"{len(grid)} settings: logic OR (Netflux), OR with inputs scaled by their number, or mean of inputs; basal "
          "input 0.05/0.1/0.25; tier weights uniform or tiered (T1 1, T2 0.8, T3 0.5, P 0.6); all links, without T3, "
          "or without the prior. Hill exponent 1.4, EC50 0.5.", "",
          "| Build correct | Setting |", "|---|---|"]
    for k, cfg in sweep[:6] + sweep[-3:]:
        L.append(f"| {k}/{len(build)} | {cfg} |")
    L += ["", f"Best on build: {best}, {best_k}/{len(build)} (`netflux_best` in the tables above, read once on the "
          "test cases). `netflux` is the default fixed before scoring.", ""]
    (OUT / "results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
