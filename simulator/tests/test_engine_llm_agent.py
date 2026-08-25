import json
from types import SimpleNamespace

import pytest

from simulator.engine.llm_agent import (
    DeltaCache,
    OpenCodeClient,
    build_prompt,
    evaluate_llm_delta,
    llm_next_state,
    parse_delta,
)
from simulator.schemas import AgentCard, AgentTier, Epoch, InfluencePacket


def make_card():
    return AgentCard(
        id="tnf_hub",
        label="Tumor Necrosis Factor Alpha",
        entity_type="molecule",
        compartment="systemic",
        tier=AgentTier.HUB,
        community=1,
        baseline_state=0.3,
        pathological_rules=[
            {
                "rule_id": "RULE-tnf_hub-01",
                "description": "TNF drives microglial activation",
                "claim_refs": ["EC-0001"],
                "direction": "up",
            }
        ],
    )


def pkts():
    return [
        InfluencePacket(source_id="il6", sign=1, weight=0.9, sender_state=0.7, tick=4),
        InfluencePacket(source_id="ros", sign=-1, weight=0.5, sender_state=0.2, tick=4),
    ]


VALID = '{"new_state": 0.8, "rationale": "rules up", "refs": ["RULE-tnf_hub-01"]}'


class FakeClient:
    def __init__(self, response=VALID):
        self.response = response
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_client_invokes_opencode_run_subprocess(monkeypatch):
    seen = {}

    def fake_run(cmd, capture_output, text, timeout):
        seen["cmd"] = cmd
        seen["timeout"] = timeout
        return SimpleNamespace(returncode=0, stdout="  out \n", stderr="")

    monkeypatch.setattr("simulator.engine.llm_agent.subprocess.run", fake_run)
    monkeypatch.setenv("OPENCODE_BIN", "/fake/opencode")
    client = OpenCodeClient()
    out = client.complete("MYPROMPT")
    assert out == "out"
    assert seen["cmd"] == ["/fake/opencode", "run", "--format", "text", "MYPROMPT"]
    assert seen["timeout"] == 120


def test_client_raises_on_nonzero_exit(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("simulator.engine.llm_agent.subprocess.run", fake_run)
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    with pytest.raises(RuntimeError):
        OpenCodeClient().complete("p")


def test_build_prompt_contains_rules_packets_state_epoch():
    card = make_card()
    prompt = build_prompt(card, pkts(), 0.42, Epoch.SUBACUTE)
    assert "tnf_hub" in prompt
    assert "RULE-tnf_hub-01" in prompt
    assert "il6" in prompt
    assert "0.42" in prompt
    assert "SUBACUTE" in prompt
    assert '"new_state"' in prompt
    assert "rationale" in prompt
    assert "refs" in prompt


def test_parse_delta_plain_and_fenced():
    plain = parse_delta(VALID)
    assert plain == json.loads(VALID)
    assert plain["new_state"] == 0.8
    fenced = "```json\n" + VALID + "\n```"
    assert parse_delta(fenced) == json.loads(VALID)
    noisy = "Sure! Here it is:\n```\n" + VALID + "\n```"
    assert parse_delta(noisy) == json.loads(VALID)


def test_parse_delta_rejects_garbage():
    for junk in ["no json at all", "[1,2,3]", "", "{\"new_state\": nan}"]:
        with pytest.raises(ValueError):
            parse_delta(junk)


def test_delta_cache_hit_miss_and_order_insensitive_signature():
    cache = DeltaCache()
    key = ("cardsha", 4, DeltaCache.signature(pkts()))
    assert cache.get(*key) is None
    assert cache.hits == 0 and cache.misses == 1
    cache.put(*key, {"raw": VALID, "delta": {"new_state": 0.8}})
    got = cache.get(*key)
    assert got["delta"]["new_state"] == 0.8
    assert cache.hits == 1 and cache.misses == 1
    reordered = list(reversed(pkts()))
    assert DeltaCache.signature(reordered) == key[2]


def test_llm_next_state_happy_path_returns_state_delta():
    result = evaluate_llm_delta(make_card(), pkts(), 0.42, Epoch.SUBACUTE, 4, FakeClient())
    delta = llm_next_state(make_card(), pkts(), 0.42, Epoch.SUBACUTE, 4, FakeClient())
    assert delta is not None
    assert delta.emitter == "llm"
    assert delta.agent_id == "tnf_hub"
    assert delta.tick == 4
    assert delta.new_state == pytest.approx(0.8)
    assert result.prompt_sha256 and result.response_sha256
    assert result.cache_hit is False
    assert result.latency_ms >= 0.0


def test_llm_next_state_none_on_client_exception():
    client = FakeClient(response=RuntimeError("cli missing"))
    assert llm_next_state(make_card(), [], 0.5, Epoch.INITIATION, 0, client) is None


def test_llm_next_state_none_on_garbage_or_invalid_ranges():
    for bad in [
        "garbage",
        '{"new_state": 1.5, "rationale": "x", "refs": ["r"]}',
        '{"new_state": 0.5, "rationale": "x", "refs": []}',
        '{"new_state": "high", "rationale": "x", "refs": ["r"]}',
        '{"rationale": "x", "refs": ["r"]}',
        '{"new_state": 0.5, "rationale": "x"}',
    ]:
        assert llm_next_state(make_card(), [], 0.5, Epoch.INITIATION, 0, FakeClient(bad)) is None


def test_second_identical_call_hits_cache_and_skips_client():
    card = make_card()
    packets = pkts()
    cache = DeltaCache()
    first_client = FakeClient()
    first = llm_next_state(card, packets, 0.4, Epoch.SUBACUTE, 4, first_client, cache=cache)
    assert first is not None and first_client.prompts
    second_client = FakeClient()
    second = llm_next_state(card, packets, 0.4, Epoch.SUBACUTE, 4, second_client, cache=cache)
    assert second == first
    assert second_client.prompts == []
    attempt = evaluate_llm_delta(card, packets, 0.4, Epoch.SUBACUTE, 4, FakeClient(), cache=cache)
    assert attempt.cache_hit is True
