"""API 调用日志模块：记录 LLM 与租房 API 调用，固定文件名，写入前备份上次日志。"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

LOG_FILENAME = "agent_api_log.jsonl"
LOG_DIR = Path(__file__).resolve().parent.parent.parent


def _ensure_log_dir() -> Path:
    """确保日志目录存在。"""
    log_path = LOG_DIR / LOG_FILENAME
    return log_path


def _backup_existing_log() -> None:
    """若存在当前日志文件，重命名为带时间戳的备份。"""
    log_path = LOG_DIR / LOG_FILENAME
    if log_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = LOG_DIR / f"agent_api_log_{ts}.jsonl"
        log_path.rename(backup_path)


def log_api_call(
    session_id: str,
    call_type: str,
    api_name: str,
    params: dict[str, Any],
    status_code: int | None = None,
    response_summary: Any = None,
    url: str | None = None,
) -> None:
    """
    记录 API 调用（租房 API 或 LLM）。
    call_type: "rental_api" | "llm"
    """
    entry = {
        "ts": datetime.now().isoformat(),
        "session_id": session_id,
        "call_type": call_type,
        "api": api_name,
        "params": params,
        "status_code": status_code,
        "response_summary": _truncate_summary(response_summary),
    }
    if url:
        entry["url"] = url

    log_path = _ensure_log_dir()
    # 首次写入时备份
    if not log_path.exists():
        pass  # 新文件，无需备份
    # 注意：每次启动新会话/新进程时备份，由调用方在适当时机调用 prepare_log
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _truncate_summary(obj: Any, max_len: int = 500) -> Any:
    """截断过长的响应摘要。"""
    if obj is None:
        return None
    s = str(obj) if not isinstance(obj, (str, int, float, bool)) else obj
    if isinstance(s, str) and len(s) > max_len:
        return s[:max_len] + "..."
    return s


def prepare_log_for_new_run() -> None:
    """
    新一次运行前调用：备份现有日志，清空或创建新日志文件。
    固定文件名 agent_api_log.jsonl，上次记录改名备份。
    """
    log_path = LOG_DIR / LOG_FILENAME
    if log_path.exists():
        _backup_existing_log()
    # 备份后当前文件已不存在，后续 log_api_call 会创建新文件
