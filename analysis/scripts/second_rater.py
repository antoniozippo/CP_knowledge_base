#!/usr/bin/env python3
"""A local AI model as a second rater of the combination records (phase 4, step 1).

Reads analysis/combinations/adjudication_sample.csv and asks a model served with an OpenAI-compatible
API (llama.cpp server, vLLM, LM Studio, Ollama's /v1, ...) to fill the same fields the human expert
fills (ADJUDICATION.md). The model sees the interventions, readout, quote and surrounding text but NOT
the extracted directions or interaction class, so its answers are not anchored on them. Answers go to
analysis/combinations/adjudication_second_rater.csv; the human sheet is never touched.

  python3 analysis/scripts/second_rater.py --endpoint http://192.168.1.87:8888 [--model NAME] [--limit 5]
  python3 analysis/scripts/second_rater.py --score

Only the standard library is used, so it runs on any machine with Python 3.9+ and this checkout.
Rows already answered are skipped, so it can be stopped and restarted.
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "analysis" / "combinations" / "adjudication_sample.csv"
OUT = ROOT / "analysis" / "combinations" / "adjudication_second_rater.csv"
FIELDS = ["ran_in_paper", "interventions_ok", "readout_ok", "direction_combination", "direction_a",
          "direction_b", "interaction", "in_context"]
INTERACTIONS = ("synergy", "additive", "sub_additive", "no_added_effect", "occlusion", "antagonism", "unclear")
LESS = {"occlusion", "antagonism", "no_added_effect", "sub_additive"}

SYSTEM = """You are an expert in preclinical pain research checking records extracted from papers.
For one record you get the interventions given together, the readout, a verbatim quote from the paper
and the text around it. Judge only from that text. Answer with one JSON object and nothing else:
{
 "ran_in_paper": true or false (the paper itself ran this combination and reports a result; false for
   background, methods, another group's work or a hypothesis),
 "interventions_ok": true or false (the listed interventions, actions and targets are right and were
   given together),
 "readout_ok": true or false (the readout is the one the quote reports),
 "direction_combination": 1, -1 or 0 (how the named readout moved with the combination against the
   injured untreated control; a threshold that rose is 1),
 "direction_a": 1, -1 or 0 (the first intervention alone; 0 if not reported),
 "direction_b": 1, -1 or 0 (the second intervention alone; 0 if not reported),
 "interaction": one of "synergy" (more than the sum), "additive", "sub_additive" (more than either
   alone, less than the sum), "no_added_effect" (no more than the stronger one), "occlusion" (one
   intervention abolishes the other's effect, e.g. no effect in knockouts), "antagonism" (the
   combination does less than one alone), "unclear",
 "in_context": true or false (in vivo, rodent, nerve-injury model),
 "reason": one short sentence
}"""


def post(url, payload, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def pick_model(endpoint):
    for path in ("/v1/models", "/api/tags"):
        try:
            data = get(endpoint + path)
        except (urllib.error.URLError, ValueError, OSError):
            continue
        items = data.get("data") or data.get("models") or []
        if items:
            return items[0].get("id") or items[0].get("name")
    return None


def ask(endpoint, model, user, timeout, max_tokens=4000):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    try:
        data = post(endpoint + "/v1/chat/completions",
                    {"model": model, "messages": msgs, "temperature": 0, "max_tokens": max_tokens}, timeout)
        msg = data["choices"][0]["message"]
        # some servers put a reasoning model's thinking (and sometimes the answer) in a separate field
        return (msg.get("content") or "") + "\n" + (msg.get("reasoning_content") or msg.get("reasoning") or "")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    data = post(endpoint + "/api/chat", {"model": model, "messages": msgs, "stream": False,
                                         "options": {"temperature": 0}}, timeout)        # Ollama
    return data["message"]["content"]


def parse(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)       # reasoning models
    text = re.sub(r"```(?:json)?", "", text)
    d = None
    # the last JSON object in the reply that holds an "interaction" key (thinking may contain others)
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text, re.S))):
        try:
            cand = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(cand, dict) and ("interaction" in cand or "ran_in_paper" in cand):
            d = cand
            break
    if d is None:
        return None
    out = {}
    for k in ("ran_in_paper", "interventions_ok", "readout_ok", "in_context"):
        v = d.get(k)
        out[k] = "y" if v is True or str(v).lower() in ("true", "y", "yes") else "n" if v is not None else ""
    for k in ("direction_combination", "direction_a", "direction_b"):
        try:
            out[k] = str(max(-1, min(1, int(d.get(k)))))
        except (TypeError, ValueError):
            out[k] = ""
    i = str(d.get("interaction", "")).strip().lower()
    out["interaction"] = i if i in INTERACTIONS else ""
    out["reason"] = str(d.get("reason", ""))[:300]
    return out


def prompt_for(row):
    return (f"Interventions (in order A, B, ...): {row['interventions']}\nReadout: {row['readout']}\n"
            f"Model/species as extracted: {row['model']} / {row['species']}\nPubMed: {row['pubmed']}\n\n"
            f"Quote:\n{row['quote']}\n\nText around the quote:\n{row['context']}")


def run(args):
    endpoint = args.endpoint.rstrip("/")
    model = args.model or pick_model(endpoint)
    if not model:
        sys.exit(f"no model found at {endpoint} (tried /v1/models and /api/tags); pass --model")
    rows = list(csv.DictReader(open(SHEET, encoding="utf-8")))
    done = {}
    if OUT.exists():
        done = {r["rec"]: r for r in csv.DictReader(open(OUT, encoding="utf-8")) if r.get("interaction") or r.get("ran_in_paper")}
    cols = ["rec", "pmid", "rater", *FIELDS, "reason", "error"]
    todo = [r for r in rows if r["rec"] not in done][: args.limit or None]
    print(f"model {model}; {len(done)} done, {len(todo)} to ask")
    results = dict(done)
    for i, row in enumerate(todo, 1):
        rec = {"rec": row["rec"], "pmid": row["pmid"], "rater": model, "error": ""}
        for attempt in range(2):
            try:
                raw = ask(endpoint, model, prompt_for(row), args.timeout, args.max_tokens)
                parsed = parse(raw)
                if parsed:
                    rec.update(parsed)
                    rec["error"] = ""
                    break
                rec["error"] = "unparsable answer"
                if args.debug or i == 1:
                    print("---- raw reply (first 1500 characters) ----\n" + raw[:1500] + "\n----")
            except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
                rec["error"] = str(exc)[:200]
                time.sleep(2)
        results[row["rec"]] = rec
        print(f"[{i}/{len(todo)}] {row['rec']}: {rec.get('interaction') or rec['error']}")
        with open(OUT, "w", newline="", encoding="utf-8") as fh:      # written after every row: safe to stop
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(results[r["rec"]] for r in rows if r["rec"] in results)


def score():
    sheet = {r["rec"]: r for r in csv.DictReader(open(SHEET, encoding="utf-8"))}
    ai = [r for r in csv.DictReader(open(OUT, encoding="utf-8")) if r.get("interaction") or r.get("ran_in_paper")]
    coarse = lambda x: "less than additive" if x in LESS else x
    print(f"second rater answered {len(ai)} of {len(sheet)} rows")
    ran = [r for r in ai if r["ran_in_paper"] == "y"]
    print(f"  says the paper ran the experiment: {len(ran)}/{len(ai)}; in context: "
          f"{sum(r['in_context'] == 'y' for r in ran)}/{len(ran)}; interventions ok: "
          f"{sum(r['interventions_ok'] == 'y' for r in ran)}/{len(ran)}; readout ok: {sum(r['readout_ok'] == 'y' for r in ran)}/{len(ran)}")
    pairs = [(r, sheet[r["rec"]]) for r in ran if r["interaction"]]
    ex = sum(a["interaction"] == s["extracted_interaction"] for a, s in pairs)
    co = sum(coarse(a["interaction"]) == coarse(s["extracted_interaction"]) for a, s in pairs)
    print(f"  vs extraction, interaction: exact {ex}/{len(pairs)}, coarse {co}/{len(pairs)}")
    d = [(a, s) for a, s in pairs if a["direction_combination"] != ""]
    print(f"  vs extraction, combination direction: {sum(a['direction_combination'] == str(s['extracted_direction_combination']) for a, s in d)}/{len(d)}")
    from collections import Counter
    print("  second rater's classes:", dict(Counter(a["interaction"] for a, _ in pairs)))
    human = [(a, sheet[a["rec"]]) for a in ai if sheet[a["rec"]].get("expert_interaction", "").strip()]
    if human:
        k = sum(a["interaction"] == s["expert_interaction"].strip() for a, s in human)
        print(f"  vs human expert, interaction: {k}/{len(human)}")
    else:
        print("  no human answers yet: agreement between the two raters is computed once the expert sheet is filled")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--endpoint", default="http://192.168.1.87:8888")
    p.add_argument("--model", default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--max-tokens", type=int, default=4000, help="room for a reasoning model's thinking")
    p.add_argument("--debug", action="store_true", help="print every unparsable reply")
    p.add_argument("--score", action="store_true")
    a = p.parse_args()
    score() if a.score else run(a)
