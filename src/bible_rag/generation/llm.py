"""LLM client interface.

The default provider is OpenAI (`gpt-4o-mini`) via the official `openai` SDK.
DeepSeek (OpenAI-compatible) can be selected with LLM_PROVIDER=deepseek, so the
rest of the pipeline does not depend on one vendor.

Never construct a real client in unit tests: use `FakeLLMClient`. The factory
reads keys from the environment and does not make a network call until
`complete()` is invoked.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol


class LLMUnavailable(RuntimeError):
    """Raised when the configured provider has no API key (or an unknown name)."""


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAICompatClient:
    """Official OpenAI SDK, also used for OpenAI-compatible providers."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        from openai import OpenAI

        self.model = model
        self.base_url = base_url
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        return (response.choices[0].message.content or "").strip()


class FakeLLMClient:
    """Deterministic stand-in: no network, records every call."""

    def __init__(self, response: str | Callable[[list[dict[str, str]]], str] = ""):
        self._response = response
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        if callable(self._response):
            return self._response(messages)
        return self._response


def get_llm() -> LLMClient:
    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower() or "openai"
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY") or ""
        if not key.strip():
            raise LLMUnavailable("OPENAI_API_KEY is not set; generation is unavailable")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("OPENAI_BASE_URL") or None
        return OpenAICompatClient(api_key=key, model=model, base_url=base_url)
    if provider == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY") or ""
        if not key.strip():
            raise LLMUnavailable("DEEPSEEK_API_KEY is not set; generation is unavailable")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        return OpenAICompatClient(api_key=key, model=model, base_url=base_url)
    raise LLMUnavailable(f"unknown LLM_PROVIDER {provider!r}; use 'openai' or 'deepseek'")
