"""会话与上下文管理 - 按 session_id 存储记忆"""
from dataclasses import dataclass, field
from typing import Any

# 全局会话存储: session_id -> SessionContext
_sessions: dict[str, "SessionContext"] = {}


@dataclass
class SessionContext:
    """单个会话的上下文记忆"""

    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)  # 历史 user/assistant
    last_candidate_houses: list[str] = field(default_factory=list)  # 上一轮候选房源 ID 列表（保持顺序）
    last_query_params: dict[str, Any] = field(default_factory=dict)  # 上一轮查询参数
    last_api: str = "get_houses_by_platform"  # 上一轮调用的 API
    last_page: int = 1
    last_total: int = 0
    initialized: bool = False  # 是否已调用 init

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def set_candidate_houses(
        self,
        house_ids: list[str],
        params: dict[str, Any],
        api: str,
        page: int,
        total: int,
    ) -> None:
        self.last_candidate_houses = house_ids[:5]
        self.last_query_params = {k: v for k, v in params.items() if k != "_api"}
        self.last_api = api
        self.last_page = page
        self.last_total = total

    def get_messages_for_llm(self, max_turns: int = 10) -> list[dict[str, str]]:
        """获取最近 N 轮对话供 LLM 使用"""
        return self.messages[-(max_turns * 2) :] if self.messages else []


def get_or_create_session(session_id: str) -> SessionContext:
    if session_id not in _sessions:
        _sessions[session_id] = SessionContext(session_id=session_id)
    return _sessions[session_id]


def mark_initialized(session_id: str) -> None:
    ctx = get_or_create_session(session_id)
    ctx.initialized = True


def is_initialized(session_id: str) -> bool:
    ctx = get_or_create_session(session_id)
    return ctx.initialized


def reset_session(session_id: str) -> None:
    """重置会话（测试用）"""
    if session_id in _sessions:
        del _sessions[session_id]
