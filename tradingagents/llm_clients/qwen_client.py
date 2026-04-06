# tradingagents/llm_clients/qwen_client.py
"""
Qwen（通义千问）LLM 客户端

通过阿里云百炼平台（DashScope）的 OpenAI 兼容接口接入 Qwen 系列模型。

接入方式：
- API Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1
- API Key 环境变量: DASHSCOPE_API_KEY（或 QWEN_API_KEY）
- 接口格式: OpenAI Chat Completions 兼容

支持的 Qwen 模型：
- qwen-max           : 旗舰模型，综合能力最强
- qwen-plus          : 平衡能力与成本
- qwen-turbo         : 快速，低延迟
- qwen-long          : 超长上下文（1M token）
- qwen2.5-72b-instruct: Qwen2.5 最大开源模型
- qwen2.5-32b-instruct: Qwen2.5 大型开源
- qwen2.5-7b-instruct : Qwen2.5 轻量

使用方式：
    from tradingagents.llm_clients import create_llm_client
    client = create_llm_client(provider="qwen", model="qwen-max")
    llm = client.get_llm()
"""

import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient, normalize_content

# DashScope OpenAI 兼容端点
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class NormalizedChatQwen(ChatOpenAI):
    """ChatOpenAI 包装，使用 DashScope 端点并规范化内容输出。"""

    def invoke(self, input, config=None, **kwargs):
        return normalize_content(super().invoke(input, config, **kwargs))


class QwenClient(BaseLLMClient):
    """
    阿里云通义千问（Qwen）客户端。

    通过 DashScope 平台的 OpenAI 兼容接口调用 Qwen 系列模型。
    API Key 优先级：
    1. 显式传入的 api_key 参数
    2. DASHSCOPE_API_KEY 环境变量
    3. QWEN_API_KEY 环境变量（备用）
    """

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        """返回配置好的 Qwen（通过 DashScope）ChatOpenAI 实例。"""
        # API Key 解析
        api_key = (
            self.kwargs.get("api_key")
            or os.environ.get("DASHSCOPE_API_KEY")
            or os.environ.get("QWEN_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "Qwen API key not found. Please set DASHSCOPE_API_KEY or QWEN_API_KEY "
                "environment variable, or pass api_key explicitly."
            )

        # 端点：优先使用传入的 base_url，否则用 DashScope 默认端点
        base_url = self.base_url or DASHSCOPE_BASE_URL

        llm_kwargs = {
            "model": self.model,
            "base_url": base_url,
            "api_key": api_key,
        }

        # 透传通用参数
        for key in ("timeout", "max_retries", "callbacks", "http_client", "http_async_client"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return NormalizedChatQwen(**llm_kwargs)

    def validate_model(self) -> bool:
        """Qwen 模型名称校验（宽松校验）。"""
        known_prefixes = ("qwen", "qwen2", "qwen2.5", "qwen3")
        model_lower = self.model.lower()
        return any(model_lower.startswith(p) for p in known_prefixes)
