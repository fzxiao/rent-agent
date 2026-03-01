"""Mock 租房 API 服务：用于本地测试，模拟真实 API 响应"""
import json
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock 租房 API", version="1.0.0")

# 模拟房源数据：用于 TC-002、TC-003
MOCK_HOUSES = {
    "HF_13": {
        "house_id": "HF_13",
        "district": "西城",
        "bedrooms": 1,
        "subway_distance": 350,
        "price": 4500,
        "decoration": "精装",
        "community": "西城某小区",
    },
    "HF_906": {
        "house_id": "HF_906",
        "district": "海淀",
        "bedrooms": 2,
        "subway_distance": 280,
        "price": 7200,
        "decoration": "精装",
        "community": "海淀某小区",
    },
    "HF_1586": {
        "house_id": "HF_1586",
        "district": "海淀",
        "bedrooms": 2,
        "subway_distance": 450,
        "price": 6800,
        "decoration": "简装",
        "community": "海淀某小区",
    },
    "HF_1876": {
        "house_id": "HF_1876",
        "district": "海淀",
        "bedrooms": 2,
        "subway_distance": 520,
        "price": 6500,
        "decoration": "精装",
        "community": "海淀某小区",
    },
    "HF_706": {
        "house_id": "HF_706",
        "district": "海淀",
        "bedrooms": 2,
        "subway_distance": 600,
        "price": 6200,
        "decoration": "简装",
        "community": "海淀某小区",
    },
    "HF_33": {
        "house_id": "HF_33",
        "district": "海淀",
        "bedrooms": 2,
        "subway_distance": 750,
        "price": 5900,
        "decoration": "简装",
        "community": "海淀某小区",
    },
}

# 已租状态（用于 TC-003 第二轮后 HF_906 被租）
_rented: set[str] = set()


def _require_user_id(x_user_id: str | None = Header(None, alias="X-User-ID")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="缺少 X-User-ID 请求头")
    return x_user_id


@app.post("/api/houses/init")
def houses_init(x_user_id: str | None = Header(None, alias="X-User-ID")) -> dict:
    """房源数据重置"""
    _require_user_id(x_user_id)
    global _rented
    _rented = set()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "action": "reset_user",
            "message": "该用户状态覆盖已清空，房源恢复为初始状态",
            "user_id": x_user_id,
        },
    }


@app.get("/api/landmarks")
def get_landmarks(category: str | None = None, district: str | None = None) -> dict:
    """获取地标列表（简化 Mock）"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {"id": "SS_001", "name": "西二旗站", "category": "subway", "district": "海淀"},
                {"id": "LM_001", "name": "国贸", "category": "landmark", "district": "朝阳"},
            ],
            "total": 2,
        },
    }


@app.get("/api/landmarks/name/{name}")
def get_landmark_by_name(name: str) -> dict:
    """按名称查询地标"""
    return {
        "code": 0,
        "message": "success",
        "data": {"id": "SS_001", "name": name, "latitude": 40.0, "longitude": 116.0},
    }


# 注意：具体路径需在 /api/houses/{house_id} 之前定义，否则 by_platform 等会被当作 house_id
@app.get("/api/houses/by_platform")
def get_houses_by_platform(
    district: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    bedrooms: str | None = None,
    decoration: str | None = None,
    max_subway_dist: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    page: int = 1,
    page_size: int = 10,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> dict:
    """按条件查询房源（Mock 逻辑匹配测试用例）"""
    _require_user_id(x_user_id)

    # TC-001: 东城区精装两居 5000以内 500m地铁 -> 无匹配
    if (
        district and "东城" in district
        and max_price is not None and max_price <= 5000
        and bedrooms and "2" in bedrooms
        and decoration and "精装" in decoration
        and max_subway_dist is not None and max_subway_dist <= 500
    ):
        return {
            "code": 0,
            "message": "success",
            "data": {"items": [], "total": 0, "page_size": page_size},
        }

    # TC-002: 西城 1居 近地铁 按地铁从近到远 -> HF_13
    if district and "西城" in district and bedrooms and "1" in bedrooms:
        if max_subway_dist is None or max_subway_dist >= 350:
            items = [MOCK_HOUSES["HF_13"]]
            if sort_by == "subway" and sort_order == "asc":
                items = sorted(items, key=lambda x: x["subway_distance"])
            return {
                "code": 0,
                "message": "success",
                "data": {"items": items, "total": len(items), "page_size": page_size},
            }

    # TC-003: 海淀 2居 近地铁 按地铁从近到远 -> HF_906, HF_1586, HF_1876, HF_706, HF_33
    if district and "海淀" in district and bedrooms and "2" in bedrooms:
        if max_subway_dist is None or max_subway_dist >= 750:
            candidates = ["HF_906", "HF_1586", "HF_1876", "HF_706", "HF_33"]
            items = [MOCK_HOUSES[h] for h in candidates if h not in _rented]
            if sort_by == "subway" and sort_order == "asc":
                items = sorted(items, key=lambda x: x["subway_distance"])
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": items[:page_size],
                    "total": len(items),
                    "page_size": page_size,
                },
            }

    # 默认返回空
    return {
        "code": 0,
        "message": "success",
        "data": {"items": [], "total": 0, "page_size": page_size},
    }


@app.get("/api/houses/nearby")
def get_houses_nearby(
    landmark_id: str,
    max_distance: int = 2000,
    page: int = 1,
    page_size: int = 10,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> dict:
    """地标附近房源（简化 Mock）"""
    _require_user_id(x_user_id)
    return {
        "code": 0,
        "message": "success",
        "data": {"items": [], "total": 0, "page_size": page_size},
    }


@app.get("/api/houses/{house_id}")
def get_house(house_id: str, x_user_id: str | None = Header(None, alias="X-User-ID")) -> dict:
    """获取单套房源详情"""
    _require_user_id(x_user_id)
    if house_id in MOCK_HOUSES:
        return {
            "code": 0,
            "message": "success",
            "data": {**MOCK_HOUSES[house_id], "status": "已租" if house_id in _rented else "可租"},
        }
    return {"code": 404, "message": "房源不存在", "data": None}


@app.post("/api/houses/{house_id}/rent")
def rent_house(
    house_id: str,
    listing_platform: str = "安居客",
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> dict:
    """租房"""
    _require_user_id(x_user_id)
    _rented.add(house_id)
    h = MOCK_HOUSES.get(house_id, {"house_id": house_id})
    return {
        "code": 0,
        "message": "success",
        "data": {**h, "status": "已租"},
    }


def run() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)


if __name__ == "__main__":
    run()
