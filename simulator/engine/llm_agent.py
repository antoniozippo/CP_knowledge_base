"""LLM-driven state updates via the `opencode` CLI or a local OpenAI-compatible
endpoint, with a deterministic cache so identical (card, tick, packet-context)
requests never re-invoke the subprocess/client. All failures degrade to None;
the caller falls back to the rule engine.
"""

import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import URLError

from simulator.schemas import AgentCard, Epoch, InfluencePacket, StateDelta

logger = logging.getLogger(__name__)

DEFAULT_OPENCODE_BIN = "opencode"
CLIENT_TIMEOUT_S = 180
MAX_RATIONALE_CHARS = 300


class OpenCodeClient:
    def __init__(self, bin_path: str | None = None):
        self.bin_path = bin_path or os.environ.get("OPENCODE_BIN", DEFAULT_OPENCODE_BIN)

    def complete(self, prompt: str) -> str:
        result = subprocess.run(
            [self.bin_path, "run", "--format", "default", prompt],
            capture_output=True,
            text=True,
            timeout=CLIENT_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"opencode CLI failed with exit code {result.returncode}: {result.stderr}"
            )
        return result.stdout.strip()


class LocalLLMClient:
    """OpenAI-compatible client for local LM Studio / vLLM / ollama endpoints."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ):
        self.endpoint = (
            endpoint
            or os.environ.get("LLM_ENDPOINT", "http://192.168.1.13:1234")
        ).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", "qwen/qwen3.8-27b")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def complete(self, prompt: str) -> str:
        url = f"{self.endpoint}/v1/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "extra_body": {"enable_thinking": False},
        }).encode("utf-8")

        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=CLIENT_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"] or ""
        finish = data["choices"][0].get("finish_reason", "")

        if finish == "length" and not content.strip():
            raise RuntimeError(
                f"LLM response truncated; increase max_tokens"
            )

        return content.strip()


def card_sha256(card: AgentCard) -> str:
    canonical = json.dumps(card.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_prompt(
    card: AgentCard,
    packets: list[InfluencePacket],
    current_state: float,
    epoch: Epoch,
    tick: int = 0,
) -> str:
    rules_lines = [
        f"- {rule.rule_id}: direction={rule.direction} magnitude_hint={rule.magnitude_hint} "
        f"desc={rule.description} claims={rule.claim_refs}"
        for rule in card.pathological_rules
    ]
    inbound_lines = [
        f"- from {p.source_id}: sign={p.sign:+d} weight={p.weight:.2f} "
        f"sender_state={p.sender_state:.4f} (baseline {p.sender_baseline:.4f})"
        for p in packets
    ]
    return (
        f'You are simulating agent "{card.id}" ({card.label}), entity_type={card.entity_type}, '
        f"compartment={card.compartment}, tier={card.tier.value}.\n"
        f"tick: {tick}\n"
        f"epoch: {epoch.value}\n"
        f"current_state: {current_state:.6f}\n"
        "pathological_rules:\n"
        + ("\n".join(rules_lines) if rules_lines else "- (none)")
        + "\ninbound_influences:\n"
        + ("\n".join(inbound_lines) if inbound_lines else "- (none)")
        + "\n\nDecide this agent's next activity state for tomorrow.\n"
        'Respond with ONLY one JSON object and nothing else:\n'
        '{"new_state": <float in [0,1]>, '
        f'"rationale": "<= {MAX_RATIONALE_CHARS} chars", '
        '"refs": [<rule_id or claim ids taken from THIS card\'s pathological_rules/claim_refs>]}\n'
        "No markdown fences, no extra keys, no prose."
    )


def parse_delta(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in LLM response: {raw[:200]!r}")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in LLM response: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"LLM response JSON is not an object: {type(parsed).__name__}")
    return parsed


@dataclass
class LLMAttemptResult:
    delta: StateDelta | None
    prompt_sha256: str | None = None
    response_sha256: str | None = None
    cache_hit: bool = False
    latency_ms: float | None = None


class DeltaCache:
    def __init__(self):
        self._store: dict[tuple[str, int, str], dict] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def signature(packets: list[InfluencePacket]) -> str:
        tuples = sorted(
            (p.source_id, p.sign, p.weight, p.sender_state, p.sender_baseline, p.tick)
            for p in packets
        )
        canonical = json.dumps(tuples, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, card_sha: str, tick: int, packets_sig: str) -> dict | None:
        key = (card_sha, tick, packets_sig)
        entry = self._store.get(key)
        if entry is not None:
            self.hits += 1
        else:
            self.misses += 1
        return entry

    def put(self, card_sha: str, tick: int, packets_sig: str, value: dict) -> None:
        self._store[(card_sha, tick, packets_sig)] = value


def _validated_delta(card: AgentCard, tick: int, delta_dict: dict) -> StateDelta:
    new_state = delta_dict["new_state"]
    rationale = delta_dict["rationale"]
    refs = delta_dict["refs"]
    if not isinstance(new_state, (int, float)) or isinstance(new_state, bool):
        raise ValueError("new_state must be numeric")
    if not 0.0 <= float(new_state) <= 1.0:
        raise ValueError(f"new_state out of range: {new_state}")
    if not isinstance(rationale, str):
        raise ValueError("rationale must be a string")
    if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
        raise ValueError("refs must be a list of strings")
    if not refs:
        refs = ["LLM_NO_REFS"]
    return StateDelta(
        agent_id=card.id,
        tick=tick,
        new_state=float(new_state),
        rationale=rationale,
        refs=refs,
        emitter="llm",
    )


def evaluate_llm_delta(
    card: AgentCard,
    packets: list[InfluencePacket],
    current_state: float,
    epoch: Epoch,
    tick: int,
    client: OpenCodeClient,
    cache: DeltaCache | None = None,
) -> LLMAttemptResult:
    prompt = build_prompt(card, packets, current_state, epoch, tick)
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    csha = card_sha256(card)
    psig = DeltaCache.signature(packets)
    if cache is not None:
        cached = cache.get(csha, tick, psig)
        if cached is not None:
            try:
                delta = _validated_delta(card, tick, cached["delta"])
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("cached delta invalid for %s tick %s: %s", card.id, tick, exc)
                return LLMAttemptResult(delta=None, cache_hit=True)
            response_sha = hashlib.sha256(cached["raw"].encode("utf-8")).hexdigest()
            return LLMAttemptResult(
                delta=delta,
                prompt_sha256=prompt_sha,
                response_sha256=response_sha,
                cache_hit=True,
            )
    started = time.perf_counter()
    try:
        raw = client.complete(prompt)
    except Exception as exc:
        latency = (time.perf_counter() - started) * 1000.0
        logger.warning("llm_next_state client failure for %s at tick %s: %s", card.id, tick, exc)
        return LLMAttemptResult(delta=None, latency_ms=latency)
    latency = (time.perf_counter() - started) * 1000.0
    try:
        delta_dict = parse_delta(raw)
        delta = _validated_delta(card, tick, delta_dict)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("llm_next_state parse/validation failure for %s: %s", card.id, exc)
        return LLMAttemptResult(delta=None, latency_ms=latency)
    if cache is not None:
        cache.put(csha, tick, psig, {"raw": raw, "delta": delta_dict})
    return LLMAttemptResult(
        delta=delta,
        prompt_sha256=prompt_sha,
        response_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        cache_hit=False,
        latency_ms=latency,
    )


def llm_next_state(
    card: AgentCard,
    packets: list[InfluencePacket],
    current_state: float,
    epoch: Epoch,
    tick: int,
    client: OpenCodeClient,
    cache: DeltaCache | None = None,
) -> StateDelta | None:
    return evaluate_llm_delta(card, packets, current_state, epoch, tick, client, cache).delta
