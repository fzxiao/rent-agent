"""Agent 执行过程中的 API 调用日志记录，便于分析问题"""
import json
import os
import shutil
import time
from contextvars import ContextVar
from pathlib import Path

# 当前请求的 session_id，由 handler 设置
_current_session_id: ContextVar[str] = ContextVar("api_log_session_id", default="")

# 日志目录，可通过环境变量 AGENT_LOG_DIR 覆盖
LOG_DIR = Path(os.getenv("AGENT_LOG_DIR", str(Path(__file__).resolve().parent.parent / "logs")))

# 本次运行的日志文件路径，由 rotate_log_on_startup 设置
LOG_FILE: Path = LOG_DIR / "agent_api_calls.log"


def rotate_log_on_startup() -> Path:
    """
    Agent 启动时调用：若存在上次的 agent_api_calls.log，则改名备份。
    本次运行始终写入 agent_api_calls.log（固定文件名）。
    """
    global LOG_FILE
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    legacy_file = LOG_DIR / "agent_api_calls.log"
    if legacy_file.exists():
        backup_path = LOG_DIR / f"agent_api_calls_backup_{time.strftime('%Y%m%d_%H%M%S', time.localtime())}.log"
        try:
            shutil.move(str(legacy_file), str(backup_path))
        except OSError:
            pass

    LOG_FILE = legacy_file
    return LOG_FILE


def set_session_id(session_id: str) -> None:
    """设置当前请求的 session_id"""
    _current_session_id.set(session_id)


def get_session_id() -> str:
    """获取当前 session_id"""
    try:
        return _current_session_id.get()
    except LookupError:
        return ""


def _write_log(entry: dict) -> None:
    """写入单条 JSON 行到日志文件"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_rental_api(
    method: str,
    path: str,
    params: dict | None,
    status_code: int,
    duration_ms: float,
    result_preview: str = "",
    error: str | None = None,
) -> None:
    """记录租房 API 调用"""
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "api_type": "rental",
        "session_id": get_session_id(),
        "method": method,
        "path": path,
        "params": params or {},
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "result_preview": result_preview[:200] if result_preview else "",
        "error": error,
    }
    _write_log(entry)


def log_llm_api(
    url: str,
    messages_count: int,
    has_tools: bool,
    status_code: int,
    duration_ms: float,
    tool_calls_count: int = 0,
    content_preview: str = "",
    error: str | None = None,
) -> None:
    """记录 LLM API 调用"""
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "api_type": "llm",
        "session_id": get_session_id(),
        "url": url,
        "messages_count": messages_count,
        "has_tools": has_tools,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "tool_calls_count": tool_calls_count,
        "content_preview": content_preview[:150] if content_preview else "",
        "error": error,
    }
    _write_log(entry)


def log_tool_execution(
    tool_name: str,
    args: dict,
    result_preview: str,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """记录工具执行（汇总一次 LLM 返回后的所有 tool 调用）"""
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "api_type": "tool",
        "session_id": get_session_id(),
        "tool_name": tool_name,
        "args": args,
        "result_preview": result_preview[:300] if result_preview else "",
        "duration_ms": round(duration_ms, 2),
        "error": error,
    }
    _write_log(entry)


def log_request_start(session_id: str, message_preview: str) -> None:
    """记录请求开始"""
    set_session_id(session_id)
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "api_type": "request_start",
        "session_id": session_id,
        "message_preview": message_preview[:100] if message_preview else "",
    }
    _write_log(entry)


def log_request_end(session_id: str, status: str, duration_ms: int) -> None:
    """记录请求结束"""
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "api_type": "request_end",
        "session_id": session_id,
        "status": status,
        "duration_ms": duration_ms,
    }
    _write_log(entry)
