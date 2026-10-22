"""LLM 输出解析测试。"""
from agent.parser import parse


def test_parse_native_tool_calls():
    resp = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "reasoning_content": "用户需要计算",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": '{"expression": "1+1"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    out = parse(resp)
    assert out.has_tool_calls
    assert out.tool_calls[0].name == "calculator"
    assert out.tool_calls[0].arguments == {"expression": "1+1"}
    assert out.thought == "用户需要计算"


def test_parse_final_answer():
    resp = {"choices": [{"message": {"content": "答案是 2", "tool_calls": None}}]}
    out = parse(resp)
    assert not out.has_tool_calls
    assert out.content == "答案是 2"


def test_parse_fallback_json_tool():
    """兜底路径：模型把 JSON 写在 content 里。"""
    resp = {
        "choices": [
            {
                "message": {
                    "content": '{"thought":"查天气","tool":{"name":"search","arguments":{"query":"北京天气"}}}',
                    "tool_calls": None,
                }
            }
        ]
    }
    out = parse(resp)
    assert out.has_tool_calls
    assert out.tool_calls[0].name == "search"
    assert out.tool_calls[0].arguments == {"query": "北京天气"}
    assert out.thought == "查天气"


def test_parse_fallback_json_answer():
    resp = {
        "choices": [
            {
                "message": {
                    "content": '{"thought":"直接回答","answer":"好的"}',
                    "tool_calls": None,
                }
            }
        ]
    }
    out = parse(resp)
    assert not out.has_tool_calls
    assert out.content == "好的"


def test_parse_non_json_content_passthrough():
    resp = {
        "choices": [
            {"message": {"content": "这就是一句普通回答", "tool_calls": None}}
        ]
    }
    out = parse(resp)
    assert not out.has_tool_calls
    assert out.content == "这就是一句普通回答"


def test_parse_empty_choices():
    assert not parse({"choices": []}).has_tool_calls
