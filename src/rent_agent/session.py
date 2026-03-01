"""会话与上下文记忆管理。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    """单会话状态。"""

    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    last_candidate_houses: list[str] = field(default_factory=list)
    last_query_params: dict[str, Any] = field(default_factory=dict)
    last_page: int = 1


_sessions: dict[str, SessionState] = {}


def get_or_create(session_id: str) -> SessionState:
    if session_id not in _sessions:
        _sessions[session_id] = SessionState(session_id=session_id)
    return _sessions[session_id]


def add_message(session_id: str, role: str, content: str) -> None:
    s = get_or_create(session_id)
    s.messages.append({"role": role, "content": content})


def set_last_candidates(session_id: str, house_ids: list[str]) -> None:
    s = get_or_create(session_id)
    s.last_candidate_houses = house_ids


def set_last_query(session_id: str, params: dict, page: int = 1) -> None:
    s = get_or_create(session_id)
    s.last_query_params = params
    s.last_page = page


def get_last_candidates(session_id: str) -> list[str]:
    s = get_or_create(session_id)
    return s.last_candidate_houses


def get_last_query(session_id: str) -> tuple[dict, int]:
    s = get_or_create(session_id)
    return s.last_query_params, s.last_page


def get_messages(session_id: str) -> list[dict[str, str]]:
    s = get_or_create(session_id)
    return s.messages.copy()


def is_new_session(session_id: str) -> bool:
    return session_id not in _sessions or len(_sessions[session_id].messages) == 0
