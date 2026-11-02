"""Agent 主循环与上下文管理测试。"""
from agent import AgentRuntime
from agent.session import SessionManager
from agent.tools import build_default_registry
from conftest import FakeLLM, final_response, tool_response


def _runtime(llm, **kwargs):
    kwargs.setdefault("registry", build_default_registry())
    return AgentRuntime(llm=llm, **kwargs)


def test_direct_answer():
    llm = FakeLLM([final_response("你好！有什么可以帮你？")])
    ans = _runtime(llm).run("你好", session_id="s1")
    assert "你好" in ans


def test_tool_loop_converges():
    llm = FakeLLM(
        [
            tool_response("calculator", {"expression": "1+2*3"}, "c1"),
            final_response("计算结果是 7"),
        ]
    )
    ans = _runtime(llm).run("帮我算 1+2*3", session_id="s1")
    assert "7" in ans
    tool_calls = [c for c in llm.calls if c["tools"]]
    assert len(tool_calls) >= 1


def test_followup_with_tool():
    """带工具的追问：基于上一轮结果继续调用工具。"""
    llm = FakeLLM(
        [
            tool_response("calculator", {"expression": "2+3"}, "c1"),
            final_response("2+3=5"),
            tool_response("calculator", {"expression": "5*2"}, "c2"),
            final_response("5*2=10"),
        ]
    )
    rt = _runtime(llm)
    ans1 = rt.run("2+3 等于多少", session_id="s1")
    ans2 = rt.run("再乘以 2", session_id="s1")
    assert "5" in ans1
    assert "10" in ans2


def test_multi_session_runs_independently():
    """窗口1、窗口2 各自记录待办，流程互不影响。"""
    llm = FakeLLM(
        [
            tool_response("todo", {"action": "add", "item": "查天气"}, "c1"),
            final_response("已记录待办"),
            tool_response("todo", {"action": "add", "item": "写周报"}, "c2"),
            final_response("已记录待办"),
            tool_response("todo", {"action": "list"}, "c3"),
            final_response("窗口1的待办：查天气"),
        ]
    )
    rt = _runtime(llm)
    rt.run("帮我记待办：查天气", session_id="w1")
    rt.run("帮我记待办：写周报", session_id="w2")
    ans = rt.run("看看我的待办", session_id="w1")
    assert "写周报" not in ans


def test_max_turns_fallback():
    llm = FakeLLM(
        [tool_response("calculator", {"expression": "1+1"}, f"c{i}") for i in range(20)]
    )
    rt = _runtime(llm, max_turns=3)
    ans = rt.run("算点东西", session_id="s1")
    assert "最大处理轮次" in ans


def test_llm_error_is_handled():
    class BoomLLM:
        def chat(self, messages, tools=None, temperature=0.2):
            raise RuntimeError("network down")

    rt = _runtime(BoomLLM())
    ans = rt.run("你好", session_id="s1")
    assert "异常" in ans


def test_compress_history_triggers_summary():
    llm = FakeLLM([final_response("这是压缩后的摘要")])
    rt = _runtime(llm, max_history_messages=3)
    session = SessionManager().get_or_create("s1")
    long_text = "很长的一段话" * 100
    for i in range(5):
        session.messages.append({"role": "user", "content": f"{i} {long_text}"})
    rt._compress_history(session)
    assert session.messages[0]["role"] == "system"
    assert "摘要" in session.messages[0]["content"]
    assert len(session.messages) <= 4


def test_no_compress_when_under_limit():
    llm = FakeLLM([])
    rt = _runtime(llm, max_history_messages=10)
    session = SessionManager().get_or_create("s1")
    for i in range(3):
        session.messages.append({"role": "user", "content": f"msg {i}"})
    rt._compress_history(session)
    assert len(session.messages) == 3
