"""统一日志配置：按日期分文件，含 session_id/request_id。"""
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

import structlog

from config import settings

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
Path(settings.trace_dir).mkdir(parents=True, exist_ok=True)

_log_file_handle = None


def _add_context(logger, method_name, event_dict):
    """可选的 context 由调用方 bind session_id=..., request_id=... 传入。"""
    return event_dict


def _write_json_to_file(logger, method_name, event_dict):
    """将事件写成 JSON 行写入当日日志文件。"""
    global _log_file_handle
    if _log_file_handle is None:
        date_suffix = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"agent_{date_suffix}.log"
        _log_file_handle = open(log_file, "a", encoding="utf-8")
    try:
        line = json.dumps(event_dict, ensure_ascii=False) + "\n"
        _log_file_handle.write(line)
        _log_file_handle.flush()
    except Exception:
        pass
    return event_dict


def setup_logging():
    """配置 structlog，写入 logs/agent_{date}.log。"""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_context,
        structlog.processors.StackInfoRenderer(),
        _write_json_to_file,
        structlog.dev.ConsoleRenderer(),
    ]
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = ""):
    """获取带 name 的 logger，调用时 bind(session_id=..., request_id=...) 便于追踪。"""
    return structlog.get_logger(name or "agent")
