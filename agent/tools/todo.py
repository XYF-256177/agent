"""todo 工具：待办事项管理。

关键设计：待办按 session_id 隔离存储。
session_id 是"隐藏参数"，不出现在暴露给 LLM 的 Schema 中，
由 Runtime 在执行工具时通过 context 注入，从而保证不同窗口的待办互不影响。
"""
from __future__ import annotations

import json
from typing import Dict, List

# {session_id: [待办项, ...]}
_TODO_STORE: Dict[str, List[str]] = {}


def todo(action: str, item: str = "", session_id: str = "") -> str:
    """待办操作。action: add | list | clear。"""
    items = _TODO_STORE.setdefault(session_id, [])

    if action == "add":
        if not item or not item.strip():
            return json.dumps({"error": "add 操作需要提供 item 参数"}, ensure_ascii=False)
        items.append(item.strip())
        return json.dumps({"ok": True, "todos": list(items)}, ensure_ascii=False)

    if action == "list":
        return json.dumps({"todos": list(items)}, ensure_ascii=False)

    if action == "clear":
        items.clear()
        return json.dumps({"ok": True, "todos": []}, ensure_ascii=False)

    return json.dumps(
        {"error": f"未知 action: {action}，可选值为 add/list/clear"}, ensure_ascii=False
    )


TODO_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["add", "list", "clear"],
            "description": "操作类型：add 添加待办，list 查看待办，clear 清空待办",
        },
        "item": {
            "type": "string",
            "description": "待办事项内容，仅当 action 为 add 时需要",
        },
    },
    "required": ["action"],
}
