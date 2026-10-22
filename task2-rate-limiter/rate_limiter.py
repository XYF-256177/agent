# -*- coding: utf-8 -*-
"""滑动窗口限流器（单机版）—— 架构设计题第 6 题的可运行实现。

设计要点：
  - 数据结构：dict[userId] -> deque[时间戳]，队首最旧、队尾最新；
  - 任意连续 window_seconds 内每个用户最多 limit 次请求；
  - 时间来源可注入 clock（默认 time.monotonic），便于测试精确控制时间；
  - 不活跃用户清理：惰性淘汰 + cleanup() 主动清理 + max_users 容量保护。
"""
from collections import deque
from typing import Callable, Deque, Dict, Optional
import time


class SlidingWindowRateLimiter:
    def __init__(
        self,
        window_seconds: float,
        limit: int,
        clock: Optional[Callable[[], float]] = None,
        max_users: Optional[int] = None,
    ):
        assert window_seconds > 0 and limit > 0
        self.window = window_seconds
        self.limit = limit
        self._clock = clock or time.monotonic
        self._max_users = max_users
        self._buckets: Dict[str, Deque] = {}
        self._last_seen: Dict[str, float] = {}

    def allow(self, user_id: str) -> bool:
        now = self._clock()
        q = self._buckets.get(user_id)
        if q is None:
            q = deque()
            self._buckets[user_id] = q

        # 1. 淘汰窗口外的旧时间戳（滑动窗口核心）
        while q and now - q[0] >= self.window:
            q.popleft()

        self._last_seen[user_id] = now

        # 2. 判定 + 更新
        if len(q) < self.limit:
            q.append(now)
            self._evict_if_needed()
            return True
        return False

    def cleanup(self) -> int:
        """主动清理：删除队列为空、或已超过一个窗口未活跃的用户。返回清理数量。"""
        now = self._clock()
        stale = [
            uid
            for uid in self._buckets
            if not self._buckets[uid]
            or now - self._last_seen.get(uid, now) >= self.window
        ]
        for uid in stale:
            self._buckets.pop(uid, None)
            self._last_seen.pop(uid, None)
        return len(stale)

    def active_users(self) -> int:
        return len(self._buckets)

    def _evict_if_needed(self) -> None:
        """容量保护：用户数超上限时，驱逐最久未活跃的用户。"""
        if self._max_users and len(self._buckets) > self._max_users:
            oldest = min(self._last_seen, key=self._last_seen.get)
            self._buckets.pop(oldest, None)
            self._last_seen.pop(oldest, None)


def main():
    print("滑动窗口限流器演示：1 秒内每个用户最多 3 次请求\n")
    r = SlidingWindowRateLimiter(window_seconds=1.0, limit=3)

    for i in range(5):
        ok = r.allow("u1")
        print(f"第 {i + 1} 次请求 u1 -> {'放行' if ok else '拒绝'}")

    print("\n换一个用户不受影响：")
    print("u2 请求 ->", "放行" if r.allow("u2") else "拒绝")


if __name__ == "__main__":
    main()
