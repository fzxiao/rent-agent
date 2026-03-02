# 租房 AI Agent

「智找安居·马年省心办」租房 AI Agent 挑战赛实现。

## 功能

- 本地 Web 服务 `http://localhost:8191`
- POST `/api/v1/chat` 接收 `model_ip`、`session_id`、`message`
- 多轮会话上下文管理
- 新 session 自动调用 `POST /api/houses/init` 重置
- 调用 LLM 理解需求并生成结构化 API 调用
- 调用租房仿真 API 查询房源、租房/退租/下架
- 返回约定格式：普通对话为自然语言；房源查询为 JSON 字符串 `{"message":"...","houses":[...]}`

## 环境

- Python 3.10+
- 需可访问：LLM（model_ip:8888）、租房 API（7.225.29.223:8080）

## 配置

| 环境变量 | 说明 | 默认 |
|---------|------|------|
| X_USER_ID | 工号，用于 X-User-ID | f00954281 |
| RENT_API_BASE_URL | 租房 API 地址 | http://7.225.29.223:8080 |
| AGENT_PORT | Agent 监听端口 | 8191 |

## 安装与运行

```bash
# 使用 uv（推荐）
uv venv
uv pip install -e .
uv run rent-agent

# 或使用 pip
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .
rent-agent
```

或直接启动：

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8191
```

## 测试

```bash
pytest tests/ -v
```

## 请求示例

```bash
curl -X POST http://localhost:8191/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model_ip":"127.0.0.1","session_id":"test1","message":"海淀区两居有吗？"}'
```

## 日志

API 调用日志写入 `agent_api_log.jsonl`，每次运行前会备份旧日志。
