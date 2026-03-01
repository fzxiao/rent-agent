"""会话管理：维护 session_id 对应的对话历史与上次房源结果"""
from typing import Any

# 内存存储：session_id -> messages 列表
_sessions: dict[str, list[dict[str, Any]]] = {}

# 上次查询的房源 ID 列表，用于多轮追问（如「还有其他的吗」）
_last_house_ids: dict[str, list[str]] = {}


def get_messages(session_id: str) -> list[dict[str, Any]]:
    """获取会话的对话历史"""
    return _sessions.get(session_id, [])


def append_message(session_id: str, role: str, content: str | None = None, **kwargs: Any) -> None:
    """追加一条消息到会话历史"""
    if session_id not in _sessions:
        _sessions[session_id] = []
    msg: dict[str, Any] = {"role": role, **kwargs}
    if content is not None:
        msg["content"] = content
    _sessions[session_id].append(msg)


def set_last_house_ids(session_id: str, house_ids: list[str]) -> None:
    """保存该 session 上次查询的房源 ID"""
    _last_house_ids[session_id] = house_ids


def get_last_house_ids(session_id: str) -> list[str]:
    """获取该 session 上次查询的房源 ID"""
    return _last_house_ids.get(session_id, [])


def clear_session(session_id: str) -> None:
    """清空会话（可选，用于重置）"""
    if session_id in _sessions:
        del _sessions[session_id]
    if session_id in _last_house_ids:
        del _last_house_ids[session_id]


def get_or_create_messages(session_id: str, user_message: str) -> list[dict[str, Any]]:
    """获取当前会话消息并追加用户输入，返回完整 messages"""
    msgs = get_messages(session_id)
    msgs = msgs.copy()
    msgs.append({"role": "user", "content": user_message})
    return msgs
