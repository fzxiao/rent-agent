"""
会话上下文管理：按 session_id 存储历史消息、上一轮候选房源、查询条件等。
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionContext:
    """单个会话的上下文"""

    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)  # [{role, content}, ...]
    last_house_ids: list[str] = field(default_factory=list)  # 上一轮候选房源 ID 列表（保持顺序）
    last_query_params: dict[str, Any] = field(default_factory=dict)  # 上一轮查询参数
    last_page: int = 1
    last_total: int = 0
    initialized: bool = False  # 是否已调用 init


class SessionManager:
    """会话管理器"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}

    def get_or_create(self, session_id: str) -> SessionContext:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id=session_id)
        return self._sessions[session_id]

    def is_new_session(self, session_id: str) -> bool:
        """是否为新 session（首次出现，需调用 init）"""
        return session_id not in self._sessions or not self._sessions[session_id].initialized

    def mark_initialized(self, session_id: str) -> None:
        ctx = self.get_or_create(session_id)
        ctx.initialized = True

    def add_message(self, session_id: str, role: str, content: str) -> None:
        ctx = self.get_or_create(session_id)
        ctx.messages.append({"role": role, "content": content})

    def set_last_houses(self, session_id: str, house_ids: list[str], params: dict[str, Any], page: int, total: int) -> None:
        ctx = self.get_or_create(session_id)
        ctx.last_house_ids = house_ids
        ctx.last_query_params = params
        ctx.last_page = page
        ctx.last_total = total

    def get_last_houses(self, session_id: str) -> list[str]:
        ctx = self.get_or_create(session_id)
        return ctx.last_house_ids.copy()

    def get_last_query_params(self, session_id: str) -> dict[str, Any]:
        ctx = self.get_or_create(session_id)
        return ctx.last_query_params.copy()

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
        ctx = self.get_or_create(session_id)
        return ctx.messages.copy()

    def get_context_summary(self, session_id: str) -> str:
        """生成供 LLM 参考的上下文摘要"""
        ctx = self.get_or_create(session_id)
        parts = []
        if ctx.last_house_ids:
            parts.append(f"上一轮候选房源（按顺序）：{ctx.last_house_ids}")
        if ctx.last_query_params:
            parts.append(f"上一轮查询条件：{ctx.last_query_params}")
        if ctx.last_page > 1:
            parts.append(f"上一轮已查第 {ctx.last_page} 页，共 {ctx.last_total} 条")
        if not parts:
            return ""
        return "\n".join(parts)
