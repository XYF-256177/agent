"""session 管理：多窗口隔离。

用户 A 的窗口 1、窗口 2 是相互独立的 session，
每个 session 维护自己的消息历史，互不影响，且可随时续聊。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Session:
    """一个独立会话。"""

    id: str
    user_id: str = "default"
    messages: List[Dict[str, Any]] = field(default_factory=list)


class SessionManager:
    """管理所有 session 的生命周期。"""

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: str, user_id: str = "default") -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(id=session_id, user_id=user_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def all_ids(self) -> List[str]:
        return list(self._sessions.keys())
