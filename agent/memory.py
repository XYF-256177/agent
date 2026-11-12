"""长期记忆与上下文管理。

- Memory：跨 session 的长期记忆，按 user_id 隔离。
  - 写入：外部通过 remember(key, value) 写入；也可由 Agent 的 remember 工具自主写入。
  - 召回：recall(query) 做相关性筛选（中文按字符 bigram 分词，英文按词），只把相关记忆注入 prompt，
         避免无关记忆撑爆上下文。
  - 持久化：传入 persist_path 时，记忆落地为 JSON 文件，进程重启不丢失。
- estimate_tokens：粗略 token 估算，用于判断是否需要压缩上下文。
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中英文混合的简化启发式）。"""
    if not text:
        return 0
    return max(1, len(text) // 2)


def _tokenize(text: str) -> List[str]:
    """把文本切成可匹配的 token。

    - 连续英文/数字按词提取；
    - 连续中文按「单字 + 相邻 bigram」提取，使「我叫张三」能被「张三」召回，
      解决原实现用空格分词对中文完全失效的问题。
    """
    if not text:
        return []
    tokens: List[str] = []
    # 英文 / 数字词
    tokens += re.findall(r"[a-zA-Z0-9]+", text.lower())
    # 中文片段：单字 + bigram
    for zh_segment in re.findall(r"[一-鿿]+", text):
        chars = list(zh_segment)
        tokens += chars
        for i in range(len(chars) - 1):
            tokens.append(chars[i] + chars[i + 1])
    # 去重保序
    seen = set()
    out: List[str] = []
    for t in tokens:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


class Memory:
    """跨 session 长期记忆。

    数据模型：{user_id: [{"key", "value", "ts"}, ...]}
    召回时机：每次组装 context 之前调用 recall(query) 做相关性筛选。
    放置方式：召回结果拼接到 system prompt 顶部，优先级高于对话历史。
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self.persist_path = persist_path
        if persist_path:
            self._load()

    # ------------------------- 持久化 ------------------------- #
    def _load(self) -> None:
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._store = {k: list(v) for k, v in data.items()}
        except FileNotFoundError:
            self._store = {}
        except (json.JSONDecodeError, OSError):
            self._store = {}

    def _persist(self) -> None:
        if not self.persist_path:
            return
        tmp = self.persist_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._store, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.persist_path)
        except OSError:
            pass

    # ------------------------- 读写接口 ------------------------- #
    def remember(self, user_id: str, key: str, value: Any) -> None:
        """写入一条长期记忆，同 key 覆盖旧值。"""
        facts = self._store.setdefault(user_id, [])
        for fact in facts:
            if fact["key"] == key:
                fact["value"] = value
                fact["ts"] = time.time()
                self._persist()
                return
        facts.append({"key": key, "value": value, "ts": time.time()})
        self._persist()

    def recall(
        self, user_id: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """相关性召回：对 query 做分词后与每条记忆的 key/value 匹配打分。

        若关键词无命中，退回「最近 top_k 条」，保证追问场景不丢上下文。
        """
        facts = self._store.get(user_id, [])
        if not facts:
            return []
        if not query or not query.strip():
            return sorted(facts, key=lambda f: f["ts"], reverse=True)[:top_k]

        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return sorted(facts, key=lambda f: f["ts"], reverse=True)[:top_k]

        scored = []
        for fact in facts:
            text = f"{fact['key']} {fact['value']}"
            score = sum(1 for t in q_tokens if t in text)
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

    def clear(self, user_id: str) -> None:
        """清空某用户的全部长期记忆。"""
        self._store.pop(user_id, None)
        self._persist()
