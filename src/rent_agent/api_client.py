"""租房 API 客户端，支持真实调用与 Mock。"""

from typing import Any

import httpx

from rent_agent import logger
from rent_agent.config import RENTAL_API_BASE, USER_ID, USE_MOCK


def _headers_for_houses() -> dict[str, str]:
    return {"X-User-ID": USER_ID, "Content-Type": "application/json"}


def _log_rental_api(
    session_id: str,
    api_name: str,
    params: dict[str, Any],
    status_code: int,
    response_summary: Any,
    url: str,
) -> None:
    logger.log_api_call(
        session_id=session_id,
        call_type="rental_api",
        api_name=api_name,
        params=params,
        status_code=status_code,
        response_summary=response_summary,
        url=url,
    )


# ---------- Mock 数据 ----------


def _mock_init(session_id: str) -> dict:
    return {"code": 0, "message": "success", "data": {"action": "reset_user"}}

def _mock_by_platform(session_id: str, params: dict) -> dict:
    district = params.get("district", "")
    bedrooms = params.get("bedrooms", "")
    max_price = params.get("max_price")
    max_subway_dist = params.get("max_subway_dist")
    decoration = params.get("decoration")
    page = params.get("page", 1)

    # 用例 1 EV-43: 东城 精装 两居 5000以内 500米以内 -> 无
    if district == "东城" and bedrooms == "2" and max_price == 5000 and max_subway_dist == 500 and decoration == "精装":
        return {"code": 0, "data": {"items": [], "total": 0}}

    # 用例 2 EV-46: 西城 一居 1000米 sort_by=subway asc
    if district == "西城" and bedrooms == "1" and max_subway_dist == 1000:
        if page == 1:
            return {"code": 0, "data": {"items": [{"house_id": "HF_13"}], "total": 1}}
        return {"code": 0, "data": {"items": [], "total": 1}}

    # 用例 3 EV-45: 海淀 两居 800米 sort_by=subway asc
    if district == "海淀" and bedrooms == "2" and max_subway_dist == 800:
        return {
            "code": 0,
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

    return {"code": 0, "data": {"items": [], "total": 0}}


def _mock_rent(session_id: str, house_id: str, listing_platform: str) -> dict:
    return {"code": 0, "data": {"house_id": house_id, "status": "已租"}}


# ---------- 真实 API 调用 ----------


def call_init(session_id: str) -> dict:
    """POST /api/houses/init"""
    url = f"{RENTAL_API_BASE}/api/houses/init"
    if USE_MOCK:
        out = _mock_init(session_id)
        _log_rental_api(session_id, "init", {}, 200, "mock", url)
        return out
    with httpx.Client() as client:
        r = client.post(url, headers=_headers_for_houses())
        resp = r.json() if r.content else {}
        _log_rental_api(session_id, "init", {}, r.status_code, resp, url)
        return resp


def call_get_houses_by_platform(session_id: str, params: dict) -> dict:
    """GET /api/houses/by_platform"""
    url = f"{RENTAL_API_BASE}/api/houses/by_platform"
    if USE_MOCK:
        out = _mock_by_platform(session_id, params)
        _log_rental_api(session_id, "get_houses_by_platform", params, 200, out, url)
        return out
    with httpx.Client() as client:
        r = client.get(url, params=params, headers=_headers_for_houses())
        resp = r.json() if r.content else {}
        _log_rental_api(session_id, "get_houses_by_platform", params, r.status_code, resp, url)
        return resp


def call_rent_house(session_id: str, house_id: str, listing_platform: str = "安居客") -> dict:
    """POST /api/houses/{house_id}/rent"""
    url = f"{RENTAL_API_BASE}/api/houses/{house_id}/rent"
    params = {"listing_platform": listing_platform}
    if USE_MOCK:
        out = _mock_rent(session_id, house_id, listing_platform)
        _log_rental_api(session_id, "rent_house", {"house_id": house_id, "listing_platform": listing_platform}, 200, out, url)
        return out
    with httpx.Client() as client:
        r = client.post(url, params=params, headers=_headers_for_houses())
        resp = r.json() if r.content else {}
        _log_rental_api(session_id, "rent_house", {"house_id": house_id, "listing_platform": listing_platform}, r.status_code, resp, url)
        return resp
