"""remember 工具：让 LLM 自主决定把什么写入长期记忆。

设计要点：
- 这是唯一一个「有副作用」的工具：它把信息写入跨会话长期记忆，
  使 Agent 在后续对话（甚至换窗口后）仍能回忆起用户偏好、关键事实。
- user_id 与 memory 都是「隐藏参数」，由 Runtime 通过 context 注入，
  不出现在暴露给 LLM 的 Schema 中，避免 LLM 伪造用户身份。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

# 约定：Memory 实例通过 context 注入；仅当调用方（Runtime）注入 memory 时才真正落盘。
MemoryLike = Any


def remember(
    key: str,
    value: str,
    user_id: str = "",
    memory: Optional[MemoryLike] = None,
) -> str:
    """把一条信息写入长期记忆。

    key：记忆的索引键，如「姓名」「专业」「项目偏好」。
    value：记忆的具体内容。
    """
    if not key or not key.strip():
        return json.dumps({"error": "remember 需要提供 key"}, ensure_ascii=False)
    if not value or not value.strip():
        return json.dumps({"error": "remember 需要提供 value"}, ensure_ascii=False)

    if memory is not None:
        memory.remember(user_id or "default", key.strip(), value.strip())
        return json.dumps(
            {"ok": True, "remembered": {key.strip(): value.strip()}},
            ensure_ascii=False,
        )
    # 未注入 memory 时降级为「仅回显」，不影响主流程
    return json.dumps(
        {"ok": False, "reason": "memory 未启用", "pair": {key: value}},
        ensure_ascii=False,
    )


REMEMBER_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "记忆的索引键，例如：姓名、专业、偏好、项目方向",
        },
        "value": {
            "type": "string",
            "description": "要记住的具体内容",
        },
    },
    "required": ["key", "value"],
}
