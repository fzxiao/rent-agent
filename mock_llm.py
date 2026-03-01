"""Mock LLM 服务：用于本地测试，根据用户消息返回预设的 tool_calls 或文本"""
import json
import re
from typing import Any

from fastapi import FastAPI, Request

app = FastAPI(title="Mock LLM", version="1.0.0")


def _parse_district(text: str) -> str | None:
    for d in ["东城", "西城", "海淀", "朝阳", "通州", "昌平", "大兴", "房山", "丰台", "顺义"]:
        if d in text:
            return d
    return None


def _parse_bedrooms(text: str) -> str | None:
    if "一居" in text or "1居" in text:
        return "1"
    if "两居" in text or "2居" in text:
        return "2"
    if "三居" in text:
        return "3"
    return None


def _parse_max_price(text: str) -> int | None:
    m = re.search(r"(\d+)\s*以内|租金\s*(\d+)|(\d+)\s*元", text)
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return None


def _parse_max_subway(text: str) -> int:
    if "500" in text or "500米" in text:
        return 500
    if "近地铁" in text or "800" in text:
        return 800
    if "1000" in text or "地铁可达" in text:
        return 1000
    return 1000  # 默认


def _parse_decoration(text: str) -> str | None:
    if "精装" in text:
        return "精装"
    if "简装" in text:
        return "简装"
    return None


def _parse_rent_intent(text: str) -> bool:
    return "就租" in text or "租这套" in text or "租这个" in text or "租最近" in text


def _get_last_user_message(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return m["content"]
    return ""


def _has_tool_results(messages: list[dict]) -> bool:
    return any(m.get("role") == "tool" for m in messages)


def _get_last_tool_call_house_ids(messages: list[dict]) -> list[str]:
    """从最近的 tool 消息中提取 house_id"""
    for m in reversed(messages):
        if m.get("role") == "tool":
            try:
                data = json.loads(m.get("content", "{}"))
                # 租房接口返回单条 data 为 dict
                single = data.get("data")
                if isinstance(single, dict) and "house_id" in single:
                    return [single["house_id"]]
                items = data.get("data", {})
                if isinstance(items, dict):
                    items = items.get("items", [])
                ids = []
                for it in items:
                    if isinstance(it, dict) and "house_id" in it:
                        ids.append(it["house_id"])
                return ids
            except Exception:
                pass
    return []


def _last_tool_was_rent(messages: list[dict]) -> bool:
    """检查上一轮 assistant 是否调用了 rent_house"""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls", []):
                if tc.get("function", {}).get("name") == "rent_house":
                    return True
            return False
    return False


def _generate_response(messages: list[dict], tools: list | None) -> dict:
    last_user = _get_last_user_message(messages)

    # 已有 tool 结果时，优先检查是否刚完成租房（避免重复返回 rent_house）
    if _has_tool_results(messages):
        if _last_tool_was_rent(messages):
            msg = "好的，已为您办理租房手续。"
            return {
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": msg},
                        "finish_reason": "stop",
                    },
                ],
            }
        # 用户说「就租」且已有房源列表，返回 rent_house tool_call
        if _parse_rent_intent(last_user):
            house_ids = _get_last_tool_call_house_ids(messages)
            first_id = house_ids[0] if house_ids else "HF_906"
            return {
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_rent",
                                    "type": "function",
                                    "function": {
                                        "name": "rent_house",
                                        "arguments": json.dumps(
                                            {"house_id": first_id, "listing_platform": "安居客"},
                                            ensure_ascii=False,
                                        ),
                                    },
                                },
                            ],
                        },
                        "finish_reason": "tool_calls",
                    },
                ],
            }
        house_ids = _get_last_tool_call_house_ids(messages)
        # 追问「还有其他的吗」时，应回复没有其他的
        if "还有" in last_user or "其他" in last_user or "都给" in last_user:
            if len(house_ids) <= 1:
                msg = "没有其他的了，只有这一套。" + (f"（{house_ids[0]}）" if house_ids else "")
            else:
                msg = f"符合条件的共 {len(house_ids)} 套：{', '.join(house_ids)}。"
        elif house_ids:
            district = _parse_district(last_user)
            bedrooms = _parse_bedrooms(last_user)
            dist_str = f"（{district}区）" if district else ""
            bed_str = f"{bedrooms}居" if bedrooms else ""
            msg = f"为您找到{dist_str}{bed_str} {len(house_ids)} 套符合条件的房源：{', '.join(house_ids)}。"
        else:
            msg = "抱歉，没有找到符合条件的房源。"
        return {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": msg},
                    "finish_reason": "stop",
                },
            ],
        }

    # 首轮：解析需求并返回 tool_calls
    district = _parse_district(last_user)
    bedrooms = _parse_bedrooms(last_user)
    max_price = _parse_max_price(last_user)
    max_subway = _parse_max_subway(last_user)
    decoration = _parse_decoration(last_user)

    sort_by = "subway" if "地铁" in last_user and ("近" in last_user or "排" in last_user) else None
    sort_order = "asc" if "从近到远" in last_user or "近到远" in last_user else None

    tool_calls = [
        {
            "id": "call_init",
            "type": "function",
            "function": {"name": "houses_init", "arguments": "{}"},
        },
        {
            "id": "call_query",
            "type": "function",
            "function": {
                "name": "get_houses_by_platform",
                "arguments": json.dumps(
                    {
                        "district": district,
                        "bedrooms": bedrooms,
                        "max_price": max_price,
                        "max_subway_dist": max_subway,
                        "decoration": decoration,
                        "sort_by": sort_by,
                        "sort_order": sort_order,
                    },
                    ensure_ascii=False,
                ),
            },
        },
    ]

    return {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls,
                },
                "finish_reason": "tool_calls",
            },
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> dict:
    """模拟 LLM 接口"""
    req = await request.json()
    messages = req.get("messages", [])
    tools = req.get("tools")
    result = _generate_response(messages, tools)
    result["id"] = "mock-cmpl-1"
    result["object"] = "chat.completion"
    result["created"] = 1700000000
    result["model"] = "mock"
    result["usage"] = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    return result


def run() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)


if __name__ == "__main__":
    run()
