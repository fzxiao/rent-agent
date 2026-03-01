"""本地测试：基于 test_cases.json 验证 Agent 输出。"""

import json
from pathlib import Path

import pytest


def load_cases():
    path = Path(__file__).parent / "test_cases.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _chat(client, session_id: str, message: str, model_ip: str = "127.0.0.1") -> dict:
    r = client.post(
        "/api/v1/chat",
        json={"model_ip": model_ip, "session_id": session_id, "message": message},
    )
    assert r.status_code == 200
    return r.json()


def _check_response(response: str, expected: dict) -> tuple[bool, str]:
    """检查 response 是否满足 message_contains 和 expectedHouses。"""
    message_contains = expected.get("message_contains", [])
    expected_houses = expected.get("expectedHouses", [])

    # 尝试解析为 JSON（房源查询完成时）
    try:
        parsed = json.loads(response)
        msg = parsed.get("message", "")
        houses = parsed.get("houses", [])
    except json.JSONDecodeError:
        msg = response
        houses = []

    for kw in message_contains:
        if kw not in msg:
            return False, f"message 应包含 '{kw}'，实际: {msg[:200]}"
    if houses != expected_houses:
        return False, f"houses 应为 {expected_houses}，实际: {houses}"
    return True, ""


@pytest.fixture(autouse=True)
def reset_sessions():
    """每个 test 前清空会话，确保隔离。"""
    from rent_agent import session
    session._sessions.clear()
    yield


def test_ev43_no_results(client):
    """用例 1：东城精装两居 5000 以内 500 米 -> 无"""
    cases = load_cases()
    case = cases[0]
    for rnd in case["rounds"]:
        resp = _chat(client, rnd["session_id"], rnd["user_input"])
        ok, err = _check_response(resp["response"], rnd["expected"])
        assert ok, err


def test_ev46_multi_round(client):
    """用例 2：西城一居 + 还有其他的吗"""
    cases = load_cases()
    case = cases[1]
    for rnd in case["rounds"]:
        resp = _chat(client, rnd["session_id"], rnd["user_input"])
        ok, err = _check_response(resp["response"], rnd["expected"])
        assert ok, err


def test_ev45_rent(client):
    """用例 3：海淀两居 + 就租最近的那套"""
    cases = load_cases()
    case = cases[2]
    for rnd in case["rounds"]:
        resp = _chat(client, rnd["session_id"], rnd["user_input"])
        ok, err = _check_response(resp["response"], rnd["expected"])
        assert ok, err


def test_all_cases(client):
    """顺序执行所有用例（模拟判题器）。"""
    cases = load_cases()
    for case in cases:
        for rnd in case["rounds"]:
            resp = _chat(client, rnd["session_id"], rnd["user_input"])
            ok, err = _check_response(resp["response"], rnd["expected"])
            assert ok, f"session={rnd['session_id']} input={rnd['user_input'][:30]}... {err}"
