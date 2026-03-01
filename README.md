# 租房 AI Agent - 智找安居·马年省心办

基于 Plan 实现的租房 Agent，支持本地 Mock 测试与真实 API 调用。

## 快速开始

### 安装

```bash
uv sync
```

### 本地测试（Mock 模式）

```bash
uv run python -m pytest tests/test_agent.py -v
```

### 启动服务

```bash
# Mock 模式（默认，无需外网 API）
RENT_AGENT_USE_MOCK=true uv run uvicorn rent_agent.main:app --host 0.0.0.0 --port 8191

# 真实 API 模式
RENT_AGENT_USE_MOCK=false RENT_AGENT_USER_ID=你的工号 uv run uvicorn rent_agent.main:app --host 0.0.0.0 --port 8191
```

### 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| RENT_AGENT_USE_MOCK | 是否 Mock（本地无 API 时用 true） | true |
| RENT_AGENT_USER_ID | 工号，用于 X-User-ID | test_user |
| RENTAL_API_BASE | 租房 API 地址 | http://7.225.29.223:8080 |

## 项目结构

- `src/rent_agent/` - Agent 实现
  - `agent.py` - 主逻辑
  - `api_client.py` - 租房 API 客户端（含 Mock）
  - `llm_client.py` - LLM 客户端
  - `session.py` - 会话与上下文
  - `parser.py` - 规则解析（Mock 模式）
  - `logger.py` - API 调用日志
- `tests/` - 本地测试
  - `test_cases.json` - 用例（来自需求说明）
  - `test_agent.py` - 测试

## 日志

- 固定文件名：`agent_api_log.jsonl`
- 每次运行前备份为 `agent_api_log_YYYYMMDD_HHMMSS.jsonl`
- 记录：租房 API 调用、LLM 调用（或 rule_based_skip）
