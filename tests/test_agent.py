"""
本地测试：Mock 租房 API 与 LLM，验证 Agent 逻辑。
基于需求说明中的用例示例构造测试。
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agent import process_message, _build_house_response, _build_query_message
from src.session_manager import SessionManager


# --- Mock 数据 ---

# 用例1 EV-43：东城区精装两居，5000以内，离地铁500米 - 无结果
MOCK_EMPTY_HOUSES = {"success": True, "data": {"items": [], "total": 0}}

# 用例2 EV-46：西城区离地铁近一居 - 仅 HF_13
MOCK_HOUSES_EV46 = {"success": True, "data": {"items": [{"house_id": "HF_13"}], "total": 1}}

# 用例3 EV-45：海淀区离地铁近两居 - 5 套
MOCK_HOUSES_EV45 = {
    "success": True,
    "data": {
        "items": [
            {"house_id": "HF_906"},
            {"house_id": "HF_1586"},
            {"house_id": "HF_1876"},
            {"house_id": "HF_706"},
            {"house_id": "HF_33"},
        ],
        "total": 5,
    },
}

# LLM 模拟输出
def make_llm_query_house(api: str, params: dict):
    return {"intent": "query_house", "reply": "", "action": {"api": api, "params": params}, "actions": None}

def make_llm_rent(house_id: str):
    return {"intent": "rent", "reply": "好的", "action": {"api": "rent_house", "params": {"house_id": house_id, "listing_platform": "安居客"}}, "actions": None}

def make_llm_chat(reply: str):
    return {"intent": "chat", "reply": reply, "action": None, "actions": None}


@pytest.mark.asyncio
async def test_build_house_response_format():
    """验证房源查询完成的 response 为合法 JSON 字符串"""
    result = _build_house_response("为您找到3套房源", ["HF_1", "HF_2"], "success", [], "s1", 0)
    assert "session_id" in result
    assert "response" in result
    parsed = json.loads(result["response"])
    assert "message" in parsed
    assert "houses" in parsed
    assert parsed["houses"] == ["HF_1", "HF_2"]


@pytest.mark.asyncio
async def test_build_query_message_contains_keywords():
    """验证 message 包含判分所需关键词"""
    params = {"district": "海淀", "bedrooms": "2", "max_subway_dist": 800, "sort_by": "subway", "sort_order": "asc"}
    msg = _build_query_message("", None, "get_houses_by_platform", params)
    assert "海淀" in msg
    assert "2" in msg
    assert "800" in msg
    assert "subway_distance" in msg
    assert "asc" in msg


@pytest.mark.asyncio
async def test_case_ev43_no_results(session_manager):
    """用例1 EV-43：无结果时返回 houses:[] 且 message 含「没有」"""
    with patch("src.agent.call_init", new_callable=AsyncMock, return_value={"success": True}):
        with patch("src.agent.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = make_llm_query_house("get_houses_by_platform", {
                "district": "东城", "bedrooms": "2", "max_price": 5000, "max_subway_dist": 500,
                "decoration": "精装", "page": 1, "page_size": 10,
            })
            with patch("src.agent.call_rent_api", new_callable=AsyncMock, return_value=MOCK_EMPTY_HOUSES):
                result = await process_message("127.0.0.1", "EV-43", "东城区精装两居，租金 5000 以内，离地铁 500 米以内的有吗？", session_manager, None)

    assert result["status"] == "success"
    resp = json.loads(result["response"])
    assert resp["houses"] == []
    assert "没有" in resp["message"]


@pytest.mark.asyncio
async def test_case_ev46_round1(session_manager):
    """用例2 EV-46 第1轮：西城区离地铁近一居，按地铁从近到远"""
    with patch("src.agent.call_init", new_callable=AsyncMock, return_value={"success": True}):
        with patch("src.agent.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = make_llm_query_house("get_houses_by_platform", {
                "district": "西城", "bedrooms": "1", "max_subway_dist": 1000,
                "sort_by": "subway", "sort_order": "asc", "page": 1, "page_size": 10,
            })
            with patch("src.agent.call_rent_api", new_callable=AsyncMock, return_value=MOCK_HOUSES_EV46):
                result = await process_message("127.0.0.1", "EV-46", "西城区离地铁近的一居室有吗？按离地铁从近到远排。", session_manager, None)

    assert result["status"] == "success"
    resp = json.loads(result["response"])
    assert resp["houses"] == ["HF_13"]
    msg = resp["message"]
    assert "西城" in msg
    assert "1" in msg
    assert "1000" in msg
    assert "subway_distance" in msg
    assert "asc" in msg


@pytest.mark.asyncio
async def test_case_ev46_round2_no_more(session_manager):
    """用例2 EV-46 第2轮：还有其他的吗 -> 没有其他的了，只有这一套"""
    # 先执行第1轮以填充上下文
    with patch("src.agent.call_init", new_callable=AsyncMock, return_value={"success": True}):
        with patch("src.agent.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = make_llm_query_house("get_houses_by_platform", {
                "district": "西城", "bedrooms": "1", "max_subway_dist": 1000,
                "sort_by": "subway", "sort_order": "asc", "page": 1, "page_size": 10,
            })
            with patch("src.agent.call_rent_api", new_callable=AsyncMock, return_value=MOCK_HOUSES_EV46):
                await process_message("127.0.0.1", "EV-46", "西城区离地铁近的一居室有吗？按离地铁从近到远排。", session_manager, None)

    # 第2轮：翻页无更多
    with patch("src.agent.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = make_llm_query_house("get_houses_by_platform", {
            "district": "西城", "bedrooms": "1", "max_subway_dist": 1000,
            "sort_by": "subway", "sort_order": "asc", "page": 2, "page_size": 10,
        })
        with patch("src.agent.call_rent_api", new_callable=AsyncMock, return_value=MOCK_EMPTY_HOUSES):
            result = await process_message("127.0.0.1", "EV-46", "还有其他的吗？把所有符合条件的都给出来", session_manager, None)

    assert result["status"] == "success"
    resp = json.loads(result["response"])
    assert resp["houses"] == ["HF_13"]
    assert "没有其他的了，只有这一套" in resp["message"]


@pytest.mark.asyncio
async def test_case_ev45_round1_and_rent(session_manager):
    """用例3 EV-45：第1轮查房，第2轮租房"""
    with patch("src.agent.call_init", new_callable=AsyncMock, return_value={"success": True}):
        with patch("src.agent.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = make_llm_query_house("get_houses_by_platform", {
                "district": "海淀", "bedrooms": "2", "max_subway_dist": 800,
                "sort_by": "subway", "sort_order": "asc", "page": 1, "page_size": 10,
            })
            with patch("src.agent.call_rent_api", new_callable=AsyncMock, return_value=MOCK_HOUSES_EV45):
                result1 = await process_message("127.0.0.1", "EV-45", "海淀区离地铁近的两居有吗？按离地铁从近到远排一下。", session_manager, None)

    assert result1["status"] == "success"
    resp1 = json.loads(result1["response"])
    assert resp1["houses"] == ["HF_906", "HF_1586", "HF_1876", "HF_706", "HF_33"]
    assert "海淀" in resp1["message"] and "2" in resp1["message"] and "800" in resp1["message"]

    # 第2轮：就租最近的那套
    with patch("src.agent.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = make_llm_rent("HF_906")
        with patch("src.agent.call_rent_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"success": True, "data": {"house_id": "HF_906"}}
            result2 = await process_message("127.0.0.1", "EV-45", "就租最近的那套吧。", session_manager, None)

    assert result2["status"] == "success"
    resp2 = json.loads(result2["response"])
    assert resp2["houses"] == ["HF_906"]
    assert "好的" in resp2["message"]
    # 验证调用了 rent API
    mock_api.assert_called_once()
    call_args = mock_api.call_args
    assert call_args[0][0] == "rent_house"
    assert call_args[0][1].get("house_id") == "HF_906"
