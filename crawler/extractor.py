# crawler/extractor.py - LLM entity/relationship extraction

import json
import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# One content budget for every paper (the old 8k/30k split cut a 29k paper
# to 8k while keeping 30k of a 31k one). ~6k tokens of paper text.
MAX_CONTENT_CHARS = 24000
LLM_TIMEOUT_S = 300

# Predicates whose direction is fixed by the verb; the LLM-reported sign is
# overridden by these. The rest (binds, modulates, ...) keep the LLM sign.
PREDICATE_SIGN = {
    "activates": 1, "upregulates": 1, "releases": 1, "recruits": 1,
    "activates_pathway": 1, "causes": 1,
    "inhibits": -1, "downregulates": -1, "degrades": -1,
    "inhibits_pathway": -1, "prevents": -1,
}

_THINK_RE = re.compile(r"<(think|thought)>.*?</\1>", re.DOTALL | re.IGNORECASE)
_QUOTE_NORM_RE = re.compile(r"[\W_]+")
# inline markup PubMed leaves in some abstracts ("CD8<sup>+</sup>", "<i>P</i>")
_TAG_RE = re.compile(r"</?[A-Za-z][^<>]{0,40}>")


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str = "molecule"
    aliases: list[str] = Field(default_factory=list)
    compartment: str = "other"
    mentions: int = 1


class ExtractedRelationship(BaseModel):
    subject: str
    predicate: str
    object: str
    sign: int = 0
    evidence_quote: str
    confidence: str = "MEDIUM"
    pmid: str = ""


class ExtractionResult(BaseModel):
    pmid: str
    title: str
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    novel_terms: list[str] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You are a biomedical entity and relationship extractor. Your task is to extract \
biological entities and regulatory relationships from PubMed paper content.

ENTITY TYPES (use exactly these):
- molecule: proteins, genes, chemicals, drugs, metabolites
- receptor: cell surface or intracellular receptors
- channel: ion channels, transporters
- drug: pharmacological agents, inhibitors, agonists, antagonists
- cell_type: immune cells, neurons, glia, etc.
- pathway: signaling cascades, metabolic pathways
- process: biological processes (e.g., apoptosis, inflammation)
- structure: anatomical or subcellular structures
- symptom: clinical signs, pain phenotypes
- concept: abstract biological concepts

COMPARTMENTS (use exactly these):
- DRG: dorsal root ganglion
- dorsal_horn: spinal dorsal horn
- ACC: anterior cingulate cortex
- barrier: blood-brain or blood-spinal cord barrier
- peripheral: peripheral nervous system
- systemic: whole-body or systemic
- other: unmatched or unclear

RELATIONSHIPS:
- subject is the entity that ACTS; object is the entity acted upon. Write
  "TNF-alpha downregulates KCC2", never "KCC2 is downregulated by TNF-alpha"
  as KCC2 -> TNF-alpha.
- sign: +1 if more subject means more/activated object; -1 if more subject
  means less/inhibited object; 0 for binding, association or unclear direction.
- Only relationships the paper itself reports (its own results or clearly
  stated established facts), not speculation.
- evidence_quote: copy one sentence or clause VERBATIM from the Content
  (exact words, no paraphrase). Relationships whose quote is not found in the
  Content are discarded.

OUTPUT ONLY valid JSON. No markdown fences, no commentary.
"""

_USER_PROMPT_TEMPLATE = """\
Extract biological entities and regulatory relationships from this PubMed paper.

{focus_line}

Paper PMID: {pmid}
Title: {title}

Content:
{content}

