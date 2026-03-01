"""配置：工号、租房 API BaseURL、是否 Mock 等。"""

import os
from typing import Literal

# 工号，用于 X-User-ID
USER_ID = os.environ.get("RENT_AGENT_USER_ID", "test_user")

# 租房 API BaseURL
RENTAL_API_BASE = os.environ.get(
    "RENTAL_API_BASE",
    "http://7.225.29.223:8080",
)

# 是否使用 Mock（本地无法访问 API 时）
USE_MOCK = os.environ.get("RENT_AGENT_USE_MOCK", "true").lower() in ("1", "true", "yes")

# LLM 端口固定 8888
LLM_PORT = 8888
