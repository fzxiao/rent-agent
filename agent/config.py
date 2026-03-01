"""Agent 配置"""
import os

# 租房 API 基础 URL，可通过环境变量覆盖（本地测试指向 Mock）
RENTAL_API_BASE_URL = os.getenv("RENTAL_API_BASE_URL", "http://localhost:8080")

# 用户工号，比赛时由判题器下发，本地测试使用默认值
DEFAULT_USER_ID = os.getenv("X_USER_ID", "test_user_001")

# Agent 监听端口
AGENT_PORT = int(os.getenv("AGENT_PORT", "8191"))
