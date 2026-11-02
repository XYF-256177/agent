"""LLM 输出解析：提取思考过程、工具调用、最终答案。

主路径：解析 OpenAI 原生 tool_calls 字段。
兜底路径：当模型不支持 function calling、或未返回 tool_calls 时，
从 content 文本中手写提取 JSON（形如 {"thought":..., "tool":..., "answer":...}）。

这个模块自研实现，不依赖任何 agent 框架。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """一次工具调用。"""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ParsedOutput:
    """解析结果：思考过程 + 文本内容 + 工具调用列表。"""

    thought: str = ""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """从文本中提取 JSON 对象（支持 ```json 代码块包裹）。"""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        candidate = match.group(0)
    try:
        data = json.loads(candidate)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_arguments(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def parse(response: Dict[str, Any]) -> ParsedOutput:
    """把 LLM 原始响应解析成结构化对象。"""
    choices = response.get("choices") or []
    if not choices:
        return ParsedOutput()

    message = choices[0].get("message") or {}

    # 思考过程：优先取 reasoning_content（DeepSeek reasoner / 部分模型提供）
    thought = message.get("reasoning_content") or ""
    content = message.get("content") or ""

    # 主路径：原生 tool_calls
    tool_calls: List[ToolCall] = []
    raw_calls = message.get("tool_calls") or []
    for raw in raw_calls:
        fn = raw.get("function") or {}
        name = fn.get("name", "")
        tool_calls.append(
            ToolCall(
                id=raw.get("id") or "",
                name=name,
                arguments=_parse_arguments(fn.get("arguments")),
            )
        )

    # 兜底路径：模型把结构化结果写在 content 里
    if not tool_calls:
        obj = _extract_json(content)
        if obj:
            thought = obj.get("thought") or thought
            tool = obj.get("tool")
            if isinstance(tool, dict) and tool.get("name"):
                tool_calls.append(
                    ToolCall(
                        id=obj.get("id") or "",
                        name=tool["name"],
                        arguments=_parse_arguments(tool.get("arguments")),
                    )
                )
            answer = obj.get("answer")
            if answer is not None:
                content = str(answer)

    return ParsedOutput(thought=thought, content=content, tool_calls=tool_calls)
