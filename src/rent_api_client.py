"""
租房 API 客户端：根据 operationId 与 params 调用租房仿真 API。
所有 /api/houses/* 请求必须带 X-User-ID；地标类不需。
"""
import httpx
from typing import Any, Optional

from .config import USER_ID, RENT_API_BASE_URL

# operationId -> (method, path_template, path_params, needs_user_id)
API_ROUTES = {
    "get_landmarks": ("GET", "/api/landmarks", [], False),
    "get_landmark_by_name": ("GET", "/api/landmarks/name/{name}", ["name"], False),
    "search_landmarks": ("GET", "/api/landmarks/search", [], False),
    "get_landmark_by_id": ("GET", "/api/landmarks/{id}", ["id"], False),
    "get_landmark_stats": ("GET", "/api/landmarks/stats", [], False),
    "get_house_by_id": ("GET", "/api/houses/{house_id}", ["house_id"], True),
    "get_house_listings": ("GET", "/api/houses/listings/{house_id}", ["house_id"], True),
    "get_houses_by_community": ("GET", "/api/houses/by_community", [], True),
    "get_houses_by_platform": ("GET", "/api/houses/by_platform", [], True),
    "get_houses_nearby": ("GET", "/api/houses/nearby", [], True),
    "get_nearby_landmarks": ("GET", "/api/houses/nearby_landmarks", [], True),
    "get_house_stats": ("GET", "/api/houses/stats", [], True),
    "rent_house": ("POST", "/api/houses/{house_id}/rent", ["house_id"], True),
    "terminate_rental": ("POST", "/api/houses/{house_id}/terminate", ["house_id"], True),
    "take_offline": ("POST", "/api/houses/{house_id}/offline", ["house_id"], True),
}

# init 接口（需求说明约定，不在 OpenAPI 中）
INIT_PATH = "/api/houses/init"


def _build_path(template: str, path_params: list[str], params: dict[str, Any]) -> str:
    """从 params 填充 path 中的占位符"""
    path = template
    for key in path_params:
        val = params.get(key)
        if val is not None:
            path = path.replace(f"{{{key}}}", str(val))
    return path


def _build_query(params: dict[str, Any], path_params: list[str]) -> dict[str, Any]:
    """排除 path 参数，其余作为 query"""
    return {k: v for k, v in params.items() if k not in path_params and v is not None}


async def call_rent_api(
    operation_id: str,
    params: dict[str, Any],
    base_url: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    根据 operationId 和 params 调用租房 API。
    返回 {"success": bool, "data": ..., "error": str?}
    """
    base_url = base_url or RENT_API_BASE_URL
    user_id = user_id or USER_ID

    if operation_id not in API_ROUTES:
        return {"success": False, "error": f"Unknown operation: {operation_id}"}

    method, path_template, path_params, needs_user_id = API_ROUTES[operation_id]
    path = _build_path(path_template, path_params, params)
    query = _build_query(params, path_params)

    url = f"{base_url.rstrip('/')}{path}"
    headers = {}
    if needs_user_id:
        headers["X-User-ID"] = user_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            resp = await client.get(url, params=query, headers=headers)
        else:
            resp = await client.post(url, params=query, headers=headers)

    try:
        data = resp.json()
    except Exception:
        return {
            "success": False,
            "error": f"Invalid JSON: {resp.text[:200]}",
            "status_code": resp.status_code,
        }

    if resp.status_code >= 400:
        return {
            "success": False,
            "error": data.get("message", resp.text),
            "status_code": resp.status_code,
        }

    return {"success": True, "data": data, "status_code": resp.status_code}


async def call_init(base_url: Optional[str] = None, user_id: Optional[str] = None) -> dict[str, Any]:
    """新 session 时调用 init 重置用户房源状态"""
    base_url = base_url or RENT_API_BASE_URL
    user_id = user_id or USER_ID
    url = f"{base_url.rstrip('/')}{INIT_PATH}"
    headers = {"X-User-ID": user_id}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers)

    try:
        data = resp.json()
    except Exception:
        return {
            "success": False,
            "error": f"Invalid JSON: {resp.text[:200]}",
            "status_code": resp.status_code,
        }

    if resp.status_code >= 400:
        return {"success": False, "error": data.get("message", resp.text), "status_code": resp.status_code}

    return {"success": True, "data": data, "status_code": resp.status_code}
