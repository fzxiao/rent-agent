"""Agent 配置，支持环境变量覆盖。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 比赛平台用户工号，用于 X-User-ID
    rent_user_id: str = "f00952481"
    # 租房 API 地址
    rent_api_base: str = "http://7.225.29.223:8080"
    # Agent 监听端口
    agent_port: int = 8190
    # LLM 端口（固定）
    llm_port: int = 8888

    # 日志与 Trace
    log_level: str = "INFO"
    enable_trace_export: bool = True
    enable_retry: bool = True
    trace_dir: str = "logs/traces"


settings = Settings()
