"""LLM 客户端：调用比赛 LLM 或 Mock 返回结构化 JSON。"""

import json
import re
from typing import Any

import httpx

from rent_agent import logger
from rent_agent.config import LLM_PORT, USE_MOCK


def call_llm(
    model_ip: str,
    session_id: str,
    messages: list[dict[str, str]],
    tools: list[dict] | None = None,
) -> dict:
    """
    调用 LLM POST /v1/chat/completions。
    返回 choices[0].message 内容。
    """
    url = f"http://{model_ip}:{LLM_PORT}/v1/chat/completions"
    body = {
        "model": "",
        "messages": messages,
        "stream": False,
    }
    if tools:
        body["tools"] = tools

    if USE_MOCK:
        # Mock：不真正调 LLM，返回空或由 rule 层处理
        content = ""
        logger.log_api_call(
            session_id=session_id,
            call_type="llm",
            api_name="chat_completions",
            params={"messages_count": len(messages), "tools": bool(tools)},
            status_code=200,
            response_summary="mock (rule-based in test)",
            url=url,
        )
        return {"content": content, "finish_reason": "stop"}

    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            url,
            json=body,
            headers={"Content-Type": "application/json", "session_id": session_id},
        )
        resp = r.json() if r.content else {}
        msg = resp.get("choices", [{}])[0].get("message", {})
        logger.log_api_call(
            session_id=session_id,
            call_type="llm",
            api_name="chat_completions",
            params={"messages_count": len(messages)},
            status_code=r.status_code,
            response_summary={"content_preview": str(msg.get("content", ""))[:200]},
            url=url,
        )
        return msg


def parse_llm_json(content: str) -> dict | None:
    """从 LLM 回复中解析 JSON。"""
    if not content or not content.strip():
        return None
    content = content.strip()
    # 尝试提取 ```json ... ``` 或纯 JSON
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if m:
        content = m.group(1).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None
