"""LLM 客户端 - 调用 model_ip:8888"""
import json
import logging
import re
from typing import Any

import httpx

from .config import LLM_PORT

logger = logging.getLogger(__name__)


async def call_llm(
    model_ip: str,
    messages: list[dict[str, str]],
    session_id: str,
) -> str:
    """
    调用 LLM，返回 assistant 的 content 文本。
    请求头必须带 session_id。
    """
    url = f"http://{model_ip}:{LLM_PORT}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "session_id": session_id}
    payload = {
        "model": "",
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            body = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                logger.error("LLM error: %s %s", resp.status_code, body)
                return ""

            choices = body.get("choices", [])
            if not choices:
                return ""
            msg = choices[0].get("message", {})
            return msg.get("content", "").strip()
    except Exception as e:
        logger.exception("LLM call error: %s", e)
        return ""


def parse_structured_output(content: str) -> dict[str, Any] | None:
    """
    解析 LLM 返回的 JSON 结构化输出。
    支持：纯 JSON、```json ... ``` 包裹。
    返回格式: { intent, reply?, action?, actions? }
    """
    if not content:
        return None

    # 尝试提取 ```json ... ``` 块
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if json_match:
        content = json_match.group(1).strip()

    # 尝试提取 { ... } 块
    brace_match = re.search(r"\{[\s\S]*\}", content)
    if brace_match:
        content = brace_match.group(0)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None
