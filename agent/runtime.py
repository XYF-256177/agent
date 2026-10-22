"""Agent 主循环（核心 Runtime，自研实现，不依赖任何 agent 框架）。

循环步骤（对应题目要求）：
    Step 1  接收用户输入
    Step 2  组装 context，调用 LLM 判断"直接回复"还是"调用工具"
    Step 3  调用工具
    Step 4  根据工具结果决定"继续 loop"还是"返回最终答案"

附带能力：基本异常处理、工具调用 trace/执行日志、上下文轮次限制与基础压缩。
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from agent.llm_client import LLMClient
from agent.memory import Memory, estimate_tokens
from agent.parser import ParsedOutput, parse
from agent.session import Session, SessionManager
from agent.tool_registry import ToolRegistry

logger = logging.getLogger("agent.runtime")

SYSTEM_PROMPT_TEMPLATE = """你是一个乐于助人的智能助手，可以调用工具完成计算、检索和待办管理。

{memory_section}

可用工具：
{tool_section}

回答要求：
1. 优先使用工具获取准确结果，不要凭空编造事实。
2. 需要计算时调用 calculator，需要查资料时调用 search，需要记录或查看待办时调用 todo。
3. 结合工具返回的结果，用简洁友好的中文回答用户。
"""


class AgentRuntime:
    """最小可用 Agent 运行时。"""

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        session_manager: Optional[SessionManager] = None,
        memory: Optional[Memory] = None,
        max_turns: int = 8,
        max_history_messages: int = 20,
        temperature: float = 0.2,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.sessions = session_manager or SessionManager()
        self.memory = memory or Memory()
        self.max_turns = max_turns
        self.max_history_messages = max_history_messages
        self.temperature = temperature

    # ------------------------------------------------------------------ #
    # 对外入口
    # ------------------------------------------------------------------ #
    def run(
        self,
        user_input: str,
        session_id: str = "default",
        user_id: str = "default",
    ) -> str:
        """处理一次用户输入，返回最终答案。"""
        session = self.sessions.get_or_create(session_id, user_id)
        self._auto_remember(user_input, user_id)

        # Step 1: 接收用户输入
        session.messages.append({"role": "user", "content": user_input})
        trace_id = uuid.uuid4().hex[:12]
        self._log_trace(trace_id, "input", {"session_id": session_id, "user": user_input})

        for turn in range(1, self.max_turns + 1):
            # Step 2: 组装 context，让 LLM 决策
            messages = self._build_messages(session, user_id, user_input)
            try:
                response = self.llm.chat(
                    messages,
                    tools=self.registry.to_openai_schema(),
                    temperature=self.temperature,
                )
            except Exception as exc:  # noqa: BLE001 基本异常处理
                self._log_trace(trace_id, "llm_error", {"error": str(exc)})
                fallback = f"抱歉，模型调用出现异常：{exc}"
                session.messages.append({"role": "assistant", "content": fallback})
                return fallback

            parsed = parse(response)
            self._log_trace(trace_id, "llm", {"turn": turn, "thought": parsed.thought[:200]})

            if parsed.has_tool_calls:
                # Step 3: 调用工具并回填结果
                self._execute_tools(session, parsed, session_id, trace_id)
                continue  # Step 4: 继续 loop

            # Step 4: 无工具调用，返回最终答案
            final = parsed.content or "（模型未返回内容）"
            session.messages.append({"role": "assistant", "content": final})
            self._log_trace(trace_id, "answer", {"content": final})
            return final

        fallback = "抱歉，本次任务步骤较多，已达到最大处理轮次，请换一种更简单的方式提问。"
        session.messages.append({"role": "assistant", "content": fallback})
        self._log_trace(trace_id, "max_turns", {"turns": self.max_turns})
        return fallback

    # ------------------------------------------------------------------ #
    # 工具执行
    # ------------------------------------------------------------------ #
    def _execute_tools(
        self,
        session: Session,
        parsed: ParsedOutput,
        session_id: str,
        trace_id: str,
    ) -> None:
        """执行本轮所有工具调用，并回填 assistant/tool 消息。"""
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": parsed.content or None,
            "tool_calls": [],
        }
        tool_msgs: List[Dict[str, Any]] = []

        for tc in parsed.tool_calls:
            call_id = tc.id or uuid.uuid4().hex[:12]
            assistant_msg["tool_calls"].append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
            )
            # 注入隐藏参数 session_id，保证 todo 等工具按会话隔离
            result = self.registry.call(
                tc.name, tc.arguments, context={"session_id": session_id}
            )
            self._log_trace(
                trace_id,
                "tool_call",
                {"tool": tc.name, "args": tc.arguments, "result": result[:500]},
            )
            tool_msgs.append(
                {"role": "tool", "tool_call_id": call_id, "content": result}
            )

        session.messages.append(assistant_msg)
        session.messages.extend(tool_msgs)

    # ------------------------------------------------------------------ #
    # 上下文组装与压缩
    # ------------------------------------------------------------------ #
    def _build_messages(
        self, session: Session, user_id: str, query: str
    ) -> List[Dict[str, Any]]:
        """组装完整 context = system prompt + 历史消息。"""
        self._compress_history(session)

        memory_text = self.memory.summarize(user_id)
        memory_section = (
            "已记住的长期信息：\n" + memory_text if memory_text else ""
        )

        tool_lines = []
        for name in self.registry.names():
            tool = self.registry.get(name)
            if tool:
                tool_lines.append(f"- {name}: {tool.description}")
        tool_section = "\n".join(tool_lines)

        system = SYSTEM_PROMPT_TEMPLATE.format(
            memory_section=memory_section, tool_section=tool_section
        )
        return [{"role": "system", "content": system}] + session.messages

    def _compress_history(self, session: Session) -> None:
        """轮次限制 + 基础压缩。

        当历史消息超过 max_history_messages 时，把最老的一部分用 LLM
        摘要成一条 system 消息，保留最近的消息，避免上下文无限增长。
        """
        msgs = session.messages
        if len(msgs) <= self.max_history_messages:
            return

        overflow = msgs[: len(msgs) - self.max_history_messages]
        keep = msgs[len(msgs) - self.max_history_messages :]
        summary = self._summarize(overflow)
        session.messages = [
            {"role": "system", "content": f"[对话历史摘要]\n{summary}"}
        ] + keep

    def _summarize(self, messages: List[Dict[str, Any]]) -> str:
        """用 LLM 把一组历史消息压缩成要点。失败则退回原文。"""
        text = self._messages_to_text(messages)
        if estimate_tokens(text) < 200:
            return text
        try:
            resp = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": "你是对话摘要助手，把下面的对话压缩成简洁要点，保留关键事实、用户意图和待办。",
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
            )
            summary = parse(resp).content
            return summary.strip() if summary else text
        except Exception:  # noqa: BLE001
            return text

    @staticmethod
    def _messages_to_text(messages: List[Dict[str, Any]]) -> str:
        lines = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content") or ""
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # 记忆与日志
    # ------------------------------------------------------------------ #
    def _auto_remember(self, user_input: str, user_id: str) -> None:
        """简单规则：检测自我介绍/偏好表达，写入长期记忆。"""
        text = user_input.strip()
        for marker in ("我叫", "我是", "我喜欢", "记住"):
            if marker in text:
                self.memory.remember(user_id, marker, text)
                break

    @staticmethod
    def _log_trace(trace_id: str, event: str, detail: Dict[str, Any]) -> None:
        logger.info(
            "[%s][%s] %s",
            trace_id,
            event,
            json.dumps(detail, ensure_ascii=False, default=str),
        )
