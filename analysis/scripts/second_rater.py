#!/usr/bin/env python3
"""A local AI model as a second rater of the combination records (phase 4, step 1).

Reads analysis/combinations/adjudication_sample.csv and asks a model served with an OpenAI-compatible
API (LM Studio by default, on port 1234; also llama.cpp, vLLM, Ollama) to fill the same fields the human expert
fills (ADJUDICATION.md). The model sees the interventions, readout, quote and surrounding text but NOT
the extracted directions or interaction class, so its answers are not anchored on them. Answers go to
analysis/combinations/adjudication_second_rater.csv; the human sheet is never touched.

  python3 analysis/scripts/second_rater.py --endpoint http://192.168.1.87:1234 [--model NAME] [--limit 5]
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
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "analysis" / "combinations" / "adjudication_sample.csv"
OUT = ROOT / "analysis" / "combinations" / "adjudication_second_rater.csv"
FOCUSED = ROOT / "analysis" / "combinations" / "adjudication_focused.csv"
FOCUSED_OUT = ROOT / "analysis" / "combinations" / "adjudication_focused_rater.csv"
# v2 (2026-11-28) adds the sentence on "better than either alone", the main disagreement of the v1 run
PROMPT_VERSION = 2
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
   combination does less than one alone), "unclear". A combination that is better than either
   intervention alone is "synergy" only when its effect exceeds the SUM of the two single effects (or
   the paper shows synergy, e.g. by isobologram); better than either but not more than the sum is
   "sub_additive"; when the single effects are not reported well enough to tell, "unclear".
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
    # LM Studio: /api/v0/models says which model is loaded; /v1/models lists every downloaded one
    try:
        items = get(endpoint + "/api/v0/models").get("data") or []
        loaded = [m["id"] for m in items if m.get("state") == "loaded" and m.get("type") in ("llm", "vlm", None)]
        if loaded:
            return loaded[0]
    except (urllib.error.URLError, ValueError, OSError, KeyError):
        pass
    for path in ("/v1/models", "/api/tags"):
        try:
            data = get(endpoint + path)
        except (urllib.error.URLError, ValueError, OSError):
            continue
        names = [m.get("id") or m.get("name") for m in data.get("data") or data.get("models") or []]
        names = [n for n in names if n and "embed" not in n.lower()]          # not an embedding model
        if names:
            return names[0]
    return None


SCHEMA = {
    "name": "rating", "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "ran_in_paper": {"type": "boolean"}, "interventions_ok": {"type": "boolean"},
            "readout_ok": {"type": "boolean"},
            "direction_combination": {"type": "integer", "enum": [-1, 0, 1]},
            "direction_a": {"type": "integer", "enum": [-1, 0, 1]},
            "direction_b": {"type": "integer", "enum": [-1, 0, 1]},
            "interaction": {"type": "string", "enum": list(INTERACTIONS)},
            "in_context": {"type": "boolean"}, "reason": {"type": "string"},
        },
        "required": ["ran_in_paper", "interventions_ok", "readout_ok", "direction_combination", "direction_a",
                     "direction_b", "interaction", "in_context", "reason"],
    },
}
FOLLOW_UP = "Stop reasoning. Reply now with only the final JSON object, nothing else."


class Asker:
    """One chat call per question. Tries JSON-schema output (LM Studio, vLLM, llama.cpp) and drops it
    if the server refuses; appends /no_think (Qwen) unless thinking is wanted; and when a reply ends
    without a JSON object, asks once more for only the JSON, with the reply so far as context."""

    def __init__(self, endpoint, model, timeout, max_tokens, think=False):
        self.endpoint, self.model, self.timeout, self.max_tokens, self.think = endpoint, model, timeout, max_tokens, think
        self.schema_ok = True
        self.last_finish = ""

    def chat(self, msgs, max_tokens):
        payload = {"model": self.model, "messages": msgs, "temperature": 0, "max_tokens": max_tokens}
        if self.schema_ok:
            payload["response_format"] = {"type": "json_schema", "json_schema": SCHEMA}
        try:
            data = post(self.endpoint + "/v1/chat/completions", payload, self.timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                data = post(self.endpoint + "/api/chat", {"model": self.model, "messages": msgs, "stream": False,
                                                          "format": "json", "options": {"temperature": 0}}, self.timeout)
                self.last_finish = data.get("done_reason", "")
                return data["message"]["content"]
            if self.schema_ok and exc.code in (400, 422, 500):
                self.schema_ok = False               # this server does not take response_format
                return self.chat(msgs, max_tokens)
            raise
        choice = data["choices"][0]
        self.last_finish = choice.get("finish_reason") or ""
        msg = choice["message"]
        # some servers put a reasoning model's thinking (and sometimes the answer) in a separate field
        return (msg.get("content") or "") + "\n" + (msg.get("reasoning_content") or msg.get("reasoning") or "")

    def __call__(self, user):
        suffix = "" if self.think else " /no_think"
        msgs = [{"role": "system", "content": SYSTEM + suffix}, {"role": "user", "content": user + suffix}]
        raw = self.chat(msgs, self.max_tokens)
        if parse(raw):
            return raw
        tail = raw[-6000:]
        again = self.chat(msgs + [{"role": "assistant", "content": tail}, {"role": "user", "content": FOLLOW_UP + suffix}], 800)
        return raw + "\n" + again


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
    sheet_path, out_path = Path(args.sheet), Path(args.out)
    rows = list(csv.DictReader(open(sheet_path, encoding="utf-8")))
    done = {}
    if out_path.exists():
        done = {r["rec"]: r for r in csv.DictReader(open(out_path, encoding="utf-8")) if r.get("interaction") or r.get("ran_in_paper")}
    cols = ["rec", "pmid", "rater", *FIELDS, "reason", "error"]
    todo = [r for r in rows if r["rec"] not in done][: args.limit or None]
    asker = Asker(endpoint, model, args.timeout, args.max_tokens, args.think)
    print(f"model {model}; {len(done)} done, {len(todo)} to ask")
    results = dict(done)
    for i, row in enumerate(todo, 1):
        rec = {"rec": row["rec"], "pmid": row["pmid"], "rater": f"{model} (prompt v{PROMPT_VERSION}, thinking {'on' if args.think else 'off'})", "error": ""}
        for attempt in range(2):
            try:
                raw = asker(prompt_for(row))
                parsed = parse(raw)
                if parsed:
                    rec.update(parsed)
                    rec["error"] = ""
                    if attempt or i == 1:
                        print(f"  (schema output {'on' if asker.schema_ok else 'off'}; finish reason '{asker.last_finish}')")
                    break
                rec["error"] = "unparsable answer"
                if args.debug or i == 1:
                    print(f"---- unparsable reply: {len(raw)} characters, finish reason "
                          f"'{asker.last_finish}'; last 1500 characters ----\n" + raw[-1500:] + "\n----")
            except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
                rec["error"] = str(exc)[:200]
                time.sleep(2)
        results[row["rec"]] = rec
        print(f"[{i}/{len(todo)}] {row['rec']}: {rec.get('interaction') or rec['error']}")
        with open(out_path, "w", newline="", encoding="utf-8") as fh:      # written after every row: safe to stop
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(results[r["rec"]] for r in rows if r["rec"] in results)


def score(sheet_path=SHEET, out_path=OUT):
    sheet = {r["rec"]: r for r in csv.DictReader(open(sheet_path, encoding="utf-8"))}
    ai = [r for r in csv.DictReader(open(out_path, encoding="utf-8")) if r.get("interaction") or r.get("ran_in_paper")]
    print(f"rater: {ai[0]['rater'] if ai else '-'}")
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
    print("  second rater's classes:", dict(Counter(a["interaction"] for a, _ in pairs)))
    if out_path != OUT and OUT.exists():
        first = {r["rec"]: r for r in csv.DictReader(open(OUT, encoding="utf-8"))}
        both = [(a, first[a["rec"]]) for a in ai if a["rec"] in first and a["interaction"]]
        changed = [(a, f) for a, f in both if a["interaction"] != f["interaction"]]
        print(f"  vs the first run (prompt v1, thinking off): same class on {len(both) - len(changed)}/{len(both)}; "
              f"changes: {dict(Counter((f['interaction'], a['interaction']) for a, f in changed).most_common(8))}")
        print(f"  says the paper did NOT run it: {sum(a['ran_in_paper'] == 'n' for a in ai)} (first run: "
              f"{sum(first[a['rec']]['ran_in_paper'] == 'n' for a in ai if a['rec'] in first)})")
    human = [(a, sheet[a["rec"]]) for a in ai if sheet[a["rec"]].get("expert_interaction", "").strip()]
    if human:
        k = sum(a["interaction"] == s["expert_interaction"].strip() for a, s in human)
        print(f"  vs human expert, interaction: {k}/{len(human)}")
    else:
        print("  no human answers yet: agreement between the two raters is computed once the expert sheet is filled")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--endpoint", default="http://192.168.1.87:1234")
    p.add_argument("--model", default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--max-tokens", type=int, default=4000, help="room for a reasoning model's thinking")
    p.add_argument("--debug", action="store_true", help="print every unparsable reply")
    p.add_argument("--think", action="store_true", help="let the model think (slower); by default /no_think is sent")
    p.add_argument("--score", action="store_true")
    p.add_argument("--sheet", default=str(SHEET))
    p.add_argument("--out", default=str(OUT))
    p.add_argument("--focused", action="store_true",
                   help="the 60-row focused sheet, thinking on, larger budget, answers in adjudication_focused_rater.csv")
    a = p.parse_args()
    if a.focused:
        a.sheet, a.out, a.think = str(FOCUSED), str(FOCUSED_OUT), True
        a.max_tokens = max(a.max_tokens, 16000)
        a.timeout = max(a.timeout, 1800)
    score(Path(a.sheet), Path(a.out)) if a.score else run(a)
