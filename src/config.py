"""配置模块：工号、租房 API BaseURL 等可从环境变量读取"""
import os

# 工号，用于 X-User-ID，判题器按工号隔离
USER_ID = os.environ.get("X_USER_ID", "f00954281")

# 租房 API BaseURL
RENT_API_BASE_URL = os.environ.get("RENT_API_BASE_URL", "http://7.225.29.223:8080")

# LLM 端口固定 8888，IP 由 model_ip 下发
LLM_PORT = 8888

# Agent 监听端口
AGENT_PORT = int(os.environ.get("AGENT_PORT", "8191"))

# 房源结果最多返回条数
MAX_HOUSES = 5

# 近地铁距离：一居 1000 米，两居及以上 800 米
MAX_SUBWAY_DIST_ONE_BED = 1000
MAX_SUBWAY_DIST_TWO_BED_PLUS = 800
