"""LLM 工具定义：将租房 API 转为 Function Calling 格式"""
from typing import Any

# 租房相关工具定义，供 LLM 进行 API 规划和填参
RENTAL_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "houses_init",
            "description": "房源数据重置。每新起一个 session 必须调用，保证用例可重复执行。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_houses_by_platform",
            "description": "按条件查询可租房源，支持区域、价格、户型、装修、地铁距离、排序等。主查询接口。",
            "parameters": {
                "type": "object",
                "properties": {
                    "district": {"type": "string", "description": "行政区，如 海淀、朝阳、西城、东城"},
                    "min_price": {"type": "integer", "description": "最低月租金（元）"},
                    "max_price": {"type": "integer", "description": "最高月租金（元）"},
                    "bedrooms": {"type": "string", "description": "卧室数，如 1、2、1,2"},
                    "decoration": {"type": "string", "description": "装修：精装、简装、豪华、毛坯、空房"},
                    "max_subway_dist": {
                        "type": "integer",
                        "description": "最大地铁距离（米）。近地铁建议800，地铁可达1000",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序字段：price(价格)、area(面积)、subway(地铁距离)",
                        "enum": ["price", "area", "subway"],
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "排序方向：asc 升序、desc 降序",
                        "enum": ["asc", "desc"],
                    },
                    "page": {"type": "integer", "description": "页码，默认1"},
                    "page_size": {"type": "integer", "description": "每页条数，默认10，最大10000"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_house",
            "description": "根据房源 ID 获取单套房源详情",
            "parameters": {
                "type": "object",
                "properties": {
                    "house_id": {"type": "string", "description": "房源 ID，如 HF_2001"},
                },
                "required": ["house_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rent_house",
            "description": "租房操作。将指定房源设为已租，必须调用此 API 才算完成租房。",
            "parameters": {
                "type": "object",
                "properties": {
                    "house_id": {"type": "string", "description": "房源 ID"},
                    "listing_platform": {
                        "type": "string",
                        "description": "挂牌平台",
                        "enum": ["链家", "安居客", "58同城"],
                    },
                },
                "required": ["house_id", "listing_platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_landmark_by_name",
            "description": "按名称精确查询地标，如西二旗站、百度。用于后续 nearby 查房。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "地标名称"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_houses_nearby",
            "description": "以地标为圆心查询附近房源，需先通过 get_landmark_by_name 获得 landmark_id",
            "parameters": {
                "type": "object",
                "properties": {
                    "landmark_id": {"type": "string", "description": "地标 ID 或名称"},
                    "max_distance": {"type": "integer", "description": "最大直线距离（米），默认2000"},
                    "page": {"type": "integer"},
                    "page_size": {"type": "integer"},
                },
                "required": ["landmark_id"],
            },
        },
    },
]
