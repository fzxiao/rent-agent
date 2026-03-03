"""对话处理主逻辑：LLM 调用 + 工具循环，直至生成最终回复。"""
import json
import time
from pathlib import Path

from config import settings
from .llm_client import chat_completions
from .prompts import SYSTEM_PROMPT, normalize_house_response
from . import session
from tools.definitions import get_tools
from tools.executor import execute_tool_calls

MAX_TURN = 20


async def handle_chat(model_ip: str, session_id: str, message: str) -> tuple[str, list[dict]]:
    """
    处理单次用户消息：维护会话、调用 LLM、执行工具，返回 (response 字符串, tool_results)。
    """
    await session.ensure_session_inited_async(session_id)
    session.append_message(session_id, "user", message)

    tools = get_tools()
    messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}] + session.get_messages(session_id)
    tool_results_collect: list[dict] = []

    for _ in range(MAX_TURN):
        resp = await chat_completions(model_ip, session_id, messages_for_llm, tools)
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = (msg.get("content") or "").strip()
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            session.append_message(
                session_id,
                "assistant",
                content=content or None,
                tool_calls=tool_calls,
            )
            results = await execute_tool_calls(tool_calls)
            for r in results:
                tool_results_collect.append({"tool_call_id": r["tool_call_id"], "success": r["success"], "output": r["output"][:500]})
                session.append_tool_message(session_id, r["tool_call_id"], r["output"])
            messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}] + session.get_messages(session_id)
            continue

        if content:
            normalized = normalize_house_response(content)
            _export_trace(session_id, message, session.get_messages(session_id), normalized)
            return normalized, tool_results_collect
        _export_trace(session_id, message, session.get_messages(session_id), "")
        return "", tool_results_collect

    _export_trace(session_id, message, session.get_messages(session_id), "")
    return "", tool_results_collect


def _export_trace(session_id: str, input_message: str, messages: list, response: str) -> None:
    """请求结束后将完整 trace 写入 logs/traces/。"""
    if not settings.enable_trace_export:
        return
    try:
        trace_dir = Path(settings.trace_dir)
        trace_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = trace_dir / f"{session_id}_{ts}.json"
        payload = {
            "session_id": session_id,
            "input_message": input_message,
            "messages": messages,
            "response": response,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
