# crawler/extractor.py - LLM entity/relationship extraction

import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
            resp = requests.post(url, json=payload, timeout=120)
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

        # Strip markdown fences if present
        text = raw_text.strip()
        if text.startswith("```"):
            # Remove opening fence (possibly with language tag)
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Some models output <thought> blocks before JSON — strip them
        if "<thought>" in text and "</thought>" in text:
            thought_end = text.index("</thought>") + len("</thought>")
            text = text[thought_end:].strip()
        elif text.startswith("<thought>"):
            # No closing tag — try to find JSON start
            bracket_pos = text.find("{")
            if bracket_pos >= 0:
                text = text[bracket_pos:]

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON output: %s\nRaw output (first 500 chars): %s",
                         exc, text[:500])
            return None

    def _check_cache(self, pmid: str, content_hash: str) -> Optional[dict]:
        """Check if a cached extraction exists for this PMID + content hash."""
        cache_path = self.cache_dir / f"extract_{pmid}_{content_hash}.json"
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Cache read failed for %s: %s", cache_path, exc)
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
            content: Full text or abstract.
            theme_entities: Optional list of theme-relevant entity names.
            max_budget: If >0, raise RuntimeError when call_count reaches this.

        Returns:
            ExtractionResult or None on failure.
        """
        if max_budget > 0 and self.call_count >= max_budget:
            raise RuntimeError(
                f"LLM budget exhausted ({self.call_count}/{max_budget} calls)"
            )

        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]

        # Check cache
        cached = self._check_cache(pmid, content_hash)
        if cached is not None:
            logger.debug("Cache hit for PMID %s", pmid)
            validated = self._validate_result(cached)
            if validated is not None:
                return validated
            logger.warning("Cached result invalid for PMID %s, re-extracting", pmid)

        # Truncate content for LLM context
        if len(content) > 30000:
            content = content[:30000] + "\n\n[... truncated for LLM context ...]"
        elif len(content) > 8000 and len(content) <= 30000:
            # Likely abstract-only; still truncate at 8000
            content = content[:8000] + "\n\n[... truncated ...]"

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

        self._save_cache(pmid, content_hash, raw)
        logger.info("Extracted %d entities, %d relationships from PMID %s",
                     len(result.entities), len(result.relationships), pmid)
        return result


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
