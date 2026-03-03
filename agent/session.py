"""会话管理：按 session_id 存储消息历史，新 session 时调用 init 重置房源数据。"""
from tools import rent_api

# session_id -> list of messages (OpenAI 格式)
_sessions: dict[str, list[dict]] = {}
# 已做过 init 的 session_id 集合
_inited: set[str] = set()


def get_messages(session_id: str) -> list[dict]:
    """获取会话消息列表，若不存在则返回空列表。"""
    return _sessions.get(session_id, []).copy()


def append_message(session_id: str, role: str, content: str | None = None, tool_calls: list | None = None) -> None:
    """追加一条消息。role 为 user / assistant / tool。"""
    if session_id not in _sessions:
        _sessions[session_id] = []
    msg = {"role": role}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    _sessions[session_id].append(msg)


def append_tool_message(session_id: str, tool_call_id: str, content: str) -> None:
    """追加一条 role=tool 的消息。"""
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    })


async def ensure_session_inited_async(session_id: str) -> bool:
    """
    若该 session 尚未调用过 init，则调用并标记已初始化。
    返回是否为新初始化的 session。
    """
    if session_id in _inited:
        return False
    await rent_api.init_houses()
    _inited.add(session_id)
    return True
