"""交互式演示：从零实现的 Agent 运行示例。

运行方式（在项目根目录）：
    python examples/demo.py

会读取 .env 中的 LLM 配置，若未配置则无法调用真实模型。
输入 quit 退出，输入 new <会话id> 切换会话。
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
    print("最小可用 Agent 已启动")
    print("  - 输入问题直接对话")
    print("  - 输入 new <id> 切换会话（模拟多窗口隔离）")
    print("  - 输入 quit 退出")
    print("=" * 60)

    session_id = "window-1"
    while True:
        try:
            user_input = input(f"\n[{session_id}] 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower().startswith("new "):
            session_id = user_input.split(" ", 1)[1].strip() or "window-1"
            print(f"已切换到会话 [{session_id}]")
            continue

        reply = runtime.run(user_input, session_id=session_id)
        print(f"[{session_id}] Agent: {reply}")


if __name__ == "__main__":
    main()
