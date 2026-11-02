"""工具注册机制测试。"""
import pytest

from agent.tool_registry import ToolRegistry
from agent.tools import build_default_registry


def test_build_default_registry():
    reg = build_default_registry()
    assert set(reg.names()) == {"calculator", "search", "todo"}


def test_to_openai_schema():
    reg = build_default_registry()
    schema = reg.to_openai_schema()
    assert len(schema) == 3
    for item in schema:
        assert item["type"] == "function"
        assert item["function"]["name"] in reg.names()
        assert "parameters" in item["function"]
        assert "description" in item["function"]


def test_duplicate_register_raises():
    reg = ToolRegistry()
    reg.register("x", "desc", {"type": "object", "properties": {}}, lambda: "ok")
    with pytest.raises(ValueError):
        reg.register("x", "desc", {"type": "object", "properties": {}}, lambda: "ok")


def test_call_unknown_tool():
    reg = ToolRegistry()
    result = reg.call("nope", {})
    assert "error" in result


def test_call_calculator():
    reg = build_default_registry()
    assert reg.call("calculator", {"expression": "1+2*3"}) == "7"
    assert reg.call("calculator", {"expression": "2**10"}) == "1024"


def test_call_tool_exception_is_caught():
    reg = ToolRegistry()

    def boom() -> str:
        raise RuntimeError("内部错误")

    reg.register("boom", "d", {"type": "object", "properties": {}}, boom)
    result = reg.call("boom", {})
    assert "内部错误" in result


def test_context_injection_for_hidden_params():
    """验证 session_id 作为隐藏参数被注入，实现 todo 会话隔离。"""
    reg = build_default_registry()
    reg.call("todo", {"action": "add", "item": "A的待办"}, context={"session_id": "w1"})
    reg.call("todo", {"action": "add", "item": "B的待办"}, context={"session_id": "w2"})
    r1 = reg.call("todo", {"action": "list"}, context={"session_id": "w1"})
    r2 = reg.call("todo", {"action": "list"}, context={"session_id": "w2"})
    assert "A的待办" in r1
    assert "B的待办" not in r1
    assert "B的待办" in r2
