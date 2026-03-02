"""
LLM 客户端：调用 model_ip:8888 的 chat completions 接口。
要求 LLM 返回结构化 JSON：intent, reply, action/actions。
"""
import json
import re
from typing import Any, Optional

import httpx

from .config import LLM_PORT, MAX_SUBWAY_DIST_ONE_BED, MAX_SUBWAY_DIST_TWO_BED_PLUS, MAX_HOUSES

SYSTEM_PROMPT = """你是租房助手，根据用户需求选择并调用租房 API。若需求不清晰则追问，不调用 API。

输出格式：必须输出一个 JSON 对象，且只输出该 JSON，不要前后缀、不要 markdown 代码块。格式如下：

当需要调 API 时：
{
  "intent": "query_house" | "rent" | "terminate" | "offline" | "need_clarification" | "chat",
  "reply": "",
  "action": {
    "api": "接口 operationId，如 get_houses_by_platform, rent_house 等",
    "params": { "参数名": "值", ... }
  }
}

当仅追问或聊天时（不调 API）：
{
  "intent": "need_clarification" | "chat",
  "reply": "给用户的自然语言回复",
  "action": null
}

若需连续多个 API（如先查地标再 nearby），用 actions 数组：
{
  "intent": "query_house",
  "reply": "",
  "actions": [{"api": "get_landmark_by_name", "params": {...}}, {"api": "get_houses_nearby", "params": {...}}]
}

参数说明：
- district: 行政区，如 海淀、西城、朝阳、东城
- bedrooms: 卧室数，"1" 或 "2"
- max_price: 最高月租金（元）
- min_price: 最低月租金
- max_subway_dist: 最大地铁距离（米）。近地铁：一居用 1000，两居及以上用 800；离地铁 500 米以内用 500
- sort_by: price/area/subway（按地铁距离用 subway）
- sort_order: asc/desc（从近到远用 asc）
- page: 页码，默认 1
- page_size: 每页条数，默认 10
- listing_platform: 链家/安居客/58同城，租房必填，默认安居客
- house_id: 房源 ID，如 HF_906
- community: 小区名
- landmark_id: 地标 ID
- name: 地标名称（用于 get_landmark_by_name）
- decoration: 精装/简装
- rental_type: 整租/合租

指代消解：
- "还有其他的吗"：用上一轮查询条件，page 加 1
- "就租最近的那套/第一套"：house_id 取上一轮候选列表第一条
- "租第二套"：取第二条

只输出 JSON，不要其他文字。"""


def _normalize_max_subway_dist(params: dict[str, Any]) -> None:
    """根据 bedrooms 自动设置 max_subway_dist（近地铁时）"""
    if "max_subway_dist" in params:
        return
    bedrooms = params.get("bedrooms")
    if bedrooms is None:
        return
    try:
        if str(bedrooms) == "1":
            params["max_subway_dist"] = MAX_SUBWAY_DIST_ONE_BED
        else:
            params["max_subway_dist"] = MAX_SUBWAY_DIST_TWO_BED_PLUS
    except Exception:
        return


def _ensure_page_size(params: dict[str, Any]) -> None:
    if "page_size" not in params:
        params["page_size"] = 10


async def call_llm(
    model_ip: str,
    messages: list[dict[str, str]],
    session_id: str,
    context_summary: str = "",
) -> dict[str, Any]:
    """
    调用 LLM，返回解析后的结构化信息。
    返回 {"intent": str, "reply": str, "action": dict|None, "actions": list|None, "raw": str}
    """
    url = f"http://{model_ip}:{LLM_PORT}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "session_id": session_id}

    user_content = "\n\n".join(
        [f"{m['role']}: {m['content']}" for m in messages]
    )
    if context_summary:
        user_content += f"\n\n[上下文记忆]\n{context_summary}"

    payload = {
        "model": "",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        return {
            "intent": "chat",
            "reply": f"抱歉，调用模型失败：{resp.status_code}",
            "action": None,
            "actions": None,
            "raw": resp.text,
        }

    data = resp.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return {"intent": "chat", "reply": "模型返回格式异常", "action": None, "actions": None, "raw": str(data)}

    # 解析 JSON
    parsed = _parse_llm_json(content)
    if not parsed:
        return {"intent": "chat", "reply": content or "解析失败", "action": None, "actions": None, "raw": content}

    action = parsed.get("action")
    actions = parsed.get("actions")

    if action:
        params = action.get("params") or {}
        _normalize_max_subway_dist(params)
        _ensure_page_size(params)
        action["params"] = params

    if actions:
        for a in actions:
            params = a.get("params") or {}
            _normalize_max_subway_dist(params)
            _ensure_page_size(params)
            a["params"] = params

    return {
        "intent": parsed.get("intent", "chat"),
        "reply": parsed.get("reply", ""),
        "action": action,
        "actions": actions,
        "raw": content,
    }


def _parse_llm_json(content: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON"""
    content = content.strip()
    # 移除可能的 markdown 代码块
    if content.startswith("```"):
        content = re.sub(r"^```\w*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # 尝试提取 {...}
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


def extract_house_ids_from_response(api_result: dict) -> list[str]:
    """从 get_houses_by_platform / get_houses_nearby 等接口的返回中提取房源 ID 列表"""
    if not isinstance(api_result, dict):
        return []
    data = api_result.get("data")
    if data is None:
        return []
    # 支持 {"code":0, "data": {"items": [...], "total": N}} 或 {"items": [...], "total": N}
    items = None
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, dict):
            items = inner.get("items") or inner.get("data")
        elif isinstance(inner, list):
            items = inner
        else:
            items = data.get("items") or data.get("data")
    elif isinstance(data, list):
        items = data
    if not isinstance(items, list):
        return []
    ids = []
    for item in items[:MAX_HOUSES]:
        if isinstance(item, dict):
            hid = item.get("house_id") or item.get("id")
        else:
            hid = None
        if hid:
            ids.append(str(hid))
    return ids
