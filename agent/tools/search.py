"""search 工具：mock 实现，基于内置知识库做简单关键词检索。"""
from __future__ import annotations

import json

# 预设知识库（可自行扩充）
_KNOWLEDGE_BASE = [
    "今天北京天气晴，气温 18 到 26 摄氏度，适合出行。",
    "今天广州有阵雨，气温 24 到 30 摄氏度，出门记得带伞。",
    "明天上海多云转晴，气温 20 到 27 摄氏度。",
    "深圳今日多云，气温 25 到 31 摄氏度。",
    "2026 年国庆假期为 10 月 1 日至 10 月 7 日。",
    "个人所得税起征点为每月 5000 元。",
]


def search(query: str) -> str:
    """按关键词命中知识库，返回检索结果（mock）。"""
    keywords = [w for w in query.split() if w.strip()]
    if not keywords:
        return json.dumps({"results": []}, ensure_ascii=False)

    matched = []
    for doc in _KNOWLEDGE_BASE:
        if any(kw in doc for kw in keywords):
            matched.append(doc)

    if not matched:
        return json.dumps(
            {"results": [], "hint": "mock 知识库中未找到相关内容"}, ensure_ascii=False
        )
    return json.dumps({"results": matched}, ensure_ascii=False)


SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "要检索的关键词，例如 '北京 天气'",
        }
    },
    "required": ["query"],
}
