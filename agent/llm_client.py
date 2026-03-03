"""LLM 客户端：OpenAI 兼容接口，请求头带 session_id。"""
import httpx
from config import settings

try:
    from logging_conf import get_logger
    _log = get_logger("llm_client")
except Exception:
    _log = None

LLM_PORT = settings.llm_port
MAX_LLM_RETRIES = 1 if settings.enable_retry else 0


async def chat_completions(
    model_ip: str,
    session_id: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    """
    调用 LLM POST /v1/chat/completions。
    请求头必须带 session_id。
    返回完整响应体，含 choices[0].message（可能含 content 和/或 tool_calls）。
    """
    url = f"http://{model_ip.rstrip('/')}:{LLM_PORT}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "session_id": session_id}
    body = {
        "model": "",
        "messages": messages,
        "stream": False,
    }
    if tools is not None:
        body["tools"] = tools
    last_error = None
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, json=body, headers=headers)
                if _log:
                    usage = {}
                    if r.status_code == 200:
                        try:
                            usage = (r.json().get("usage") or {})
                        except Exception:
                            pass
                    _log.info("llm_request", url=url, status=r.status_code, usage=usage)
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            last_error = e
            if _log:
                _log.warning("llm_error", error=str(e))
            if attempt == MAX_LLM_RETRIES:
                raise
    if last_error:
        raise last_error
    return {}
