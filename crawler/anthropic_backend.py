# crawler/anthropic_backend.py - Claude API extraction: synchronous calls and Message Batches
#
# Both paths produce the same raw extraction dicts as the OpenAI-compatible
# path and store them in the extractor cache (extract_{pmid}_{hash}.json), so
# run.py consumes them as ordinary cache hits: quote verification, matching
# and the graph update are unchanged.
#
# Full runs use the Batches API (crawler/batch_extract.py): 50% of standard
# price and no wall-clock cost in the session.
#
# Credentials: CRAWLER_ANTHROPIC_API_KEY, deliberately not ANTHROPIC_API_KEY.
# Claude Code sessions export ANTHROPIC_BASE_URL (and may read
# ANTHROPIC_API_KEY) for their own use; a bare anthropic.Anthropic() would
# inherit them, so the client is built with an explicit key and base URL.

import hashlib
import json
import logging
import os
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from crawler.extractor import (
    MAX_CONTENT_CHARS,
    LLMExtractor,
    _SYSTEM_PROMPT,
    parse_json_object,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"  # the model's own default, stated explicitly
MAX_TOKENS = 16000  # non-streaming ceiling; thinking counts toward it
FALLBACK_BETA = "server-side-fallback-2026-07-01"
API_KEY_ENV = "CRAWLER_ANTHROPIC_API_KEY"
BASE_URL_ENV = "CRAWLER_ANTHROPIC_BASE_URL"
DEFAULT_BASE_URL = "https://api.anthropic.com"


def make_client() -> anthropic.Anthropic:
    """Claude API client from the crawler's own variables (see header)."""
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            f"{API_KEY_ENV} is not set; add it as an environment secret for the crawler"
        )
    return anthropic.Anthropic(
        api_key=api_key, base_url=os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL)
    )

ENTITY_TYPES = ["molecule", "receptor", "channel", "drug", "cell_type", "pathway",
                "process", "structure", "symptom", "concept"]
COMPARTMENTS = ["DRG", "dorsal_horn", "ACC", "barrier", "peripheral", "systemic", "other"]
PREDICATES = ["activates", "inhibits", "upregulates", "downregulates", "phosphorylates",
              "dephosphorylates", "binds", "expresses", "releases", "degrades", "recruits",
              "activates_pathway", "inhibits_pathway", "causes", "prevents", "modulates",
              "interacts_with"]


def _strings():
    return {"type": "array", "items": {"type": "string"}}


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


# Mirrors extractor.ExtractionResult; the API guarantees the reply matches it.
EXTRACTION_SCHEMA = _object({
    "entities": {"type": "array", "items": _object({
        "name": {"type": "string"},
        "entity_type": {"type": "string", "enum": ENTITY_TYPES},
        "aliases": _strings(),
        "compartment": {"type": "string", "enum": COMPARTMENTS},
        "mentions": {"type": "integer"},
    })},
    "relationships": {"type": "array", "items": _object({
        "subject": {"type": "string"},
        "predicate": {"type": "string", "enum": PREDICATES},
        "object": {"type": "string"},
        "sign": {"type": "integer"},
        "evidence_quote": {"type": "string"},
        "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
    })},
    "key_findings": _strings(),
    "novel_terms": _strings(),
})


def message_params(prompt: str, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT) -> dict:
    """Messages API parameters for one extraction prompt."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {
            "effort": effort,
            "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
        },
    }


def reply_json(message) -> dict | None:
    """The extraction dict from a Message, or None for a refusal / truncation."""
    if message.stop_reason == "refusal":
        category = getattr(getattr(message, "stop_details", None), "category", None)
        logger.warning("Extraction declined (refusal, category=%s)", category)
        return None
    if message.stop_reason == "max_tokens":
        logger.warning("Extraction truncated at max_tokens=%d", MAX_TOKENS)
        return None
    text = next((b.text for b in message.content if b.type == "text"), "")
    return parse_json_object(text)


class AnthropicExtractor(LLMExtractor):
    """LLMExtractor whose model call goes to the Claude API.

    Synchronous, for small runs (--theme, a few hundred papers). Refused
    requests are re-run server-side on Anthropic's recommended fallback
    model (fallbacks="default").
    """

    def __init__(self, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT,
                 cache_dir: Path | None = None, client: anthropic.Anthropic | None = None):
        super().__init__(endpoint="https://api.anthropic.com", model=model, cache_dir=cache_dir)
        self.effort = effort
        self.client = client or make_client()

    def _call_llm(self, prompt: str) -> dict | None:
        try:
            message = self.client.beta.messages.create(
                **message_params(prompt, self.model, self.effort),
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.APIStatusError as exc:
            logger.error("Claude API error %s: %s", exc.status_code, exc.message)
            return None
        except anthropic.APIConnectionError as exc:
            logger.error("Claude API connection error: %s", exc)
            return None
        return reply_json(message)


# ---------------------------------------------------------------------------
# Message Batches
# ---------------------------------------------------------------------------

def prepare_batch_items(focused: list[tuple[dict, list[str]]], cache_dir: Path) -> list[dict]:
    """Batch items for papers without a cached extraction.

    Applies the same truncation and content hash as LLMExtractor.extract,
    so collected results land where run.py looks them up.
    """
    builder = LLMExtractor(cache_dir=cache_dir)
    items = []
    for paper, focus in focused:
        content = paper["content"]
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS] + "\n\n[... truncated for LLM context ...]"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        if builder._check_cache(paper["pmid"], content_hash) is not None:
            continue
        items.append({
            "custom_id": f"{paper['pmid']}_{content_hash}",
            "pmid": paper["pmid"],
            "title": paper["title"],
            "content_hash": content_hash,
            "prompt": builder._build_prompt(content, paper["pmid"], paper["title"], focus),
        })
    return items


def submit_batch(items: list[dict], model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT,
                 client: anthropic.Anthropic | None = None):
    """Create one Message Batch for the items; returns the batch object."""
    client = client or make_client()
    requests = [
        Request(custom_id=item["custom_id"],
                params=MessageCreateParamsNonStreaming(**message_params(item["prompt"], model, effort)))
        for item in items
    ]
    return client.messages.batches.create(requests=requests)


def collect_batch(batch_id: str, manifest: dict, cache_dir: Path,
                  client: anthropic.Anthropic | None = None) -> dict:
    """Write each succeeded result to the extractor cache; returns counts.

    manifest maps custom_id -> {pmid, title, content_hash}. Errored or
    expired requests are counted, not cached, so a later submit retries them.
    """
    client = client or make_client()
    cache = LLMExtractor(cache_dir=cache_dir)
    counts = {"cached": 0, "unparsable": 0, "errored": 0, "canceled": 0, "expired": 0}
    for result in client.messages.batches.results(batch_id):
        kind = result.result.type
        if kind != "succeeded":
            counts[kind] = counts.get(kind, 0) + 1
            continue
        entry = manifest.get(result.custom_id)
        raw = reply_json(result.result.message) if entry else None
        if raw is None:
            counts["unparsable"] += 1
            continue
        raw.setdefault("pmid", entry["pmid"])
        raw.setdefault("title", entry["title"])
        cache._save_cache(entry["pmid"], entry["content_hash"], raw)
        counts["cached"] += 1
    return counts


def write_manifest(path: Path, batch_id: str, items: list[dict], model: str, effort: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "batch_id": batch_id, "model": model, "effort": effort,
        "requests": {i["custom_id"]: {k: i[k] for k in ("pmid", "title", "content_hash")}
                     for i in items},
    }, indent=2))
