"""长期记忆与上下文管理。

- Memory：跨 session 的长期记忆，按 user_id 隔离，支持关键词召回与摘要。
- estimate_tokens：粗略 token 估算，用于判断是否需要压缩上下文。
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中英文混合的简化启发式）。"""
    if not text:
        return 0
    return max(1, len(text) // 2)


class Memory:
    """跨 session 长期记忆。

    数据模型：{user_id: [{"key", "value", "ts"}, ...]}
    召回时机：每次组装 context 之前调用 recall/summarize。
    放置方式：召回结果拼接到 system prompt 顶部，优先级高于对话历史。
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def remember(self, user_id: str, key: str, value: Any) -> None:
        """写入一条长期记忆，同 key 覆盖旧值。"""
        facts = self._store.setdefault(user_id, [])
        for fact in facts:
            if fact["key"] == key:
                fact["value"] = value
                fact["ts"] = time.time()
                return
        facts.append({"key": key, "value": value, "ts": time.time()})

    def recall(self, user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """关键词召回：query 分词后匹配 key/value。

        若关键词无命中，退回"最近 top_k 条"，保证追问场景不丢上下文。
        """
        facts = self._store.get(user_id, [])
        if not facts:
            return []
        if not query or not query.strip():
            return sorted(facts, key=lambda f: f["ts"], reverse=True)[:top_k]

        tokens = [t for t in re.split(r"\s+", query) if t]
        scored = []
        for fact in facts:
            text = f"{fact['key']} {fact['value']}"
            score = sum(1 for t in tokens if t in text)
            if score > 0:
                scored.append((score, fact))
        if scored:
            scored.sort(key=lambda x: (x[0], x[1]["ts"]), reverse=True)
            return [f for _, f in scored[:top_k]]
        return sorted(facts, key=lambda f: f["ts"], reverse=True)[:top_k]

    def summarize(self, user_id: str) -> str:
        """生成长期记忆摘要，用于塞进 system prompt。"""
        facts = self._store.get(user_id, [])
        if not facts:
            return ""
        facts_sorted = sorted(facts, key=lambda f: f["ts"], reverse=True)
        lines = [f"- {f['key']}: {f['value']}" for f in facts_sorted]
        return "\n".join(lines)
