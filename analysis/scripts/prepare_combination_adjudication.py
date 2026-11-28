#!/usr/bin/env python3
"""Prepare the expert check of the combination records (phase 4, step 1) and score it once returned.

  python3 analysis/scripts/prepare_combination_adjudication.py prepare   # writes the sheet
  python3 analysis/scripts/prepare_combination_adjudication.py score     # agreement, from the filled sheet

The sheet (analysis/combinations/adjudication_sample.csv) holds 120 records: every scored case that
carries a synergy or additive label, a random draw of the other scored cases, and a draw of the
unscored records so that each interaction class has at least 8. For each the expert sees the
extracted fields, the verbatim quote with the text around it, and a PubMed link, and fills the
`expert_*` columns. Sampling is fixed (seed 7).
"""

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_combinations as ec  # noqa: E402

OUT = ROOT / "analysis" / "combinations"
SHEET = OUT / "adjudication_sample.csv"
CACHE = ROOT / "crawler" / "cache"
N, SEED, MIN_PER_CLASS, WINDOW = 120, 7, 8, 700
EXPERT = ["expert_ran_in_paper", "expert_interventions_ok", "expert_readout_ok", "expert_direction_combination",
          "expert_direction_a", "expert_direction_b", "expert_interaction", "expert_in_context", "reviewer", "notes"]


def context_around(pmid, quote):
    path = CACHE / f"paper_{pmid}.json"
    if not path.exists():
        return ""
    from crawler import agent_extract as ae
    text = re.sub(r"\s+", " ", ae._cached_text(json.loads(path.read_text())))
    probe = " ".join(quote.split()[:8])
    i = text.find(probe)
    if i < 0:
        return ""
    return text[max(0, i - WINDOW): i + len(quote) + WINDOW]


def prepare():
    records = ec.load_records()
    scored = {r["rec"]: r for r in csv.DictReader(open(OUT / "cases.csv", encoding="utf-8"))}
    rng = random.Random(SEED)
    chosen = {}
    for rec in records:                       # the rare classes among scored cases first
        if rec["rec"] in scored and rec.get("interaction") in ("synergy", "additive"):
            chosen[rec["rec"]] = rec
    pool = [r for r in records if r["rec"] in scored and r["rec"] not in chosen]
    rng.shuffle(pool)
    for rec in pool[:max(0, 40 - len(chosen))]:
        chosen[rec["rec"]] = rec
    by_class = defaultdict(list)
    for rec in records:
        if rec["rec"] not in chosen:
            by_class[rec.get("interaction")].append(rec)
    for cls, items in by_class.items():
        rng.shuffle(items)
        have = sum(r.get("interaction") == cls for r in chosen.values())
        for rec in items[:max(0, MIN_PER_CLASS - have)]:
            chosen[rec["rec"]] = rec
    rest = [r for items in by_class.values() for r in items if r["rec"] not in chosen]
    rng.shuffle(rest)
    for rec in rest[:max(0, N - len(chosen))]:
        chosen[rec["rec"]] = rec
    rows = []
    for rec in chosen.values():
        ivs = rec["interventions"]
        rows.append({
            "rec": rec["rec"], "pmid": rec["pmid"], "pubmed": f"https://pubmed.ncbi.nlm.nih.gov/{rec['pmid']}/",
            "scored_by_model": int(rec["rec"] in scored),
            "interventions": " + ".join(f"{i.get('agent', '')} [{i.get('action', '')}"
                                        + (f"; target {i['target']}" if i.get("target") else "") + "]" for i in ivs),
            "readout": rec["readout"], "model": rec.get("model", ""), "species": rec.get("species", ""),
            "extracted_direction_combination": rec.get("readout_direction", 0),
            "extracted_singles": json.dumps(rec.get("singles") or []),
            "extracted_interaction": rec.get("interaction", ""), "interaction_basis": rec.get("interaction_basis", ""),
            "magnitude": rec.get("magnitude", ""), "confidence": rec.get("confidence", ""),
            "quote": rec["evidence_quote"], "context": context_around(rec["pmid"], rec["evidence_quote"]),
            **{k: "" for k in EXPERT}})
    rows.sort(key=lambda r: (r["extracted_interaction"], r["pmid"]))
    with open(SHEET, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} records -> {SHEET}")
    print("classes:", dict(Counter(r["extracted_interaction"] for r in rows)),
          "| scored by model:", sum(r["scored_by_model"] for r in rows),
          "| context found:", sum(bool(r["context"]) for r in rows))


def score(sheet=SHEET):
    rows = [r for r in csv.DictReader(open(sheet, encoding="utf-8")) if r["expert_ran_in_paper"].strip()]
    if not rows:
        print("no filled rows")
        return
    yn = lambda v: v.strip().lower() in ("y", "yes", "1", "true")
    n = len(rows)
    ran = [r for r in rows if yn(r["expert_ran_in_paper"])]
    print(f"{n} reviewed; the paper itself ran the experiment in {len(ran)} ({100 * len(ran) / n:.0f}%)")
    for field, label in (("expert_interventions_ok", "interventions correct"), ("expert_readout_ok", "readout correct"),
                         ("expert_in_context", "in rodent nerve-injury context")):
        print(f"  {label}: {sum(yn(r[field]) for r in ran)}/{len(ran)}")
    both = [r for r in ran if r["expert_interaction"].strip()]
    collapse = lambda x: "less" if x in ec.LESS else x
    print(f"  interaction class agrees: {sum(r['expert_interaction'].strip() == r['extracted_interaction'] for r in both)}/{len(both)}; "
          f"on the three coarse classes: {sum(collapse(r['expert_interaction'].strip()) == collapse(r['extracted_interaction']) for r in both)}/{len(both)}")
    for basis in ("stated", "inferred"):
        sub = [r for r in both if r["interaction_basis"] == basis]
        print(f"    {basis}: {sum(r['expert_interaction'].strip() == r['extracted_interaction'] for r in sub)}/{len(sub)}")
    d = [r for r in ran if r["expert_direction_combination"].strip()]
    print(f"  combination direction agrees: {sum(r['expert_direction_combination'].strip() == str(r['extracted_direction_combination']) for r in d)}/{len(d)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if cmd == "score":
        score(Path(sys.argv[2]) if len(sys.argv) > 2 else SHEET)     # e.g. analysis/combinations/adjudication_focused.csv
    else:
        prepare()
