"""租房仿真 API HTTP 封装，房源接口统一带 X-User-ID。"""
import httpx
from config import settings

try:
    from logging_conf import get_logger
    _log = get_logger("rent_api")
except Exception:
    _log = None

HOUSES_HEADERS = {"X-User-ID": settings.rent_user_id}
RENT_API_BASE = settings.rent_api_base.rstrip("/")
MAX_RETRIES = 2 if settings.enable_retry else 0


def _houses_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=RENT_API_BASE,
        headers=HOUSES_HEADERS,
        timeout=30.0,
    )


def _landmarks_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=RENT_API_BASE, timeout=30.0)


async def init_houses() -> dict:
    """房源数据重置，新 session 时调用。"""
    async with _houses_client() as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                r = await client.post("/api/houses/init")
                if _log:
                    _log.info("rent_api", api="init_houses", status=r.status_code)
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if _log:
                    _log.warning("rent_api_error", api="init_houses", error=str(e))
                if attempt == MAX_RETRIES:
                    raise
                continue
    return {}


# ---------- 地标（不需 X-User-ID） ----------


async def get_landmarks(category: str | None = None, district: str | None = None) -> dict:
    async with _landmarks_client() as client:
        r = await client.get(
            "/api/landmarks",
            params={"category": category, "district": district} if (category or district) else None,
        )
        r.raise_for_status()
        return r.json()


async def get_landmark_by_name(name: str) -> dict:
    async with _landmarks_client() as client:
        r = await client.get(f"/api/landmarks/name/{name}")
        r.raise_for_status()
        return r.json()


async def search_landmarks(
    q: str,
    category: str | None = None,
    district: str | None = None,
) -> dict:
    async with _landmarks_client() as client:
        params: dict = {"q": q}
        if category:
            params["category"] = category
        if district:
            params["district"] = district
        r = await client.get("/api/landmarks/search", params=params)
        r.raise_for_status()
        return r.json()


async def get_landmark_by_id(id: str) -> dict:
    async with _landmarks_client() as client:
        r = await client.get(f"/api/landmarks/{id}")
        r.raise_for_status()
        return r.json()


async def get_landmark_stats() -> dict:
    async with _landmarks_client() as client:
        r = await client.get("/api/landmarks/stats")
        r.raise_for_status()
        return r.json()


# ---------- 房源（必带 X-User-ID） ----------


async def get_house_by_id(house_id: str) -> dict:
    async with _houses_client() as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                r = await client.get(f"/api/houses/{house_id}")
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPStatusError, httpx.RequestError):
                if attempt == MAX_RETRIES:
                    raise
                continue
    return {}


async def get_house_listings(house_id: str) -> dict:
    async with _houses_client() as client:
        r = await client.get(f"/api/houses/listings/{house_id}")
        r.raise_for_status()
        return r.json()


async def get_houses_by_community(
    community: str,
    listing_platform: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict:
    params: dict = {"community": community}
    if listing_platform:
        params["listing_platform"] = listing_platform
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    async with _houses_client() as client:
        r = await client.get("/api/houses/by_community", params=params)
        r.raise_for_status()
        return r.json()


async def get_houses_by_platform(
    listing_platform: str | None = None,
    district: str | None = None,
    area: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    bedrooms: str | None = None,
    rental_type: str | None = None,
    decoration: str | None = None,
    orientation: str | None = None,
    elevator: str | None = None,
    min_area: int | None = None,
    max_area: int | None = None,
    property_type: str | None = None,
    subway_line: str | None = None,
    max_subway_dist: int | None = None,
    subway_station: str | None = None,
    utilities_type: str | None = None,
    available_from_before: str | None = None,
    commute_to_xierqi_max: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict:
    params: dict = {}
    if listing_platform is not None:
        params["listing_platform"] = listing_platform
    if district is not None:
        params["district"] = district
    if area is not None:
        params["area"] = area
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price
    if bedrooms is not None:
        params["bedrooms"] = bedrooms
    if rental_type is not None:
        params["rental_type"] = rental_type
    if decoration is not None:
        params["decoration"] = decoration
    if orientation is not None:
        params["orientation"] = orientation
    if elevator is not None:
        params["elevator"] = elevator
    if min_area is not None:
        params["min_area"] = min_area
    if max_area is not None:
        params["max_area"] = max_area
    if property_type is not None:
        params["property_type"] = property_type
    if subway_line is not None:
        params["subway_line"] = subway_line
    if max_subway_dist is not None:
        params["max_subway_dist"] = max_subway_dist
    if subway_station is not None:
        params["subway_station"] = subway_station
    if utilities_type is not None:
        params["utilities_type"] = utilities_type
    if available_from_before is not None:
        params["available_from_before"] = available_from_before
    if commute_to_xierqi_max is not None:
        params["commute_to_xierqi_max"] = commute_to_xierqi_max
    if sort_by is not None:
        params["sort_by"] = sort_by
    if sort_order is not None:
        params["sort_order"] = sort_order
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    async with _houses_client() as client:
        r = await client.get("/api/houses/by_platform", params=params or None)
        r.raise_for_status()
        return r.json()


async def get_houses_nearby(
    landmark_id: str,
    max_distance: float | int | None = None,
    listing_platform: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict:
    params: dict = {"landmark_id": landmark_id}
    if max_distance is not None:
        params["max_distance"] = max_distance
    if listing_platform is not None:
        params["listing_platform"] = listing_platform
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    async with _houses_client() as client:
        r = await client.get("/api/houses/nearby", params=params)
        r.raise_for_status()
        return r.json()


async def get_nearby_landmarks(
    community: str,
    type: str | None = None,
    max_distance_m: float | int | None = None,
) -> dict:
    params: dict = {"community": community}
    if type is not None:
        params["type"] = type
    if max_distance_m is not None:
        params["max_distance_m"] = max_distance_m
    async with _houses_client() as client:
        r = await client.get("/api/houses/nearby_landmarks", params=params)
        r.raise_for_status()
        return r.json()


async def get_house_stats() -> dict:
    async with _houses_client() as client:
        r = await client.get("/api/houses/stats")
        r.raise_for_status()
        return r.json()


async def rent_house(house_id: str, listing_platform: str) -> dict:
    async with _houses_client() as client:
        r = await client.post(
            f"/api/houses/{house_id}/rent",
            params={"listing_platform": listing_platform},
        )
        r.raise_for_status()
        return r.json()


async def terminate_rental(house_id: str, listing_platform: str) -> dict:
    async with _houses_client() as client:
        r = await client.post(
            f"/api/houses/{house_id}/terminate",
            params={"listing_platform": listing_platform},
        )
        r.raise_for_status()
        return r.json()


async def take_offline(house_id: str, listing_platform: str) -> dict:
    async with _houses_client() as client:
        r = await client.post(
            f"/api/houses/{house_id}/offline",
            params={"listing_platform": listing_platform},
        )
        r.raise_for_status()
        return r.json()
