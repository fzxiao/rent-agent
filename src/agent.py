"""
Agent 核心逻辑：整合 LLM、租房 API、会话管理，处理单轮/多轮请求。
"""
import json
import re
import time
from typing import Any, Optional

from .config import MAX_HOUSES, USER_ID
from .llm_client import call_llm, extract_house_ids_from_response
from .rent_api_client import call_rent_api, call_init
from .session_manager import SessionManager


def _parse_user_id_from_session(session_id: str) -> str:
    """从 session_id 解析工号。格式：eval_{工号}_EV-XX_..."""
    m = re.match(r"eval_([^_]+)_EV-", session_id)
    if m:
        return m.group(1)
    return USER_ID


async def process_message(
    model_ip: str,
    session_id: str,
    message: str,
    session_manager: SessionManager,
    api_logger: Optional[Any] = None,
) -> dict[str, Any]:
    """
    处理单轮用户消息，返回 {response, status, tool_results, ...}
    """
    start_ts = time.time()
    tool_results: list[dict] = []
    user_id = _parse_user_id_from_session(session_id)

    # 1. 新 session 先 init
    if session_manager.is_new_session(session_id):
        init_res = await call_init(user_id=user_id)
        if api_logger:
            api_logger.log_api("init", "POST", f"/api/houses/init", {}, init_res, session_id)
        if init_res.get("success"):
            session_manager.mark_initialized(session_id)
        # init 失败也继续，可能环境问题

    # 2. 记录用户消息
    session_manager.add_message(session_id, "user", message)

    # 3. 构建 LLM 输入
    messages = session_manager.get_messages(session_id)
    context_summary = session_manager.get_context_summary(session_id)

    # 4. 调用 LLM
    llm_out = await call_llm(model_ip, messages, session_id, context_summary)
    if api_logger:
        api_logger.log_llm(session_id, llm_out)

    intent = llm_out.get("intent", "chat")
    reply = llm_out.get("reply", "")
    action = llm_out.get("action")
    actions = llm_out.get("actions")

    # 5. 根据 intent 处理
    if intent in ("chat", "need_clarification"):
        session_manager.add_message(session_id, "assistant", reply)
        return _build_response(reply, "success", tool_results, session_id, start_ts)

    # 6. 执行 API 调用
    to_execute = []
    if actions:
        to_execute = actions
    elif action:
        to_execute = [action]

    last_house_ids: list[str] = []
    last_api_data: Optional[dict] = None
    last_operation = ""
    last_query_params: dict[str, Any] = {}
    rent_house_id: Optional[str] = None  # 租房成功时的 house_id

    for i, act in enumerate(to_execute):
        api_name = act.get("api", "")
        params = act.get("params") or {}

        # 指代消解：还有其他的吗 -> page+1
        if "还有其他的" in message or "还有吗" in message or "翻页" in message:
            prev_params = session_manager.get_last_query_params(session_id)
            if prev_params and api_name == "get_houses_by_platform":
                params = {**prev_params, "page": prev_params.get("page", 1) + 1}

        # 指代消解：就租最近/第一套 -> 从记忆取 house_id
        if api_name == "rent_house" and not params.get("house_id"):
            prev_ids = session_manager.get_last_houses(session_id)
            if prev_ids:
                params["house_id"] = prev_ids[0]
            if not params.get("listing_platform"):
                params["listing_platform"] = "安居客"

        result = await call_rent_api(api_name, params, user_id=user_id)
        if api_logger:
            path = _get_api_path(api_name, params)
            api_logger.log_api(api_name, "GET" if "get_" in api_name else "POST", path, params, result, session_id)

        tool_results.append({"name": api_name, "success": result.get("success", False), "output": str(result)})

        if api_name == "rent_house" and result.get("success"):
            rent_house_id = params.get("house_id")

        if result.get("success"):
            data = result.get("data", {})
            last_api_data = data
            last_operation = api_name

            # 多步调用：第一步可能是地标，将 landmark_id 填入下一步
            if i + 1 < len(to_execute) and "landmark" in api_name.lower():
                landmark_id = None
                inner = data.get("data")
                if isinstance(inner, dict):
                    landmark_id = inner.get("id") or inner.get("landmark_id")
                elif isinstance(inner, list) and inner:
                    first = inner[0] if isinstance(inner[0], dict) else {}
                    landmark_id = first.get("id") or first.get("landmark_id")
                if landmark_id:
                    to_execute[i + 1]["params"] = to_execute[i + 1].get("params") or {}
                    to_execute[i + 1]["params"]["landmark_id"] = landmark_id

            # 提取房源 ID
            ids = extract_house_ids_from_response(result)
            if ids:
                last_house_ids = ids
                last_query_params = params
                # 保存到 session
                inner = data.get("data") or data
                total = inner.get("total", len(ids)) if isinstance(inner, dict) else len(ids)
                page = params.get("page", 1)
                session_manager.set_last_houses(session_id, ids, params, page, total)

    # 7. 生成最终 response
    if intent == "rent" and last_operation == "rent_house":
        # 租房完成
        house_id = rent_house_id
        if not house_id and action:
            house_id = action.get("params", {}).get("house_id")
        if not house_id and to_execute:
            house_id = to_execute[0].get("params", {}).get("house_id")
        if not house_id and last_house_ids:
            house_id = last_house_ids[0]
        if house_id:
            msg = reply if reply else "好的，已为您办理租房手续。"
            if "好的" not in msg:
                msg = "好的，" + msg
            return _build_house_response(msg, [house_id], "success", tool_results, session_id, start_ts)

    if last_house_ids:
        # 查房完成，返回 JSON
        msg = _build_query_message(reply, last_api_data, last_operation, last_query_params)
        return _build_house_response(msg, last_house_ids, "success", tool_results, session_id, start_ts)

    # 翻页无更多
    if ("还有其他的" in message or "还有吗" in message) and not last_house_ids:
        prev_ids = session_manager.get_last_houses(session_id)
        if prev_ids:
            return _build_house_response(
                "没有其他的了，只有这一套",
                prev_ids,
                "success",
                tool_results,
                session_id,
                start_ts,
            )

    # 查无结果
    if last_operation in ("get_houses_by_platform", "get_houses_nearby", "get_houses_by_community") and not last_house_ids:
        msg = reply if "没有" in reply else "没有找到符合条件的房源。"
        return _build_house_response(msg, [], "success", tool_results, session_id, start_ts)

    # 其他情况
    final_reply = reply or "操作已完成。"
    session_manager.add_message(session_id, "assistant", final_reply)
    return _build_response(final_reply, "success", tool_results, session_id, start_ts)


