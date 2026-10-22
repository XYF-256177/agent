"""工具注册机制。

每个工具包含三要素：名称(name)、描述(description)、参数 Schema(parameters JSON Schema)。
LLM 基于这些 Schema 自主决策是否调用、如何传参。
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class Tool:
    """单个工具的元信息与实现。"""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    func: Callable[..., Any]


class ToolRegistry:
    """工具注册表：注册工具、生成 OpenAI 兼容 tools 描述、执行工具。"""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Any],
    ) -> None:
        if name in self._tools:
            raise ValueError(f"工具 {name} 已注册，不允许重复注册")
        self._tools[name] = Tool(name, description, parameters, func)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def to_openai_schema(self) -> list[Dict[str, Any]]:
        """生成 OpenAI 兼容的 tools 参数列表。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def call(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """执行工具并返回字符串结果。

        context 用于注入工具"隐藏参数"（例如 session_id），
        这些参数不会暴露给 LLM，但工具函数可按需声明接收。
        实现方式：通过 inspect 检查函数签名，只注入函数确实需要的 context 键。
        """
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

        kwargs: Dict[str, Any] = dict(arguments or {})
        if context:
            sig = inspect.signature(tool.func)
            for key, value in context.items():
                if key in sig.parameters:
                    kwargs[key] = value

        try:
            result = tool.func(**kwargs)
        except Exception as exc:  # noqa: BLE001 兜住工具内部异常，交给 LLM 感知
            return json.dumps(
                {"error": f"工具 {name} 执行异常: {exc}"}, ensure_ascii=False
            )

        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)
