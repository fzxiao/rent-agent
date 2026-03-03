# 租房 AI Agent

智找安居·马年省心办 —— 租房 AI Agent 开发挑战赛参赛实现。

## 环境

- Python 3.10+
- 依赖见 `requirements.txt` 或 `pyproject.toml`

## 安装与运行

```bash
# 使用 uv（推荐）
uv venv
uv pip sync  # 或 uv pip install -e .
uv run uvicorn main:app --host 0.0.0.0 --port 8190

# 或使用 pip
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8190
```

服务监听 `http://localhost:8190`，判题器请求 `POST /api/v1/chat`。

## 配置

通过环境变量或 `.env` 覆盖（参考 `.env.example`）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| RENT_USER_ID | 比赛平台用户工号（X-User-ID） | f00952481 |
| RENT_API_BASE | 租房仿真 API 地址 | http://7.225.29.223:8080 |
| AGENT_PORT | Agent 监听端口 | 8190 |
| LOG_LEVEL | 日志级别 | INFO |
| ENABLE_TRACE_EXPORT | 是否导出 trace 文件 | true |
| ENABLE_RETRY | 是否启用 API 重试 | true |

## 本地测试

1. 启动 Agent（见上文）。
2. 执行测试脚本（需本地或评测环境有可用的 LLM，且 `model_ip` 正确）：

```bash
python scripts/run_tests.py
# 或指定用例文件与 Agent 地址
python scripts/run_tests.py tests/fixtures/sample_cases.json --base http://localhost:8190 --model-ip <LLM_IP>
```

脚本会按用例中的 `session_id`、`user_input` 发送请求，并校验 `message_contains` 与 `expectedHouses`。

## 日志与 Trace

- **日志**：`logs/agent_YYYY-MM-DD.log`（JSON 行），每条含 `session_id`、`request_id` 等，便于按会话检索。同时输出到控制台。
- **Trace**：每个请求结束后，将完整会话与回复写入 `logs/traces/{session_id}_{timestamp}.json`，用于复现失败用例。可通过 `ENABLE_TRACE_EXPORT=false` 关闭。

## 接口说明

- **POST /api/v1/chat**  
  请求体：`{ "model_ip": "", "session_id": "", "message": "" }`  
  响应：`{ "session_id", "response", "status", "tool_results", "timestamp", "duration_ms" }`  
  - 普通对话：`response` 为自然语言文本。  
  - 房源查询完成：`response` 为 JSON 字符串，含 `message` 和 `houses`（最多 5 个房源 ID）。

- **GET /health**  
  健康检查。
