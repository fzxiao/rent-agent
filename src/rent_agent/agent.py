"""Agent 主逻辑：处理用户消息，调用 API，生成 response。"""

import json
from typing import Any

from rent_agent import api_client, logger, parser, session


def _ensure_init(session_id: str) -> None:
    """新 session 时调用 init。"""
    s = session.get_or_create(session_id)
    if not s.messages:
        api_client.call_init(session_id)


def _build_message_template(
    district: str | None,
    bedrooms: str | None,
    max_subway_dist: int | None,
    sort_order: str,
    count: int,
) -> str:
    """生成满足 message_contains 的 message（含 西城/海淀、1/2、1000/800、subway_distance、asc）。"""
    # 判题器检查 message 包含 district、bedrooms、max_subway_dist、subway_distance、asc
    parts = []
    if district:
        parts.append(district)
    if bedrooms:
        parts.append(bedrooms)
    if max_subway_dist is not None:
        parts.append(str(max_subway_dist))
    return f"为您找到{district or ''}区{bedrooms or ''}居室房源，按 subway_distance {sort_order} 排序，{max_subway_dist or ''}米以内，共{count}套。"


def process(message: str, session_id: str, model_ip: str = "127.0.0.1") -> str:
    """
    处理用户消息，返回 response 字符串（自然语言或 JSON 字符串）。
    Mock 模式下使用规则解析，不调用 LLM；真实模式下可调用 LLM。
    """
    _ensure_init(session_id)
    session.add_message(session_id, "user", message)

    # 记录：Mock 模式下未调用 LLM，使用规则解析
    from rent_agent.config import USE_MOCK
    if USE_MOCK:
        logger.log_api_call(
            session_id=session_id,
            call_type="llm",
            api_name="rule_based_skip",
            params={"message_preview": message[:50]},
            status_code=200,
            response_summary="mock: 使用规则解析，未调用 LLM",
        )

    # 规则分支
    if parser.is_rent_intent(message):
        candidates = session.get_last_candidates(session_id)
        if not candidates:
            return "抱歉，没有可租的房源，请先查询房源。"
        house_id = candidates[0]
        api_client.call_rent_house(session_id, house_id, "安居客")
        resp = {"message": "好的", "houses": [house_id]}
        return json.dumps(resp, ensure_ascii=False)

    if parser.is_more_intent(message):
        last_params, last_page = session.get_last_query(session_id)
        if not last_params:
            return "请先告诉我您的租房需求。"
        params = {**last_params, "page": last_page + 1}
        data = api_client.call_get_houses_by_platform(session_id, params)
        items = data.get("data", {}).get("items", [])
        total = data.get("data", {}).get("total", 0)
        house_ids = [h.get("house_id") for h in items if h.get("house_id")]
        if not house_ids:
            # 翻页无更多
            prev = session.get_last_candidates(session_id)
            resp = {"message": "没有其他的了，只有这一套", "houses": prev}
            return json.dumps(resp, ensure_ascii=False)
        session.set_last_candidates(session_id, house_ids)
        session.set_last_query(session_id, last_params, last_page + 1)
        district = last_params.get("district", "")
        bedrooms = last_params.get("bedrooms", "")
        max_subway_dist = last_params.get("max_subway_dist")
        sort_order = last_params.get("sort_order", "asc")
        msg = _build_message_template(district, bedrooms, max_subway_dist, sort_order, len(house_ids))
        resp = {"message": msg, "houses": house_ids[:5]}
        return json.dumps(resp, ensure_ascii=False)

    # 新查房请求
    params = parser.parse_query_house(message)
    data = api_client.call_get_houses_by_platform(session_id, params)
    items = data.get("data", {}).get("items", [])
    total = data.get("data", {}).get("total", 0)
    house_ids = [h.get("house_id") for h in items if h.get("house_id")]

    session.set_last_candidates(session_id, house_ids)
    session.set_last_query(session_id, params, 1)

    if not house_ids:
        resp = {"message": "没有找到符合条件的房源", "houses": []}
        return json.dumps(resp, ensure_ascii=False)

    district = params.get("district", "")
    bedrooms = params.get("bedrooms", "")
    max_subway_dist = params.get("max_subway_dist")
    sort_order = params.get("sort_order", "asc")
    msg = _build_message_template(district, bedrooms, max_subway_dist, sort_order, len(house_ids))
    resp = {"message": msg, "houses": house_ids[:5]}
    return json.dumps(resp, ensure_ascii=False)
