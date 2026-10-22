# -*- coding: utf-8 -*-
"""一键验证脚本：先跑 pytest 单元测试，再跑真实 API 冒烟测试。

用法（在项目根目录执行）：
    python verify_all.py

说明：
  - Step 1 单元测试离线运行，不消耗 token；
  - Step 2 冒烟测试会调用真实 LLM API，需先配置好 .env 中的 LLM_API_KEY。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def _ensure_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _sep(title):
    bar = "=" * 62
    print(f"\n{bar}\n  {title}\n{bar}\n", flush=True)


def _run(args):
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", cwd=ROOT
    )
    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    return result.returncode


def main():
    _ensure_utf8()

    _sep("Step 1/2 : pytest 单元测试（离线）")
    rc1 = _run([sys.executable, "-m", "pytest", "-v"])

    _sep("Step 2/2 : 真实 API 冒烟测试")
    rc2 = _run([sys.executable, os.path.join("examples", "verify.py")])

    _sep("验证结果汇总")
    status1 = "[PASS]" if rc1 == 0 else "[FAIL]"
    status2 = "[PASS]" if rc2 == 0 else "[FAIL]"
    print(f"  单元测试        : {status1}  (exit code {rc1})")
    print(f"  真实 API 冒烟   : {status2}  (exit code {rc2})")

    if rc1 == 0 and rc2 == 0:
        print("\n  全部验证通过。")
        return 0
    print("\n  存在失败项，请检查上方输出。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
