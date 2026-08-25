#!/usr/bin/env python3
"""Extract a validation-ready inventory of scientific claim cards.

Source A (edge claims): every graph_v2.json link with nonzero ``sign`` becomes
a card carrying its original relation string, sign, and confidence. Priority:
P0 for EXTRACTED evidence, P1 otherwise (INFERRED and AMBIGUOUS alike, pending
literature validation). Special review flags: ``kalirin_inferred`` for INFERRED
cards touching a Kalirin-labeled entity, ``nrcam_ngr1_ambiguous`` for the
NrCAM/NgR1 relation pair.

Source B (quantitative statement claims): sentences mined from top-level
dossier Markdown notes that contain a concentration/dose, percentage, fold
change, IC50/EC50/ED50/Ki value, or a timepoint co-occurring with injury/pain/
model/treatment context. Consecutive non-blank lines are joined into paragraph
blocks first so hard-wrapped sentences are quoted whole; typographic hyphens
(U+2010-U+2014) act as separators in fold/timepoint patterns without altering
the verbatim quote text. Identical sentences are deduplicated per file; nothing
is silently truncated above the warning threshold (a warning is recorded).

Inputs are never modified. Extraction is deterministic pure-Python: claim ids
are sequential over a deterministic sort, so identical inputs yield byte-equal
claims.json (index.json differs only by generated_at).
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_GRAPH_PATH = Path("graphify-out/graph_v2.json")
DEFAULT_VAULT_DIR = Path(".")
DEFAULT_OUTPUT_DIR = Path("analysis/claims")

QUANT_WARN_THRESHOLD = 1500
OBJECT_MAX_CHARS = 400

PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
KNOWN_PRIORITIES = ("P0", "P1", "P2", "P3")
KNOWN_KINDS = ("edge", "quantitative")
KNOWN_CONFIDENCES = ("EXTRACTED", "INFERRED", "AMBIGUOUS")

KALIRIN_RE = re.compile(r"kalirin", re.IGNORECASE)
NRCAM_RE = re.compile(r"nrcam", re.IGNORECASE)
NGR1_RE = re.compile(r"ngr[\s-]*1|nogo-66 receptor", re.IGNORECASE)

CONCENTRATION_RE = re.compile(
    r"\d+(?:\.\d+)?\s?(?:mg/kg|ng/mL|µg/mL|μg/mL|ug/mL|mg/mL|µM|μM|uM|mM|nM)\b"
)
PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s?%")
FOLD_CHANGE_RE = re.compile(r"\d+(?:\.\d+)?[\s\u2010-\u2014-]fold")
BINDING_AFFINITY_RE = re.compile(r"\b(?:IC50|EC50|ED50|Ki)\b[^.;]{0,40}?\d+(?:\.\d+)?")
TIMEPOINT_RE = re.compile(r"\b\d+(?:\.\d+)?[\s\u2010-\u2014-]?(?:hours?|hrs?|days?|weeks?|h|d|w)\b")

ALWAYS_QUANT_PATTERNS = (
    CONCENTRATION_RE,
    PERCENT_RE,
    FOLD_CHANGE_RE,
    BINDING_AFFINITY_RE,
)

TIMEPOINT_CONTEXT_RE = re.compile(r"injur|pain|model|treat", re.IGNORECASE)

README_PREFIX = "readme"

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:[#>]+|[-*+]|\d+[.)])\s+")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MARKDOWN_BLOCK_START_RE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|#{1,6}\s|>\s)")

ABBREVIATION_ENDINGS = {
    "al", "eg", "ie", "vs", "cf", "fig", "eq", "eqs", "approx",
    "dr", "no", "nos", "pp", "ed", "eds", "ca", "ref", "seq", "st",
    "ip", "sc", "po", "iv",
}


def iter_dossier_files(vault_dir):
    root = Path(vault_dir)
    return [
        path
        for path in sorted(root.glob("*.md"))
        if not path.name.lower().startswith(README_PREFIX)
    ]


def clean_line(raw):
    line = raw.strip()
    line = MARKDOWN_PREFIX_RE.sub("", line)
    line = MARKDOWN_LINK_RE.sub(r"\1", line)
    line = line.replace("**", "").replace("__", "").replace("`", "")
    return unicodedata.normalize("NFC", line).strip()


def ends_with_abbreviation(fragment):
    tail = fragment.rstrip(")\"'”’]").rstrip(".")
    words = tail.split()
    return bool(words) and words[-1].lower().replace(".", "") in ABBREVIATION_ENDINGS


def split_sentences(line):
    merged = []
    for fragment in SENTENCE_SPLIT_RE.split(line):
        if not fragment:
            continue
        if merged and ends_with_abbreviation(merged[-1]):
            merged[-1] += " " + fragment
        else:
            merged.append(fragment)
    return merged


def iter_paragraphs(text):
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        lines = _skip_frontmatter(lines)
    in_fence = False
    block = []
    for raw in lines:
        if raw.strip().startswith("```"):
            in_fence = not in_fence
            if block:
                yield " ".join(block)
                block = []
            continue
        if in_fence:
            continue
        if block and MARKDOWN_BLOCK_START_RE.match(raw):
            yield " ".join(block)
            block = []
        cleaned = clean_line(raw)
        if not cleaned:
            if block:
                yield " ".join(block)
                block = []
            continue
        block.append(cleaned)
    if block:
        yield " ".join(block)


def iter_sentences(text):
    for paragraph in iter_paragraphs(text):
        yield from split_sentences(paragraph)


def _skip_frontmatter(lines):
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[i + 1:]
    return []


def match_value_tokens(sentence):
    patterns = ALWAYS_QUANT_PATTERNS
    if TIMEPOINT_CONTEXT_RE.search(sentence):
        patterns += (TIMEPOINT_RE,)
    tokens = []
    for pattern in patterns:
        for match in pattern.finditer(sentence):
            token = " ".join(match.group(0).split())
            if token not in tokens:
                tokens.append(token)
    return tokens


def make_quant_claim(subject, source_note, sentence, tokens):
    normalized = " ".join(sentence.split())
    return {
        "kind": "quantitative",
        "subject": subject,
        "predicate": "quantitative_statement",
        "object": normalized[:OBJECT_MAX_CHARS],
        "sign": 0,
        "confidence": "EXTRACTED",
        "source_note": source_note,
        "quote": normalized,
        "citation_status": "UNVERIFIED",
        "priority": "P3",
        "priority_flag": None,
        "theme_hint": None,
        "value_tokens": tokens,
    }


def read_dossier(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"error: {path.name}: {exc}", file=sys.stderr)
        raise


def extract_quant_claims(vault_dir):
    claims = []
    for path in iter_dossier_files(vault_dir):
        seen = set()
        for sentence in iter_sentences(read_dossier(path)):
            tokens = match_value_tokens(sentence)
            if not tokens:
                continue
            key = " ".join(sentence.lower().split())
            if key in seen:
                continue
            seen.add(key)
            claims.append(make_quant_claim(path.stem, path.name, sentence, tokens))
    return claims


def edge_priority_flag(subject, target, confidence):
    if (NRCAM_RE.search(subject) and NGR1_RE.search(target)) or (
        NRCAM_RE.search(target) and NGR1_RE.search(subject)
    ):
        return "nrcam_ngr1_ambiguous"
    if confidence == "INFERRED" and (KALIRIN_RE.search(subject) or KALIRIN_RE.search(target)):
        return "kalirin_inferred"
    return None


def extract_edge_claims(graph):
    labels = {node.get("id"): node.get("label", "") for node in graph.get("nodes", [])}
    claims = []
    for link in graph.get("links", []):
        sign = link.get("sign", 0)
        if sign == 0:
            continue
        confidence = link.get("confidence", "")
        subject = labels.get(link.get("source"), "")
        target = labels.get(link.get("target"), "")
        claims.append({
            "kind": "edge",
            "subject": subject,
            "predicate": link.get("relation", ""),
            "object": target,
            "sign": sign,
            "confidence": confidence,
            "source_note": link.get("source_file"),
            "quote": None,
            "citation_status": "UNVERIFIED",
            "priority": "P0" if confidence == "EXTRACTED" else "P1",
            "priority_flag": edge_priority_flag(subject, target, confidence),
            "theme_hint": None,
        })
    return claims


def edge_id_sort_key(claim):
    return (
        claim["priority"],
        claim["subject"],
        claim["predicate"],
        claim["object"],
        claim["source_note"] or "",
    )


def extract_all(graph, vault_dir):
    quant_claims = extract_quant_claims(vault_dir)
    numbered = [
        {"id": f"EC-{i:04d}", **claim}
        for i, claim in enumerate(sorted(extract_edge_claims(graph), key=edge_id_sort_key), 1)
    ]
    numbered += [
        {"id": f"QC-{i:04d}", **claim}
        for i, claim in enumerate(quant_claims, 1)
    ]
    return sorted(numbered, key=lambda claim: (PRIORITY_RANK[claim["priority"]], claim["id"]))


def count_by(claims, field, known_values):
    return {value: sum(1 for claim in claims if claim[field] == value) for value in known_values}


def summarize(claims):
    index = {
        "counts_by_priority": count_by(claims, "priority", KNOWN_PRIORITIES),
        "counts_by_kind": count_by(claims, "kind", KNOWN_KINDS),
        "counts_by_confidence": count_by(claims, "confidence", KNOWN_CONFIDENCES),
        "kalirin_inferred_count": sum(
            1 for claim in claims if claim.get("priority_flag") == "kalirin_inferred"
        ),
        "nrcam_ngr1_flag_count": sum(
            1 for claim in claims if claim.get("priority_flag") == "nrcam_ngr1_ambiguous"
        ),
        "quantitative_statement_count": sum(
            1 for claim in claims if claim["kind"] == "quantitative"
        ),
    }
    quant_total = index["quantitative_statement_count"]
    if quant_total > QUANT_WARN_THRESHOLD:
        index["warnings"] = [
            f"quantitative statements ({quant_total}) exceed warning threshold "
            f"({QUANT_WARN_THRESHOLD}); all kept, none truncated"
        ]
    return index


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--vault-dir", type=Path, default=DEFAULT_VAULT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    claims = extract_all(graph, args.vault_dir)
    index = summarize(claims)
    index["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index["input_sha256"] = sha256_file(args.graph)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    claims_path = args.output_dir / "claims.json"
    index_path = args.output_dir / "index.json"
    write_json(claims_path, claims)
    write_json(index_path, index)

    kinds = index["counts_by_kind"]
    priorities = index["counts_by_priority"]
    print(f"claims: {len(claims)} total (edges {kinds['edge']}, quantitative {kinds['quantitative']})")
    print(f"priorities: {priorities}")
    print(
        f"review flags: kalirin_inferred={index['kalirin_inferred_count']}, "
        f"nrcam_ngr1_ambiguous={index['nrcam_ngr1_flag_count']}"
    )
    for warning in index.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    print(f"wrote {claims_path} and {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
