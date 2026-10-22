"""session 隔离测试。"""
from agent.session import SessionManager


def test_sessions_are_isolated():
    sm = SessionManager()
    s1 = sm.get_or_create("w1", "A")
    s2 = sm.get_or_create("w2", "A")
    s1.messages.append({"role": "user", "content": "窗口1的消息"})
    assert len(s1.messages) == 1
    assert len(s2.messages) == 0
    assert sm.get_or_create("w1", "A") is s1


def test_get_or_create_reuses_same_session():
    sm = SessionManager()
    assert sm.get_or_create("w1") is sm.get_or_create("w1")


def test_reset():
    sm = SessionManager()
    sm.get_or_create("w1")
    sm.reset("w1")
    assert sm.get("w1") is None