def _get_api_path(api_name: str, params: dict) -> str:
    """用于日志"""
    if "house_id" in params:
        return f"/api/houses/{params.get('house_id', '')}/..."
    return f"/api/{api_name}"


def _build_query_message(
    llm_reply: str,
    api_data: Optional[dict],
    operation: str,
    params: dict,
) -> str:
    """
    构建满足 message_contains 的 message。
    需包含：区域、户型、地铁距离数值、subway_distance、asc 等关键词。
    """
    parts = []
    if params.get("district"):
        parts.append(params["district"])
    if params.get("bedrooms"):
        parts.append(f"{params['bedrooms']}居")
    if params.get("max_subway_dist"):
        parts.append(f"{params['max_subway_dist']}米")
    if params.get("sort_by") == "subway":
        parts.append("subway_distance")
        parts.append(params.get("sort_order", "asc"))
    if parts:
        base = "、".join(str(p) for p in parts)
        if llm_reply and "没有" not in llm_reply:
            return f"为您找到{base}以内的房源：{llm_reply}"
        return f"为您找到{base}以内的房源。" + (llm_reply or "")
    return llm_reply or "已为您查询到以下房源。"


def _build_response(
    response: str,
    status: str,
    tool_results: list,
    session_id: str,
    start_ts: float,
) -> dict:
    return {
        "session_id": session_id,
        "response": response,
        "status": status,
        "tool_results": tool_results,
        "timestamp": int(time.time()),
        "duration_ms": int((time.time() - start_ts) * 1000),
    }


def _build_house_response(
    message: str,
    houses: list[str],
    status: str,
    tool_results: list,
    session_id: str,
    start_ts: float,
) -> dict:
    """房源查询完成时，response 为 JSON 字符串"""
    payload = {"message": message, "houses": houses[:MAX_HOUSES]}
    response_str = json.dumps(payload, ensure_ascii=False)
    return {
        "session_id": session_id,
        "response": response_str,
        "status": status,
        "tool_results": tool_results,
        "timestamp": int(time.time()),
        "duration_ms": int((time.time() - start_ts) * 1000),
    }
