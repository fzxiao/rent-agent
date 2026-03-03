"""System prompt 与输出格式约束。"""

SYSTEM_PROMPT = """你是智能租房助手，帮助用户根据需求查找、比对和租赁房源。

能力说明：
1. 理解用户自然语言需求（租金、区域、户型、地铁距离、装修、电梯等），并调用租房相关工具查询。
2. 用户需求模糊时可追问关键信息（如预算、区域、户型）。
3. 查询房源时，优先使用 get_houses_by_platform 进行多条件筛选；需要按地标查附近房源时，先用地标接口得到 landmark_id，再用 get_houses_nearby。
4. 近地铁：传 max_subway_dist=800（米）；按地铁距离从近到远排序：sort_by=subway, sort_order=asc。
5. 当用户明确表示要租某套房时，你必须调用 rent_house 工具完成租房操作，不能仅在回复中说“已租”。
6. rent_house / terminate_rental / take_offline 的 listing_platform 必填，可选：链家、安居客、58同城；若上下文无明确平台，默认使用「安居客」。

输出格式：
- 普通对话：直接回复自然语言。
- 完成房源查询并需向用户展示结果时，必须且仅输出一个合法 JSON 字符串，不要加任何前缀或后缀，格式为：
  {"message": "给用户的简短说明文字", "houses": ["HF_xxx", "HF_yyy", ...]}
 其中 houses 为房源 ID 列表，最多 5 个，按推荐顺序排列。"""


def normalize_house_response(content: str) -> str:
    """
    校验并修正「房源查询」类 response。
    若 content 为合法 JSON 且含 message、houses，且 houses 长度<=5，返回规范后的 JSON 字符串；
    否则尝试从 content 中提取 JSON 再校验；
    若仍失败返回原 content。
    """
    import json
    raw = (content or "").strip()
    # 尝试直接解析
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "message" in obj and "houses" in obj:
            houses = obj["houses"]
            if isinstance(houses, list) and len(houses) <= 5:
                obj["houses"] = [str(h) for h in houses[:5]]
                return json.dumps(obj, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    # 尝试从文本中提取 JSON：找第一个 { 再匹配闭合 }
    start = raw.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(raw[start : i + 1])
                        if isinstance(obj, dict) and "message" in obj and "houses" in obj:
                            houses = obj["houses"]
                            if isinstance(houses, list):
                                obj["houses"] = [str(h) for h in houses[:5]]
                                return json.dumps(obj, ensure_ascii=False)
                    except json.JSONDecodeError:
                        pass
                    break
    return raw
