"""工具执行器：根据 LLM tool_calls 调用租房 API，支持并行执行。"""
import asyncio
import json
from tools import rent_api

# operationId -> 实际异步函数
_TOOL_FUNCS = {
    "get_landmarks": rent_api.get_landmarks,
    "get_landmark_by_name": rent_api.get_landmark_by_name,
    "search_landmarks": rent_api.search_landmarks,
    "get_landmark_by_id": rent_api.get_landmark_by_id,
    "get_landmark_stats": rent_api.get_landmark_stats,
    "get_house_by_id": rent_api.get_house_by_id,
    "get_house_listings": rent_api.get_house_listings,
    "get_houses_by_community": rent_api.get_houses_by_community,
    "get_houses_by_platform": rent_api.get_houses_by_platform,
    "get_houses_nearby": rent_api.get_houses_nearby,
    "get_nearby_landmarks": rent_api.get_nearby_landmarks,
    "get_house_stats": rent_api.get_house_stats,
    "rent_house": rent_api.rent_house,
    "terminate_rental": rent_api.terminate_rental,
    "take_offline": rent_api.take_offline,
}


async def _run_one(tool_call_id: str, tool_name: str, arguments: dict) -> tuple[str, bool, str]:
    """执行单个工具调用，返回 (tool_call_id, success, output_str)。"""
    fn = _TOOL_FUNCS.get(tool_name)
    if not fn:
        return tool_call_id, False, json.dumps({"error": f"unknown tool: {tool_name}"}, ensure_ascii=False)
    try:
        result = await fn(**arguments)
        return tool_call_id, True, json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return tool_call_id, False, json.dumps({"error": str(e)}, ensure_ascii=False)


async def execute_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """
    执行一批 tool_calls，并行执行。
    tool_calls 每项含: id, function.name, function.arguments (JSON 字符串或已解析 dict)。
    返回列表，每项 { "tool_call_id": id, "success": bool, "output": str }，
    用于组装 OpenAI 格式的 tool 消息。
    """
    tasks = []
    ids = []
    for tc in tool_calls:
        tid = tc.get("id", "")
        name = tc.get("function", {}).get("name", "") or tc.get("name", "")
        raw = tc.get("function", {}).get("arguments", "") or tc.get("arguments", "")
        if isinstance(raw, str):
            try:
                args = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw or {}
        ids.append(tid)
        tasks.append(_run_one(tid, name, args))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            out.append({
                "tool_call_id": ids[i],
                "success": False,
                "output": json.dumps({"error": str(r)}, ensure_ascii=False),
            })
        else:
            tid, success, output = r
            out.append({
                "tool_call_id": tid,
                "success": success,
                "output": output,
            })
    return out
