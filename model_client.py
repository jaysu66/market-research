"""统一模型调用封装 — 所有通道都走 OpenAI 兼容格式"""

import httpx
import json
import os
import re
import time
from pathlib import Path

# 自动加载 .env 文件
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


# 通道配置
PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "env_key": "SILICONFLOW_API_KEY",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "env_key": "KIMI_API_KEY",
    },
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "env_key": "MINIMAX_API_KEY",
    },
    "xiaomi": {
        "base_url": "https://api.xiaomimimo.com/v1",
        "env_key": "XIAOMI_API_KEY",
    },
    "gateway": {
        "base_url": "http://192.168.43.59:3000/v1",
        "env_key": "GATEWAY_API_KEY",
    },
}


def call_model(
    provider: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8192,
    response_format: dict | None = None,
    retries: int = 2,
    timeout: int = 120,
) -> dict:
    """
    统一模型调用接口

    Args:
        provider: 通道名 (openrouter/siliconflow/dashscope/...)
        model: 模型ID
        messages: [{"role": "user", "content": "..."}]
        temperature: 温度
        max_tokens: 最大输出token
        response_format: 如 {"type": "json_object"}
        retries: 重试次数
        timeout: 超时秒数

    Returns:
        {"content": "模型输出文本", "usage": {...}, "model": "...", "provider": "..."}
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}")

    api_key = os.environ.get(cfg["env_key"], "")
    if not api_key:
        raise ValueError(f"Missing API key: {cfg['env_key']}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        body["response_format"] = response_format

    url = f"{cfg['base_url']}/chat/completions"

    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            content = choice["message"]["content"]

            # 过滤 <think>...</think> 思维链标签（MiniMax/DeepSeek-R1等模型）
            content = re.sub(r'<think>[\s\S]*?</think>\s*', '', content).strip()

            return {
                "content": content,
                "usage": data.get("usage", {}),
                "model": data.get("model", model),
                "provider": provider,
            }
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout,
                httpx.RemoteProtocolError) as e:
            if attempt < retries:
                wait = 5 * (attempt + 1)
                print(f"  [Retry {attempt+1}/{retries}] {type(e).__name__}: {e}, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"API call failed after {retries + 1} attempts: {e}")


# ========== 3类任务模型配置 ==========
# 低级任务（Step 7/9/11：提取+缺口检查）→ D1指令遵循 + D2结构化提取
TASK_LOW = {
    "provider": os.environ.get("TASK_LOW_PROVIDER", "siliconflow"),
    "model": os.environ.get("TASK_LOW_MODEL", "Qwen/Qwen3-8B"),
}

# 中级任务（Step 14：自查纠错）→ D5审查纠错
TASK_MID = {
    "provider": os.environ.get("TASK_MID_PROVIDER", "minimax"),
    "model": os.environ.get("TASK_MID_MODEL", "MiniMax-M2.7"),
}

# 高级任务（Step 12/13/15/19：写报告+质疑+跨州对比）→ D3长文写作 + D4数据忠实 + D6批判思维
TASK_HIGH = {
    "provider": os.environ.get("TASK_HIGH_PROVIDER", "minimax"),
    "model": os.environ.get("TASK_HIGH_MODEL", "MiniMax-M2.7"),
}


def call_task(tier: str, messages: list[dict], temperature: float = 0.7,
              max_tokens: int = 8192, timeout: int = 120, **kwargs) -> dict:
    """按任务层级调用对应模型，失败自动fallback

    Args:
        tier: "low" / "mid" / "high"
    """
    cfg = {"low": TASK_LOW, "mid": TASK_MID, "high": TASK_HIGH}[tier]
    try:
        return call_model(
            provider=cfg["provider"],
            model=cfg["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
    except RuntimeError as e:
        # Fallback: MiniMax失败 → 切SiliconFlow DeepSeek-V3.2
        if cfg["provider"] == "minimax":
            print(f"  [Fallback] {cfg['provider']}/{cfg['model']} failed, trying siliconflow/deepseek-ai/DeepSeek-V3...")
            return call_model(
                provider="siliconflow",
                model="deepseek-ai/DeepSeek-V3",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs,
            )
        raise


def call_sonar(query: str) -> dict:
    """调用 Perplexity Sonar 搜索"""
    return call_model(
        provider="openrouter",
        model="perplexity/sonar",
        messages=[{"role": "user", "content": query}],
        temperature=0.1,
        max_tokens=4096,
    )
