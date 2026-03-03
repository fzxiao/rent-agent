"""将租房 OpenAPI 转为 OpenAI tools 格式（JSON Schema）。"""
import json
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = ROOT / "租房API接口.json"

# 对部分 tool 的 description 做增强，便于 LLM 选参
DESCRIPTION_OVERRIDES = {
    "get_houses_by_platform": (
        "查询可租房源，支持行政区、价格、户型、地铁距离、装修、电梯等筛选。"
        "近地铁：传 max_subway_dist=800（米）；按地铁距离从近到远排序：sort_by=subway, sort_order=asc。"
        "listing_platform 不传则默认安居客；传 链家/安居客/58同城 则只返回该平台。"
    ),
    "get_houses_nearby": (
        "以地标为圆心查附近可租房源，返回直线距离、步行距离、步行时间。"
        "需先用地标接口获得 landmark_id 或地标名称。max_distance 单位米，默认 2000。"
    ),
}


def _openapi_param_to_json_schema(param: dict) -> dict:
    """单条 OpenAPI parameter 转为 JSON Schema property."""
    schema = param.get("schema", {})
    prop = {
        "type": schema.get("type", "string"),
        "description": schema.get("description", ""),
    }
    if "enum" in schema:
        prop["enum"] = schema["enum"]
    if schema.get("type") == "integer":
        pass
    if schema.get("type") == "number":
        pass
    return prop


def _build_parameters(openapi_params: list) -> dict:
    """OpenAPI parameters 转为 OpenAI parameters (JSON Schema object)."""
    if not openapi_params:
        return {"type": "object", "properties": {}}
    properties = {}
    required = []
    for p in openapi_params:
        name = p["name"]
        # OpenAI 中 sort_by 等若用 enum 更易生成正确值
        schema = p.get("schema", {})
        prop = _openapi_param_to_json_schema(p)
        if name == "sort_by" and "enum" not in prop:
            prop["enum"] = ["price", "area", "subway"]
        if name == "sort_order" and "enum" not in prop:
            prop["enum"] = ["asc", "desc"]
        properties[name] = prop
        if p.get("required", False):
            required.append(name)
    return {
        "type": "object",
        "properties": properties,
        "required": required if required else [],
    }


def load_openapi() -> dict:
    """加载 OpenAPI 文档。"""
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def openapi_to_openai_tools() -> list[dict]:
    """将 OpenAPI paths 转为 OpenAI tools 数组。"""
    doc = load_openapi()
    paths = doc.get("paths", {})
    tools = []
    for path_str, path_item in paths.items():
        for method, op in path_item.items():
            if method.lower() not in ("get", "post"):
                continue
            op_id = op.get("operationId")
            if not op_id:
                continue
            desc = op.get("description") or op.get("summary", "")
            if op_id in DESCRIPTION_OVERRIDES:
                desc = DESCRIPTION_OVERRIDES[op_id]
            params = op.get("parameters", [])
            parameters = _build_parameters(params)
            tools.append({
                "type": "function",
                "function": {
                    "name": op_id,
                    "description": desc,
                    "parameters": parameters,
                },
            })
    return tools


def get_tools() -> list[dict]:
    """返回 OpenAI 格式的 tools，供 LLM 请求使用。"""
    return openapi_to_openai_tools()
