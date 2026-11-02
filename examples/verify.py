
"""真实 API 冒烟测试（非交互式）。

验证：真实 DeepSeek 下，Agent 主循环、工具调用、session 隔离是否正常工作。
运行方式（项目根目录）：
    python examples/verify.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from dotenv import load_dotenv

from agent import AgentRuntime, LLMClient
from agent.tools import build_default_registry

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def main() -> None:
    llm = LLMClient()
    registry = build_default_registry()
    runtime = AgentRuntime(llm=llm, registry=registry)

    print("=" * 60)
    print(f"模型: {llm.model}  接口: {llm.base_url}")
    print("=" * 60)

    cases = [
        ("w1", "帮我计算 128 + 256 * 2 等于多少"),
        ("w1", "帮我记个待办：下午查北京天气"),
        ("w1", "我的待办有哪些"),
        ("w2", "帮我记个待办：写周报"),
        ("w1", "我的待办有哪些（应该看不到窗口2的内容）"),
    ]

    for session_id, question in cases:
        print(f"\n[{session_id}] 你: {question}")
        try:
            answer = runtime.run(question, session_id=session_id)
            print(f"[{session_id}] Agent: {answer}")
        except Exception as exc:  # noqa: BLE001
            print(f"[{session_id}] 出错: {exc}")


if __name__ == "__main__":
    main()
