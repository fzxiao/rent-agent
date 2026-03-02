# 租房 AI Agent

「智找安居·马年省心办」租房 AI Agent 挑战赛实现。

## 功能

- 本地 Web 服务监听 `http://localhost:8191`
- 接收判题器 `POST /api/v1/chat`，解析 `model_ip`、`session_id`、`message`
- 基于 session 的上下文管理，支持多轮对话
- 调用 LLM（model_ip:8888）理解需求并输出结构化动作
- 调用租房仿真 API 完成查房、租房等操作
- 按规范返回 `response`（普通对话为自然语言；房源查询为 JSON 字符串）

## 安装与运行

### 使用 uv（推荐）

```bash
uv venv
uv pip install -e .
uv run python -m src
```

### 使用 pip

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
python -m src
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| X_USER_ID | 工号，租房 API 必填 | f0092481 |
| HOUSING_API_BASE | 租房 API 地址 | http://7.225.29.223:8080 |
| AGENT_PORT | Agent 监听端口 | 8191 |

## 接口

- `POST /api/v1/chat` - 判题器调用入口
- `GET /health` - 健康检查

## 项目结构

```
src/
  main.py       # FastAPI 入口
  agent.py      # Agent 核心逻辑
  llm_client.py # LLM 调用
  housing_api.py# 租房 API 工具层
  session.py    # 会话上下文
  config.py     # 配置
```
