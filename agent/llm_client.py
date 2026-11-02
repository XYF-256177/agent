"""OpenAI 兼容 LLM 客户端，支持 DeepSeek / DashScope / OpenAI 等任意兼容接口。"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class LLMError(Exception):
    """LLM 调用异常。"""


class LLMClient:
    """极简的 OpenAI 兼容 chat 客户端，只负责"发请求、拿原始响应"。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = (
            base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        ).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")
        self.timeout = timeout

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """调用 chat/completions，返回原始响应 JSON。

        不在这里做任何解析，保证职责单一；解析交给 parser 模块。
        """
        if not self.api_key:
            raise LLMError("缺少 LLM_API_KEY，请在 .env 文件或环境变量中配置")

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"LLM 请求失败: HTTP {exc.response.status_code} {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise LLMError(f"LLM 网络异常: {exc}") from exc
