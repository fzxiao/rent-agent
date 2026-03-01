"""规则解析：从用户输入抽取 API 参数（Mock 模式下替代 LLM）。"""

import re
from typing import Any


def _extract_district(text: str) -> str | None:
    for d in ["东城", "西城", "海淀", "朝阳", "通州", "昌平", "大兴", "房山", "丰台", "顺义"]:
        if d in text:
            return d
    return None


def _extract_bedrooms(text: str) -> str | None:
    if "一居" in text or "1居" in text:
        return "1"
    if "两居" in text or "2居" in text:
        return "2"
    if "三居" in text or "3居" in text:
        return "3"
    return None


def _extract_max_price(text: str) -> int | None:
    m = re.search(r"(\d+)\s*以内|租金\s*(\d+)|预算\s*(\d+)|(\d+)\s*元", text)
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return None


def _extract_max_subway_dist(text: str, bedrooms: str | None) -> int:
    """近地铁：一居 1000，两居及以上 800。离地铁 X 米以内用 X。"""
    m = re.search(r"(\d+)\s*米", text)
    if m:
        return int(m.group(1))
    if "近地铁" in text or "离地铁近" in text:
        if bedrooms == "1":
            return 1000
        return 800
    return 800


def _extract_decoration(text: str) -> str | None:
    if "精装" in text:
        return "精装"
    if "简装" in text:
        return "简装"
    return None


def _extract_sort(text: str) -> tuple[str, str]:
    if "从近到远" in text or "从近到远排" in text:
        return "subway", "asc"
    if "从远到近" in text:
        return "subway", "desc"
    return "subway", "asc"


def parse_query_house(text: str) -> dict[str, Any]:
    """解析查房意图，返回 get_houses_by_platform 的 params。"""
    district = _extract_district(text)
    bedrooms = _extract_bedrooms(text)
    max_price = _extract_max_price(text)
    decoration = _extract_decoration(text)
    sort_by, sort_order = _extract_sort(text)
    max_subway_dist = _extract_max_subway_dist(text, bedrooms)

    params = {
        "page": 1,
        "page_size": 10,
    }
    if district:
        params["district"] = district
    if bedrooms:
        params["bedrooms"] = bedrooms
    if max_price is not None:
        params["max_price"] = max_price
    if decoration:
        params["decoration"] = decoration
    params["sort_by"] = sort_by
    params["sort_order"] = sort_order
    params["max_subway_dist"] = max_subway_dist
    return params


def is_rent_intent(text: str) -> bool:
    return "就租" in text or "租最近" in text or "租第一" in text or "租这套" in text or "租那套" in text


def is_more_intent(text: str) -> bool:
    return "还有其他的吗" in text or "还有吗" in text or "都给出" in text or "都给出来" in text