Return a JSON object with exactly this structure:
{{
  "entities": [
    {{
      "name": "string",
      "entity_type": "molecule|receptor|channel|drug|cell_type|pathway|process|structure|symptom|concept",
      "aliases": ["string"],
      "compartment": "DRG|dorsal_horn|ACC|barrier|peripheral|systemic|other",
      "mentions": 1
    }}
  ],
  "relationships": [
    {{
      "subject": "entity_name",
      "predicate": "activates|inhibits|upregulates|downregulates|phosphorylates|dephosphorylates|binds|expresses|releases|degrades|recruits|activates_pathway|inhibits_pathway|causes|prevents|modulates|interacts_with",
      "object": "entity_name",
      "sign": 0,
      "evidence_quote": "relevant quote from text",
      "confidence": "HIGH|MEDIUM|LOW"
    }}
  ],
  "key_findings": ["string"],
  "novel_terms": ["string"]
}}
"""


class LLMExtractor:
    """Extract entities and relationships from paper content via LLM."""

    def __init__(
        self,
        endpoint: str = "http://192.168.1.13:1234",
        model: str = "qwen/qwen3.8-27b",
        max_tokens: int = 4096,
        cache_dir: Optional[Path] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.cache_dir = cache_dir or Path("crawler/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.call_count = 0
        # cache_only: never call the model; a cache miss raises like an
        # exhausted budget (run.py defers the paper)
        self.cache_only = False
        # committed extractions written by Claude Code sessions
        # (crawler/agent_extract.py), one <pmid>.json per paper; used when the
        # hash-keyed cache has no entry for this exact content
        self.extractions_dir: Optional[Path] = None
        self.dropped_unverified = 0
        self.sign_overridden = 0

    def _build_prompt(self, content: str, pmid: str, title: str,
                      theme_entities: list[str] | None = None) -> str:
        """Build the user prompt, injecting theme context."""
        if theme_entities:
            focus_line = (
                "Focus especially on entities relevant to these theme targets: "
                + ", ".join(theme_entities)
                + "."
            )
        else:
            focus_line = ""

        return _USER_PROMPT_TEMPLATE.format(
            focus_line=focus_line,
            pmid=pmid,
            title=title,
            content=content,
        )

    def _call_llm(self, prompt: str) -> dict | None:
        """Call the LLM via OpenAI-compatible /v1/chat/completions endpoint."""
        url = f"{self.endpoint}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0,
        }
        try:
            resp = requests.post(url, json=payload, timeout=LLM_TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("LLM request failed: %s", exc)
            return None

        try:
            raw_text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            logger.error("Unexpected LLM response structure: %s", json.dumps(data)[:500])
            return None

        parsed = parse_json_object(raw_text or "")
        if parsed is None:
            logger.error("Failed to parse LLM JSON output (first 500 chars): %s",
                         (raw_text or "")[:500])
        return parsed

    def _check_cache(self, pmid: str, content_hash: str) -> Optional[dict]:
        """Check if a cached extraction exists for this PMID + content hash."""
        cache_path = self.cache_dir / f"extract_{pmid}_{content_hash}.json"
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Cache read failed for %s: %s", cache_path, exc)
        if self.extractions_dir is not None:
            # keyed by PMID only: the paper text fetched here can differ
            # slightly from the worker's, so quotes are re-verified against it
            committed = self.extractions_dir / f"{pmid}.json"
            if committed.exists():
                try:
                    return json.loads(committed.read_text())
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Extraction file unreadable %s: %s", committed, exc)
        return None

    def _save_cache(self, pmid: str, content_hash: str, result: dict):
        """Persist extraction result to cache."""
        cache_path = self.cache_dir / f"extract_{pmid}_{content_hash}.json"
        try:
            cache_path.write_text(json.dumps(result, indent=2))
        except OSError as exc:
            logger.warning("Cache write failed for %s: %s", cache_path, exc)

    def _validate_result(self, raw: dict) -> ExtractionResult | None:
        """Validate and coerce raw LLM dict into ExtractionResult."""
        try:
            result = ExtractionResult(
                pmid=raw.get("pmid", ""),
                title=raw.get("title", ""),
                entities=[
                    ExtractedEntity(**e) for e in raw.get("entities", [])
                ],
                relationships=[
                    ExtractedRelationship(**r) for r in raw.get("relationships", [])
                ],
                key_findings=raw.get("key_findings", []),
                novel_terms=raw.get("novel_terms", []),
            )
            return result
        except Exception as exc:
            logger.error("Validation failed: %s", exc)
            return None

    def extract(
        self,
        pmid: str,
        title: str,
        content: str,
        theme_entities: list[str] | None = None,
        max_budget: int = 0,
    ) -> ExtractionResult | None:
        """Extract entities and relationships from paper content.

        Args:
            pmid: PubMed ID.
            title: Paper title.
            content: Full text or abstract, best sections first.
            theme_entities: Optional list of theme-relevant entity names.
            max_budget: If >0, raise RuntimeError when a real LLM call would
                exceed it (cache hits are free).

        Returns:
            ExtractionResult (after verify_relationships) or None on failure.
        """
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS] + "\n\n[... truncated for LLM context ...]"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]

        cached = self._check_cache(pmid, content_hash)
        if cached is not None:
            logger.debug("Cache hit for PMID %s", pmid)
            validated = self._validate_result(cached)
            if validated is not None:
                return self._verified(validated, content)
            logger.warning("Cached result invalid for PMID %s, re-extracting", pmid)

        if self.cache_only:
            raise RuntimeError(f"no cached extraction for PMID {pmid} (cache-only run)")
        if max_budget > 0 and self.call_count >= max_budget:
            raise RuntimeError(
                f"LLM budget exhausted ({self.call_count}/{max_budget} calls)"
            )
        prompt = self._build_prompt(content, pmid, title, theme_entities)
        self.call_count += 1
        raw = self._call_llm(prompt)
        if raw is None:
            return None

        # Inject metadata
        raw.setdefault("pmid", pmid)
        raw.setdefault("title", title)

        result = self._validate_result(raw)
        if result is None:
            return None

        # cache the raw model output; verification is re-applied on every load
        self._save_cache(pmid, content_hash, raw)
        result = self._verified(result, content)
        logger.info("Extracted %d entities, %d relationships from PMID %s",
                    len(result.entities), len(result.relationships), pmid)
        return result

    def _verified(self, result: ExtractionResult, content: str) -> ExtractionResult:
        result, stats = verify_relationships(result, content)
        self.dropped_unverified += stats["dropped_unverified"]
        self.sign_overridden += stats["sign_overridden"]
        return result


def parse_json_object(raw_text: str) -> dict | None:
    """The JSON object in a model reply, tolerating fences and think blocks.

    Qwen3-style models emit <think>...</think> before the answer; the
    object is taken from the first "{" to the last "}".
    """
    text = _THINK_RE.sub("", raw_text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _norm_for_quote(text: str) -> str:
    """Case-, punctuation-, whitespace- and inline-tag-insensitive form for
    quote lookup ("CD8+ T cells" matches "CD8<sup>+</sup> T cells")."""
    return " ".join(_QUOTE_NORM_RE.sub(" ", _TAG_RE.sub("", text).lower()).split())


def verify_relationships(
    result: ExtractionResult, content: str
) -> tuple[ExtractionResult, dict]:
    """Keep only relationships whose evidence_quote occurs in the content.

    Matching ignores case, punctuation and whitespace, nothing else, so a
    paraphrased or invented quote is dropped. Predicates with a fixed
    direction (PREDICATE_SIGN) set the sign; other signs are clamped to
    -1/0/1. Subjects/objects missing from the entity list are added so
    the matcher can resolve them. Returns (result, stats).
    """
    haystack = _norm_for_quote(content)
    kept: list[ExtractedRelationship] = []
    stats = {"dropped_unverified": 0, "sign_overridden": 0}
    for rel in result.relationships:
        quote = _norm_for_quote(rel.evidence_quote)
        if len(quote) < 15 or quote not in haystack:
            stats["dropped_unverified"] += 1
            continue
        fixed = PREDICATE_SIGN.get(rel.predicate.strip().lower())
        sign = fixed if fixed is not None else max(-1, min(1, int(rel.sign)))
        if sign != rel.sign:
            stats["sign_overridden"] += 1
        kept.append(rel.model_copy(update={"sign": sign, "pmid": result.pmid}))
    names = {e.name for e in result.entities}
    extra = [
        ExtractedEntity(name=n)
        for rel in kept for n in (rel.subject, rel.object)
        if n and n not in names and not names.add(n)
    ]
    return result.model_copy(
        update={"relationships": kept, "entities": [*result.entities, *extra]}
    ), stats


def extract_batch(
    papers: list[dict],
    theme_config: dict,
    endpoint: str,
    model: str,
    budget: int = 2000,
    cache_dir: Path | None = None,
    extractor: "LLMExtractor | None" = None,
) -> list[ExtractionResult]:
    """Extract from a batch of papers, respecting an LLM call budget.

    Pass a shared ``extractor`` to make ``budget`` apply across several
    batches: its ``call_count`` carries over, and cache hits are free.

    Each paper dict should have keys: pmid, title, content.
    Theme config is a themes.yaml-style dict with a 'entities' list.

    Returns list of ExtractionResult for papers that produced new findings.
    """
    if extractor is None:
        extractor = LLMExtractor(endpoint=endpoint, model=model, cache_dir=cache_dir)
    results: list[ExtractionResult] = []
    theme_entities = theme_config.get("entities", [])

    for paper in papers:
        pmid = paper.get("pmid", "")
        title = paper.get("title", "")
        content = paper.get("content", "")

        if not content:
            logger.warning("Skipping PMID %s: empty content", pmid)
            continue

        try:
            result = extractor.extract(
                pmid=pmid,
                title=title,
                content=content,
                theme_entities=theme_entities,
                max_budget=budget,
            )
        except RuntimeError as exc:
            logger.error("Budget exhausted at PMID %s: %s", pmid, exc)
            break

        if result is not None and (result.entities or result.relationships):
            results.append(result)

        # Small delay to avoid hammering the local LLM
        time.sleep(0.5)

    logger.info("Batch extraction complete: %d/%d papers produced results",
                len(results), len(papers))
    return results
