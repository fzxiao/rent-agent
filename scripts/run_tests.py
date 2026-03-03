"""
本地测试运行器：读取用例 JSON，向本地 Agent 发送请求，校验 message_contains 与 expectedHouses。
用法：先启动 Agent (uv run uvicorn main:app --host 0.0.0.0 --port 8190)，再执行
  python scripts/run_tests.py [--base http://localhost:8190] [cases.json]
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

# 默认用例文件与 Agent 地址
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES = ROOT / "tests" / "fixtures" / "sample_cases.json"
DEFAULT_BASE = "http://localhost:8190"
# 本地测试用的 model_ip（需可访问的 LLM，否则用例会失败）
DEFAULT_MODEL_IP = "127.0.0.1"


def load_cases(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def check_message_contains(response: str, expected: list[str]) -> tuple[bool, list[str]]:
    """response 中是否包含所有 expected 子串。返回 (是否通过, 缺失列表)。"""
    missing = []
    for s in expected:
        if s not in response:
            missing.append(s)
    return len(missing) == 0, missing


def parse_houses_from_response(response: str) -> list[str]:
    """从 response 中解析 houses 列表（可能为 JSON 字符串）。"""
    raw = (response or "").strip()
    if not raw:
        return []
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "houses" in obj:
            h = obj["houses"]
            return list(h) if isinstance(h, list) else []
    except json.JSONDecodeError:
        pass
    return []


def check_houses(response: str, expected_houses: list[str]) -> bool:
    """response 解析出的 houses 与 expectedHouses 集合相等（顺序可忽略）。"""
    got = set(parse_houses_from_response(response))
    exp = set(expected_houses or [])
    return got == exp


def run_round(base_url: str, model_ip: str, session_id: str, user_input: str) -> str:
    """发送单轮请求，返回 response 字符串。"""
    r = httpx.post(
        f"{base_url.rstrip('/')}/api/v1/chat",
        json={
            "model_ip": model_ip,
            "session_id": session_id,
            "message": user_input,
        },
        timeout=120.0,
    )
    r.raise_for_status()
    body = r.json()
    return body.get("response", "")


def main():
    parser = argparse.ArgumentParser(description="Run agent test cases locally.")
    parser.add_argument("cases_file", nargs="?", default=str(DEFAULT_CASES), help="Path to JSON cases file")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Agent base URL")
    parser.add_argument("--model-ip", default=DEFAULT_MODEL_IP, help="LLM model_ip for chat")
    args = parser.parse_args()

    cases_path = Path(args.cases_file)
    if not cases_path.is_file():
        print(f"Cases file not found: {cases_path}", file=sys.stderr)
        sys.exit(1)

    cases = load_cases(cases_path)
    passed = 0
    failed = 0
    for case_idx, case in enumerate(cases):
        rounds = case.get("rounds", [])
        for round_idx, round_data in enumerate(rounds):
            session_id = round_data.get("session_id", "")
            user_input = round_data.get("user_input", "")
            expected = round_data.get("expected", {})
            message_contains = expected.get("message_contains", [])
            expected_houses = expected.get("expectedHouses", [])

            try:
                response = run_round(args.base, args.model_ip, session_id, user_input)
            except Exception as e:
                print(f"[FAIL] case={case_idx} round={round_idx} session_id={session_id} error={e}")
                failed += 1
                continue

            ok_msg, missing = check_message_contains(response, message_contains)
            ok_houses = check_houses(response, expected_houses)
            if ok_msg and ok_houses:
                print(f"[PASS] case={case_idx} round={round_idx} session_id={session_id}")
                passed += 1
            else:
                print(f"[FAIL] case={case_idx} round={round_idx} session_id={session_id}")
                if not ok_msg:
                    print(f"  message_contains missing: {missing}")
                if not ok_houses:
                    print(f"  expectedHouses={expected_houses}, got={parse_houses_from_response(response)}")
                failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
