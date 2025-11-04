# -*- coding: utf-8 -*-
"""
LLM 客户端统一封装：
- 使用 OpenAI 官方 SDK，但通过 base_url 适配本地 Ollama 或任何 OpenAI 兼容服务（如部分 ModelScope/DashScope 网关）。
- 暴露 chat() 调用，支持工具调用（function calling）消息格式。
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
    # 返回第一条候选
    msg = resp.choices[0].message
    return msg.model_dump()