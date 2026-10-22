"""pytest 共享 fixture：可编程假 LLM，用于不依赖真实 API 的单元测试。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pytest

from agent.tools import build_default_registry


def final_response(content: str) -> Dict[str, Any]:
    """构造"直接回复"响应。"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": None,
                }
            }
        ]
    }


def tool_response(
    name: str, arguments: Dict[str, Any], call_id: str = "call_1"
) -> Dict[str, Any]:
    """构造"调用工具"响应。"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments, ensure_ascii=False),
                            },
                        }
                    ],
                }
            }
        ]
    }


class FakeLLM:
    """可编程假 LLM：按脚本依次返回响应，并记录每次调用的入参。"""

    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None) -> None:
        self.responses: List[Dict[str, Any]] = list(responses or [])
        self.calls: List[Dict[str, Any]] = []

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        self.calls.append({"messages": messages, "tools": tools})
        if self.responses:
            return self.responses.pop(0)
        return final_response("（脚本已用完）")


@pytest.fixture
def registry():
    return build_default_registry()
