"""租房 API 工具层 - 接口映射与 HTTP 调用"""
import json
import logging
from typing import Any

import httpx

from .config import HOUSING_API_BASE, X_USER_ID

logger = logging.getLogger(__name__)

# operationId -> (method, path_template, path_params, needs_user_id)
API_ROUTES = {
    # 地标类（无需 X-User-ID）
    "get_landmarks": ("GET", "/api/landmarks", [], False),
    "get_landmark_by_name": ("GET", "/api/landmarks/name/{name}", ["name"], False),
    "search_landmarks": ("GET", "/api/landmarks/search", [], False),
    "get_landmark_by_id": ("GET", "/api/landmarks/{id}", ["id"], False),
    "get_landmark_stats": ("GET", "/api/landmarks/stats", [], False),
    # 房源类（需 X-User-ID）
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


def _build_path(template: str, path_params: list[str], params: dict[str, Any]) -> str:
    """从 params 填充 path 中的占位符"""
    path = template
    for p in path_params:
        val = params.get(p)
        if val is not None:
            path = path.replace(f"{{{p}}}", str(val))
    return path


def _build_query(method: str, path_params: list[str], params: dict[str, Any]) -> dict[str, Any]:
    """从 params 中排除 path 参数，得到 query 参数"""
    query = {}
    for k, v in params.items():
        if k in path_params:
            continue
        if v is None or v == "":
            continue
        query[k] = v
    return query


async def call_housing_api(
    operation_id: str,
    params: dict[str, Any],
    base_url: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    根据 operationId 和 params 调用租房 API。
    返回 API 响应的 data 或完整响应。
    """
    base = base_url or HOUSING_API_BASE
    uid = user_id or X_USER_ID

    if operation_id not in API_ROUTES:
        return {"error": f"Unknown operation: {operation_id}"}

    method, template, path_params, needs_user_id = API_ROUTES[operation_id]
    path = _build_path(template, path_params, params)
    query = _build_query(method, path_params, params)

    url = f"{base.rstrip('/')}{path}"
    headers = {}
    if needs_user_id:
        headers["X-User-ID"] = uid

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                resp = await client.get(url, params=query, headers=headers)
            else:
                resp = await client.post(url, params=query, headers=headers)

            body = resp.json() if resp.content else {}
            log_entry = {
                "operation_id": operation_id,
                "url": str(resp.url),
                "status_code": resp.status_code,
                "params": params,
            }
            logger.info("Housing API call: %s", json.dumps(log_entry, ensure_ascii=False))

            if resp.status_code >= 400:
                return {"error": body.get("message", str(resp.status_code)), "raw": body}

            # 常见成功格式: { code: 0, data: ... }
            if isinstance(body, dict) and "data" in body:
                return body["data"]
            return body
    except Exception as e:
        logger.exception("Housing API error: %s", e)
        return {"error": str(e)}


async def init_housing(base_url: str | None = None, user_id: str | None = None) -> dict[str, Any]:
    """新 session 时调用 POST /api/houses/init 重置用户房源状态"""
    base = base_url or HOUSING_API_BASE
    uid = user_id or X_USER_ID
    url = f"{base.rstrip('/')}/api/houses/init"
    headers = {"X-User-ID": uid}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers)
            body = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                return {"error": body.get("message", str(resp.status_code))}
            return body.get("data", body)
    except Exception as e:
        logger.exception("Init housing error: %s", e)
        return {"error": str(e)}
