"""Agent 核心处理逻辑：需求理解、工具调用、响应格式化"""
import json
import time
from typing import Any

import httpx

from agent.api_logger import log_request_end, log_request_start, log_tool_execution
from agent.llm_client import (
    call_llm,
    extract_content,
    extract_tool_calls,
    parse_tool_call_args,
)
from agent.rental_client import RentalAPIClient
from agent.session import (
    append_message,
    get_last_house_ids,
    get_or_create_messages,
    set_last_house_ids,
)
from agent.tools import RENTAL_TOOLS

# 记录已初始化的 session，避免重复 init
_initialized_sessions: set[str] = set()


def _ensure_session_init(rental: RentalAPIClient, session_id: str) -> None:
    """新 session 时调用房源数据重置"""
    if session_id not in _initialized_sessions:
        try:
            rental.init()
            _initialized_sessions.add(session_id)
        except Exception:
            pass  # Mock 环境可能无 init 接口


def _execute_tool(rental: RentalAPIClient, name: str, args: dict) -> str:
    """执行工具调用，返回结果 JSON 字符串"""
    try:
        if name == "houses_init":
            result = rental.init()
        elif name == "get_houses_by_platform":
            result = rental.get_houses_by_platform(**{k: v for k, v in args.items() if v is not None})
        elif name == "get_house":
            result = rental.get_house(house_id=args["house_id"])
        elif name == "rent_house":
            result = rental.rent_house(
                house_id=args["house_id"],
                listing_platform=args.get("listing_platform", "安居客"),
            )
        elif name == "get_landmark_by_name":
            result = rental.get_landmark_by_name(name=args["name"])
        elif name == "get_houses_nearby":
            result = rental.get_houses_nearby(
                landmark_id=args["landmark_id"],
                max_distance=args.get("max_distance", 2000),
                page=args.get("page", 1),
                page_size=args.get("page_size", 10),
            )
        else:
            return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _extract_house_ids_from_result(tool_result: str, tool_name: str) -> list[str]:
    """从工具返回结果中提取房源 ID 列表"""
    try:
        data = json.loads(tool_result)
    except json.JSONDecodeError:
        return []
    if "error" in data:
        return []
    # 兼容不同 API 响应结构
    items: list | dict = data.get("data", data)
    if isinstance(items, dict):
        items = items.get("items", items.get("data", []))
    if not isinstance(items, list):
        # get_house 返回单条，data 可能是 dict
        single = data.get("data", data)
        if isinstance(single, dict) and "house_id" in single:
            return [single["house_id"]]
        if isinstance(single, dict) and "id" in single:
            return [single["id"]]
        return []
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and "house_id" in item:
            ids.append(item["house_id"])
        elif isinstance(item, dict) and "id" in item:
            ids.append(item["id"])
        elif isinstance(item, str) and item.startswith("HF_"):
            ids.append(item)
    return ids[:5]  # 最多 5 套


def handle_chat(
    model_ip: str,
    session_id: str,
    message: str,
    user_id: str = "test_user_001",
    rental_base_url: str | None = None,
) -> dict[str, Any]:
    """
    处理单轮聊天请求。
    返回: { response, status, tool_results, duration_ms }
    """
    start = time.time()
    log_request_start(session_id, message)

    rental = RentalAPIClient(user_id=user_id)
    if rental_base_url:
        rental.base_url = rental_base_url

    _ensure_session_init(rental, session_id)

    messages = get_or_create_messages(session_id, message)
    append_message(session_id, "user", message)

    tool_results: list[dict] = []
    house_ids: list[str] = []
    did_housing_query = False  # 是否执行过房源查询，用于决定是否返回 JSON
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        try:
            response = call_llm(model_ip, messages, session_id, tools=RENTAL_TOOLS)
        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start) * 1000)
            log_request_end(session_id, "error", duration_ms)
            return {
                "response": f"LLM 调用失败: {e.response.status_code}",
                "status": "error",
                "tool_results": tool_results,
                "duration_ms": duration_ms,
            }
        content = extract_content(response)
        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            # 无工具调用，直接返回
            append_message(session_id, "assistant", content)
            # 若执行过房源查询或 session 中有上次结果，需格式化为 JSON
            final_house_ids = house_ids or get_last_house_ids(session_id)
            if did_housing_query or final_house_ids:
                response_text = json.dumps(
                    {"message": content, "houses": final_house_ids},
                    ensure_ascii=False,
                )
            else:
                response_text = content
            duration_ms = int((time.time() - start) * 1000)
            log_request_end(session_id, "success", duration_ms)
            return {
                "response": response_text,
                "status": "success",
                "tool_results": tool_results,
                "duration_ms": duration_ms,
            }

        # 执行工具调用
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": content or None,
            "tool_calls": [
                {
                    "id": tc.get("id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": tc.get("function", {}).get("arguments", "{}"),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ],
        }
        messages.append(assistant_msg)

        for tc in tool_calls:
            name, args = parse_tool_call_args(tc)
            t0 = time.perf_counter()
            result = _execute_tool(rental, name, args)
            log_tool_execution(name, args, result, (time.perf_counter() - t0) * 1000)
            tool_results.append({"tool": name, "args": args, "result": result[:500]})

            # 收集房源 ID
            if name in ("get_houses_by_platform", "get_houses_nearby", "get_house"):
                did_housing_query = True
                ids = _extract_house_ids_from_result(result, name)
                if ids:
                    house_ids = ids
                    set_last_house_ids(session_id, ids)
            elif name == "rent_house":
                house_ids = [args["house_id"]]
                set_last_house_ids(session_id, house_ids)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

    # 超迭代退出
    duration_ms = int((time.time() - start) * 1000)
    log_request_end(session_id, "error", duration_ms)
    return {
        "response": "处理超时，请重试。",
        "status": "error",
        "tool_results": tool_results,
        "duration_ms": duration_ms,
    }
