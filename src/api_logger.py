"""
API 调用日志：记录 Agent 执行过程中的 API 调用信息，便于迭代分析。
每次运行前备份上次日志，写入固定文件名。
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

LOG_FILE = "agent_api_log.jsonl"
LOG_DIR = Path(__file__).resolve().parent.parent


def _backup_and_prepare() -> None:
    log_path = LOG_DIR / LOG_FILE
    if log_path.exists():
        bak_name = f"agent_api_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.bak"
        bak_path = LOG_DIR / bak_name
        try:
            log_path.rename(bak_path)
        except OSError:
            pass


def _ensure_log_ready() -> None:
    """首次写入时备份旧日志（仅进程内首次）"""
    if not hasattr(_ensure_log_ready, "_done"):
        _backup_and_prepare()
        _ensure_log_ready._done = True  # type: ignore


def _write_line(record: dict) -> None:
    _ensure_log_ready()
    log_path = LOG_DIR / LOG_FILE
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class ApiLogger:
    """API 调用日志记录器"""

    def log_api(
        self,
        operation_id: str,
        method: str,
        path: str,
        params: dict,
        result: dict,
        session_id: str = "",
    ) -> None:
        record = {
            "ts": datetime.now().isoformat(),
            "type": "api",
            "session_id": session_id,
            "operation_id": operation_id,
            "method": method,
            "path": path,
            "params": params,
            "success": result.get("success", False),
            "status_code": result.get("status_code"),
            "error": result.get("error"),
            "data_summary": _summarize_data(result.get("data")),
        }
        _write_line(record)

    def log_llm(self, session_id: str, llm_out: dict) -> None:
        record = {
            "ts": datetime.now().isoformat(),
            "type": "llm",
            "session_id": session_id,
            "intent": llm_out.get("intent"),
            "reply": llm_out.get("reply", "")[:200],
            "action": llm_out.get("action"),
            "actions": llm_out.get("actions"),
        }
        _write_line(record)


def _summarize_data(data: Any) -> Optional[Any]:
    if data is None:
        return None
    if isinstance(data, dict):
        items = data.get("items") or data.get("data")
        if isinstance(items, list):
            return {"count": len(items), "total": data.get("total"), "sample_ids": [x.get("house_id") or x.get("id") for x in items[:3] if isinstance(x, dict)]}
        return {"keys": list(data.keys())[:5]}
    return str(data)[:100]
