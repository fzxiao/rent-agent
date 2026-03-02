"""API 调用日志 - 便于迭代分析"""
import json
import logging
from datetime import datetime
from pathlib import Path

LOG_FILE = "agent_api_log.jsonl"
LOG_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)


def _backup_existing_log() -> None:
    """写入新日志前备份现有日志（每次运行启动时调用）"""
    log_path = LOG_DIR / LOG_FILE
    if log_path.exists():
        bak_name = f"agent_api_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.bak"
        bak_path = LOG_DIR / bak_name
        try:
            log_path.rename(bak_path)
        except OSError:
            pass


def log_run_start() -> None:
    """记录本次运行开始，确保日志文件在启动时即生成"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": "",
        "api": "_run_start",
        "url": "",
        "params": {},
        "status_code": 0,
        "response_summary": "agent started",
    }
    log_path = LOG_DIR / LOG_FILE
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning("Failed to write API log: %s", e)


def log_api_call(
    session_id: str,
    api_name: str,
    url: str,
    params: dict,
    status_code: int,
    response_summary: str | None = None,
) -> None:
    """记录单次 API 调用"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "api": api_name,
        "url": url,
        "params": params,
        "status_code": status_code,
        "response_summary": response_summary[:500] if response_summary else None,
    }
    log_path = LOG_DIR / LOG_FILE
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning("Failed to write API log: %s", e)
