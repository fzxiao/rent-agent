"""租房 API 客户端：带 X-User-ID，支持 init/查询/租房"""
import json
import time

import httpx

from agent.api_logger import log_rental_api
from agent.config import RENTAL_API_BASE_URL


class RentalAPIClient:
    """租房仿真 API 客户端"""

    def __init__(self, base_url: str = RENTAL_API_BASE_URL, user_id: str = "test_user_001") -> None:
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self._headers = {"X-User-ID": user_id}

    def _get(self, path: str, params: dict | None = None, need_user_id: bool = True) -> dict:
        """GET 请求"""
        url = f"{self.base_url}{path}"
        headers = self._headers if need_user_id else {}
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            log_rental_api(
                "GET", path, params, resp.status_code,
                (time.perf_counter() - start) * 1000,
                result_preview=json.dumps(data, ensure_ascii=False)[:500],
            )
            return data
        except Exception as e:
            log_rental_api(
                "GET", path, params, getattr(e, "response", None) and getattr(e.response, "status_code", 0) or 0,
                (time.perf_counter() - start) * 1000,
                error=str(e),
            )
            raise

    def _post(self, path: str, params: dict | None = None) -> dict:
        """POST 请求"""
        url = f"{self.base_url}{path}"
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, params=params, headers=self._headers)
                resp.raise_for_status()
                data = resp.json()
            log_rental_api(
                "POST", path, params, resp.status_code,
                (time.perf_counter() - start) * 1000,
                result_preview=json.dumps(data, ensure_ascii=False)[:500],
            )
            return data
        except Exception as e:
            log_rental_api(
                "POST", path, params, getattr(e, "response", None) and getattr(e.response, "status_code", 0) or 0,
                (time.perf_counter() - start) * 1000,
                error=str(e),
            )
            raise

    def init(self) -> dict:
        """房源数据重置，每新 session 调用"""
        return self._post("/api/houses/init")

    def get_landmarks(self, category: str | None = None, district: str | None = None) -> dict:
        """获取地标列表"""
        params = {}
        if category:
            params["category"] = category
        if district:
            params["district"] = district
        return self._get("/api/landmarks", params=params, need_user_id=False)

    def get_landmark_by_name(self, name: str) -> dict:
        """按名称精确查询地标"""
        return self._get(f"/api/landmarks/name/{name}", need_user_id=False)

    def search_landmarks(self, q: str, category: str | None = None, district: str | None = None) -> dict:
        """关键词模糊搜索地标"""
        params = {"q": q}
        if category:
            params["category"] = category
        if district:
            params["district"] = district
        return self._get("/api/landmarks/search", params=params, need_user_id=False)

    def get_house(self, house_id: str) -> dict:
        """根据房源 ID 获取详情"""
        return self._get(f"/api/houses/{house_id}")

    def get_houses_by_platform(
        self,
        district: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        bedrooms: str | None = None,
        decoration: str | None = None,
        max_subway_dist: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        listing_platform: str | None = None,
        page: int = 1,
        page_size: int = 10,
        **kwargs: object,
    ) -> dict:
        """按挂牌平台筛选房源（主查询接口）"""
        params: dict[str, object] = {"page": page, "page_size": page_size}
        if district:
            params["district"] = district
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if bedrooms:
            params["bedrooms"] = bedrooms
        if decoration:
            params["decoration"] = decoration
        if max_subway_dist is not None:
            params["max_subway_dist"] = max_subway_dist
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order
        if listing_platform:
            params["listing_platform"] = listing_platform
        params.update(kwargs)
        return self._get("/api/houses/by_platform", params=params)

    def get_houses_nearby(
        self,
        landmark_id: str,
        max_distance: int = 2000,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """以地标为圆心查附近房源"""
        params = {
            "landmark_id": landmark_id,
            "max_distance": max_distance,
            "page": page,
            "page_size": page_size,
        }
        return self._get("/api/houses/nearby", params=params)

    def get_houses_by_community(
        self,
        community: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """按小区名查询可租房源"""
        params = {"community": community, "page": page, "page_size": page_size}
        return self._get("/api/houses/by_community", params=params)

    def rent_house(self, house_id: str, listing_platform: str = "安居客") -> dict:
        """租房"""
        return self._post(f"/api/houses/{house_id}/rent", params={"listing_platform": listing_platform})

    def terminate_rental(self, house_id: str, listing_platform: str = "安居客") -> dict:
        """退租"""
        return self._post(f"/api/houses/{house_id}/terminate", params={"listing_platform": listing_platform})

    def take_offline(self, house_id: str, listing_platform: str = "安居客") -> dict:
        """下架"""
        return self._post(f"/api/houses/{house_id}/offline", params={"listing_platform": listing_platform})
