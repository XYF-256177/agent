"""滑动窗口限流器测试（用假时钟精确控制时间）。"""
from rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    """可手动推进的假时钟。"""

    def __init__(self, start=0.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_within_limit():
    clock = FakeClock()
    r = SlidingWindowRateLimiter(window_seconds=1.0, limit=3, clock=clock)
    assert [r.allow("u1") for _ in range(3)] == [True, True, True]


def test_exceed_limit():
    clock = FakeClock()
    r = SlidingWindowRateLimiter(window_seconds=1.0, limit=3, clock=clock)
    assert [r.allow("u1") for _ in range(5)] == [True, True, True, False, False]


def test_window_slides_and_recovers():
    """窗口滑动后应恢复放行：占满 → 拒绝 → 推进超过窗口 → 再放行。"""
    clock = FakeClock()
    r = SlidingWindowRateLimiter(window_seconds=1.0, limit=3, clock=clock)
    for _ in range(3):
        assert r.allow("u1") is True
    assert r.allow("u1") is False  # 第 4 次被拒
    clock.advance(1.1)  # 滑动窗口，旧请求全部过期
    assert r.allow("u1") is True  # 恢复放行


def test_per_user_isolated():
    clock = FakeClock()
    r = SlidingWindowRateLimiter(window_seconds=1.0, limit=2, clock=clock)
    for _ in range(2):
        r.allow("u1")
    assert r.allow("u1") is False  # u1 已满
    assert r.allow("u2") is True  # u2 不受影响


def test_cleanup_removes_inactive_user():
    clock = FakeClock()
    r = SlidingWindowRateLimiter(window_seconds=1.0, limit=3, clock=clock)
    r.allow("u1")
    assert r.active_users() == 1
    clock.advance(2.0)  # 超过一个窗口未活跃
    removed = r.cleanup()
    assert removed == 1
    assert r.active_users() == 0


def test_max_users_eviction():
    clock = FakeClock()
    r = SlidingWindowRateLimiter(
        window_seconds=1.0, limit=3, clock=clock, max_users=2
    )
    r.allow("u1")  # t=0
    clock.advance(0.5)
    r.allow("u2")  # t=0.5
    clock.advance(0.5)
    r.allow("u3")  # t=1.0，触发容量保护，驱逐最久未活跃的 u1
    assert r.active_users() <= 2
    assert r.allow("u1") is True  # u1 记录已被清除，重新计算
