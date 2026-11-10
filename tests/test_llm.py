"""LLM factory and fake client. These tests never call a real provider."""

import pytest

from bible_rag.generation.llm import (
    FakeLLMClient,
    LLMUnavailable,
    OpenAICompatClient,
    get_llm,
)


def test_fake_client_records_calls_and_returns_configured_text():
    client = FakeLLMClient("hello [[Matt.6.14]]")
    messages = [{"role": "user", "content": "q"}]
    assert client.complete(messages) == "hello [[Matt.6.14]]"
    assert client.calls == [messages]


def test_fake_client_accepts_callable_response():
    client = FakeLLMClient(lambda messages: messages[-1]["content"].upper())
    assert client.complete([{"role": "user", "content": "abc"}]) == "ABC"


def test_get_llm_openai_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(LLMUnavailable, match="OPENAI_API_KEY is not set"):
        get_llm()


def test_get_llm_deepseek_missing_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LLMUnavailable, match="DEEPSEEK_API_KEY is not set"):
        get_llm()


def test_get_llm_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not-a-vendor")
    with pytest.raises(LLMUnavailable, match="unknown LLM_PROVIDER"):
        get_llm()


def test_get_llm_openai_default_uses_placeholder_key_only(monkeypatch):
    # A placeholder key is enough to construct the client; complete() is not called.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-placeholder")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    client = get_llm()
    assert isinstance(client, OpenAICompatClient)
    assert client.model == "gpt-4o-mini"
    assert client.base_url is None


def test_get_llm_deepseek_config_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-placeholder")
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    client = get_llm()
    assert isinstance(client, OpenAICompatClient)
    assert client.model == "deepseek-chat"
    assert client.base_url == "https://api.deepseek.com"
