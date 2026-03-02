"""配置模块 - 工号、租房 API BaseURL 等"""
import os

# 工号，由环境变量或默认值提供
X_USER_ID = os.environ.get("X_USER_ID", "f0092481")

# 租房 API BaseURL
HOUSING_API_BASE = os.environ.get("HOUSING_API_BASE", "http://7.225.29.223:8080")

# Agent 监听端口
AGENT_PORT = int(os.environ.get("AGENT_PORT", "8191"))

# LLM 端口固定 8888
LLM_PORT = 8888
