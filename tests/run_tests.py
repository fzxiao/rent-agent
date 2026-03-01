"""测试运行器：读取用例、调用 Agent、校验 response 与 expectedHouses"""
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_PATH = ROOT / "tests" / "test_cases.json"
AGENT_URL = "http://127.0.0.1:8191/api/v1/chat"
MOCK_API_URL = "http://localhost:8081"
# 本地测试用的 Mock LLM 地址（需先启动 mock_llm.py）
MOCK_LLM_IP = "127.0.0.1"  # mock_llm 监听 8888


def load_test_cases() -> list[dict]:
    """加载测试用例"""
    with open(TEST_CASES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def check_message_contains(response: str, expected: list[str], is_json: bool = False) -> tuple[bool, str]:
    """
    检查 response 是否包含 expected 中的关键词。
    若 is_json，则从 JSON 的 message 字段检查。
    """
    text = response
    if is_json:
        try:
            obj = json.loads(response)
            text = obj.get("message", "")
        except json.JSONDecodeError:
            pass
    text_lower = text.lower()
    for kw in expected:
        if kw.lower() not in text_lower:
            return False, f"response 中未包含关键词: {kw}"
    return True, ""


def check_houses(response: str, expected: list[str]) -> tuple[bool, str]:
    """检查 houses 是否与 expected 一致（顺序可放宽为包含关系）"""
    try:
        obj = json.loads(response)
    except json.JSONDecodeError:
        return False, "response 不是合法 JSON"
    houses = obj.get("houses", [])
    if not isinstance(houses, list):
        return False, "houses 不是数组"
    # 顺序可放宽：expected 中的每个都应在 houses 中，且数量一致
    if len(houses) != len(expected):
        return False, f"houses 数量不符: 期望 {len(expected)}, 实际 {len(houses)}"
    for h in expected:
        if h not in houses:
            return False, f"缺少房源: {h}"
    return True, ""


def run_round(
    session_id: str,
    user_input: str,
    model_ip: str = MOCK_LLM_IP,
) -> dict:
    """执行单轮请求"""
    payload = {
        "model_ip": model_ip,
        "session_id": session_id,
        "message": user_input,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(AGENT_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


def run_test_case(tc: dict, model_ip: str = MOCK_LLM_IP) -> tuple[bool, list[str]]:
    """运行单个测试用例，返回 (是否通过, 错误信息列表)"""
    errors: list[str] = []
    for rnd in tc.get("rounds", []):
        session_id = rnd["session_id"]
        user_input = rnd["user_input"]
        expected = rnd.get("expected", {})

        try:
            result = run_round(session_id, user_input, model_ip)
        except Exception as e:
            errors.append(f"请求失败: {e}")
            return False, errors

        response = result.get("response", "")

        # 校验 message_contains
        msg_contains = expected.get("message_contains", [])
        if msg_contains:
            is_json = bool(expected.get("expectedHouses") is not None and expected.get("expectedHouses"))
            ok, err = check_message_contains(response, msg_contains, is_json=False)
            if not ok:
                errors.append(f"message_contains 校验失败: {err}")

        # 校验 expectedHouses
        exp_houses = expected.get("expectedHouses")
        if exp_houses is not None:
            # 可能是 JSON 字符串或已是对象
            if isinstance(response, str) and response.strip().startswith("{"):
                ok, err = check_houses(response, exp_houses)
            else:
                ok, err = False, "房源查询场景下 response 应为 JSON 字符串"
            if not ok:
                errors.append(f"expectedHouses 校验失败: {err}")

    return len(errors) == 0, errors


def main() -> int:
    """主入口"""
    model_ip = sys.argv[1] if len(sys.argv) > 1 else MOCK_LLM_IP

    print("加载测试用例...")
    cases = load_test_cases()
    print(f"共 {len(cases)} 个用例\n")

    passed = 0
    failed = 0
    for tc in cases:
        tid = tc.get("test_id", "?")
        desc = tc.get("description", "")
        print(f"[{tid}] {desc} ... ", end="", flush=True)
        ok, errs = run_test_case(tc, model_ip)
        if ok:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            for e in errs:
                print(f"  - {e}")
            failed += 1

    print(f"\n总计: {passed} 通过, {failed} 失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
