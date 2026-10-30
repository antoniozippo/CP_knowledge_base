# crawler/tests/test_anthropic_backend.py - Claude API extraction with stub clients (no network)

import json
from types import SimpleNamespace

import pytest

from crawler import anthropic_backend as ab
from crawler.extractor import LLMExtractor

CONTENT = "Results: TNF-alpha strongly reduced KCC2 expression in the dorsal horn."
REPLY = {
    "entities": [{"name": "TNF-alpha", "entity_type": "molecule", "aliases": [],
                  "compartment": "dorsal_horn", "mentions": 1}],
    "relationships": [{"subject": "TNF-alpha", "predicate": "downregulates", "object": "KCC2",
                       "sign": 0, "evidence_quote": "TNF-alpha strongly reduced KCC2 expression",
                       "confidence": "HIGH"}],
    "key_findings": [], "novel_terms": [],
}


def message(text=None, stop_reason="end_turn", category=None):
    content = [SimpleNamespace(type="thinking", thinking="")]
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(stop_reason=stop_reason, content=content,
                           stop_details=SimpleNamespace(category=category))


class StubMessages:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def stub_client(reply):
    messages = StubMessages(reply)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_params_use_structured_output_effort_and_system_prompt():
    params = ab.message_params("PROMPT", model="claude-opus-5-5", effort="low")
    assert params["model"] == "claude-opus-5-5"
    assert params["messages"] == [{"role": "user", "content": "PROMPT"}]
    assert "evidence_quote" in params["system"]
    fmt = params["output_config"]["format"]
    assert params["output_config"]["effort"] == "low"
    assert fmt["type"] == "json_schema"
    rel = fmt["schema"]["properties"]["relationships"]["items"]
    assert rel["additionalProperties"] is False and set(rel["required"]) == set(rel["properties"])
    assert "thinking" not in params and "temperature" not in params


def test_reply_json_reads_text_block_and_rejects_refusal_and_truncation():
    assert ab.reply_json(message(json.dumps(REPLY))) == REPLY
    assert ab.reply_json(message(stop_reason="refusal", category="bio")) is None
    assert ab.reply_json(message("{\"entities\": [", stop_reason="max_tokens")) is None


def test_sync_extractor_enables_fallbacks_and_verifies_quotes(tmp_path):
    client, messages = stub_client(message(json.dumps(REPLY)))
    extractor = ab.AnthropicExtractor(cache_dir=tmp_path, client=client)
    result = extractor.extract("1", "t", CONTENT, theme_entities=["KCC2"])
    (call,) = messages.calls
    assert call["fallbacks"] == "default" and call["betas"] == [ab.FALLBACK_BETA]
    assert "KCC2" in call["messages"][0]["content"]
    assert [(r.subject, r.sign) for r in result.relationships] == [("TNF-alpha", -1)]


def test_client_uses_crawler_key_and_ignores_harness_base_url(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://harness.invalid")
    monkeypatch.delenv(ab.API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=ab.API_KEY_ENV):
        ab.make_client()
    monkeypatch.setenv(ab.API_KEY_ENV, "sk-test")
    client = ab.make_client()
    assert str(client.base_url).rstrip("/") == ab.DEFAULT_BASE_URL
    assert client.api_key == "sk-test"


def test_batch_results_land_where_run_py_reads_them(tmp_path):
    papers = [({"pmid": "1", "title": "t1", "content": CONTENT}, ["KCC2"]),
              ({"pmid": "2", "title": "t2", "content": CONTENT + " x" * 20000}, ["KCC2"])]
    items = ab.prepare_batch_items(papers, tmp_path)
    assert [i["pmid"] for i in items] == ["1", "2"]
    assert all(len(i["custom_id"]) <= 64 for i in items)
    assert "[... truncated" in items[1]["prompt"]

    results = [
        SimpleNamespace(custom_id=items[0]["custom_id"],
                        result=SimpleNamespace(type="succeeded", message=message(json.dumps(REPLY)))),
        SimpleNamespace(custom_id=items[1]["custom_id"], result=SimpleNamespace(type="expired")),
    ]
    client = SimpleNamespace(messages=SimpleNamespace(batches=SimpleNamespace(results=lambda bid: results)))
    manifest = {i["custom_id"]: {k: i[k] for k in ("pmid", "title", "content_hash")} for i in items}
    counts = ab.collect_batch("msgbatch_x", manifest, tmp_path, client=client)
    assert counts["cached"] == 1 and counts["expired"] == 1

    # run.py's extractor now finds paper 1 as a free cache hit; paper 2 is resubmitted
    local = LLMExtractor(cache_dir=tmp_path)
    local._call_llm = lambda prompt: pytest.fail("cache miss for a collected paper")
    result = local.extract("1", "t1", CONTENT, max_budget=1)
    assert [r.sign for r in result.relationships] == [-1]
    assert [i["pmid"] for i in ab.prepare_batch_items(papers, tmp_path)] == ["2"]
