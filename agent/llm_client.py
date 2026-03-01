"""LLM 模型调用：封装 model_ip:8888，支持 tools"""
import json
import time
from typing import Any

import httpx

from agent.api_logger import log_llm_api


def call_llm(
    model_ip: str,
    messages: list[dict[str, Any]],
    session_id: str,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    调用 LLM 模型。
    model_ip: 模型服务 IP（端口固定 8888）
    messages: 对话消息列表
    session_id: 会话 ID，需放在请求头
    tools: 可选，工具定义
    """
    url = f"http://{model_ip}:8888/v1/chat/completions"
    headers = {"Content-Type": "application/json", "session_id": session_id}
    payload: dict[str, Any] = {
        "model": "",
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        tool_calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        log_llm_api(
            url, len(messages), bool(tools), resp.status_code,
            (time.perf_counter() - start) * 1000,
            tool_calls_count=len(tool_calls),
            content_preview=str(content)[:150],
        )
        return data
    except Exception as e:
        log_llm_api(
            url, len(messages), bool(tools),
            getattr(e, "response", None) and getattr(e.response, "status_code", 0) or 0,
            (time.perf_counter() - start) * 1000,
            error=str(e),
        )
        raise


def extract_content(response: dict) -> str:
    """从 LLM 响应中提取 content"""
    choices = response.get("choices", [])
    if not choices:
        return ""
    msg = choices[0].get("message", {})
    return msg.get("content", "") or ""


def extract_tool_calls(response: dict) -> list[dict]:
    """从 LLM 响应中提取 tool_calls"""
    choices = response.get("choices", [])
    if not choices:
        return []
    msg = choices[0].get("message", {})
    return msg.get("tool_calls", []) or []


def parse_tool_call_args(tool_call: dict) -> tuple[str, dict]:
    """解析 tool_call，返回 (function_name, arguments_dict)"""
    func = tool_call.get("function", {})
    name = func.get("name", "")
    args_str = func.get("arguments", "{}")
    try:
        args = json.loads(args_str) if args_str else {}
    except json.JSONDecodeError:
        args = {}
    return name, args
