# -*- coding: utf-8 -*-
"""
Unified LLM client wrapper:
- Uses the official OpenAI SDK but adapts to local Ollama or any OpenAI-compatible service via base_url (e.g., some ModelScope/DashScope gateways).
- Exposes a chat() helper that supports tool-calling (function calling) message formats.
"""
from __future__ import annotations
from typing import Any, Dict, List
from openai import OpenAI
from .config import SETTINGS


_client = OpenAI(
    api_key=SETTINGS.api_key,
    base_url=SETTINGS.base_url,
)


def chat(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] | None = None, tool_choice: str | None = None,
         temperature: float = 0.3) -> Dict[str, Any]:
    resp = _client.chat.completions.create(
        model=SETTINGS.model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,  # "auto" | "none" | {"type":"function","function":{"name":"..."}}
        temperature=temperature,
        max_tokens=SETTINGS.max_tokens,
        timeout=SETTINGS.request_timeout,
    )
    # Return the first candidate
    msg = resp.choices[0].message
    return msg.model_dump()