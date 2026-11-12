"""长期记忆与 token 估算测试。"""
from agent.memory import Memory, estimate_tokens


def test_remember_and_summarize():
    m = Memory()
    m.remember("A", "我叫", "小明")
    m.remember("A", "我喜欢", "篮球")
    summary = m.summarize("A")
    assert "小明" in summary
    assert "篮球" in summary


def test_remember_overwrite_same_key():
    m = Memory()
    m.remember("A", "城市", "北京")
    m.remember("A", "城市", "上海")
    summary = m.summarize("A")
    assert "上海" in summary
    assert "北京" not in summary


def test_recall_by_keyword():
    m = Memory()
    m.remember("A", "我叫", "小明")
    m.remember("A", "城市", "北京")
    got = m.recall("A", "北京")
    assert got and got[0]["key"] == "城市"


def test_recall_fallback_to_recent_when_no_match():
    m = Memory()
    m.remember("A", "我叫", "小明")
    got = m.recall("A", "完全不相关的词")
    assert got and got[0]["key"] == "我叫"


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 2


def test_recall_chinese_bigram():
    """验证中文按 bigram 分词后能被正确召回。

    原实现用空格分词对中文完全失效；修复后应能命中。
    """
    m = Memory()
    m.remember("A", "学校", "梧州学院")
    m.remember("A", "专业", "数据科学")
    got = m.recall("A", "梧州学院在哪里")
    assert got and "梧州学院" in got[0]["value"]
