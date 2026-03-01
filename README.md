# 租房 AI Agent

智能租房 AI Agent，支持需求理解、房源查询、多轮对话与租房决策。

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 安装

```bash
uv sync
# 或
pip install -e .
```

### 启动 Agent（对接真实环境）

```bash
# 设置租房 API 地址与用户工号
export RENTAL_API_BASE_URL=http://比赛平台API地址:8080
export X_USER_ID=你的工号

uv run python -m uvicorn agent.main:app --host 0.0.0.0 --port 8191
```

### 本地测试（无需真实 API 与 LLM）

1. 启动 Mock 租房 API（端口 8081）：

```bash
uv run python mock_rental_api.py
```

2. 启动 Mock LLM（端口 8888）：

```bash
uv run python mock_llm.py
```

3. 启动 Agent（端口 8191）：

```bash
export RENTAL_API_BASE_URL=http://localhost:8081
uv run python -m uvicorn agent.main:app --host 0.0.0.0 --port 8191
```

4. 运行测试：

```bash
uv run python tests/run_tests.py 127.0.0.1
```

或使用一键脚本：

```bash
chmod +x run_local_test.sh
./run_local_test.sh
```

## 项目结构

```
├── agent/                 # Agent 核心
│   ├── main.py            # FastAPI 入口
│   ├── handler.py         # 聊天处理逻辑
│   ├── llm_client.py      # LLM 调用
│   ├── rental_client.py   # 租房 API 客户端
│   ├── session.py         # 会话管理
│   ├── tools.py           # 工具定义
│   └── config.py          # 配置
├── mock_rental_api.py     # Mock 租房 API
├── mock_llm.py            # Mock LLM（本地测试）
├── tests/
│   ├── test_cases.json    # 测试用例
│   ├── run_tests.py      # 测试运行器
│   └── fixtures/         # Mock 响应数据
├── 需求说明.md
└── 租房API接口.json
```

## API 接口

- `POST /api/v1/chat`：接收判题器输入，返回 Agent 回复
- `GET /health`：健康检查

## API 调用日志

Agent 每次启动时会：若存在上次的 `agent_api_calls.log`，则改名备份为 `agent_api_calls_backup_YYYYMMDD_HHMMSS.log`。本次运行始终写入 `agent_api_calls.log`（固定文件名）。

日志为 JSON 行格式，便于分析问题：
- `request_start`：请求开始（session_id、用户消息摘要）
- `llm`：LLM 调用（URL、消息数、是否带 tools、响应摘要）
- `rental`：租房 API 调用（方法、路径、参数、状态码、耗时）
- `tool`：工具执行（工具名、参数、结果摘要、耗时）
- `request_end`：请求结束（状态、总耗时）

可通过环境变量 `AGENT_LOG_DIR` 指定日志目录。

## 测试用例

| 用例 ID | 类型 | 描述 |
|---------|------|------|
| TC-001 | Single | 东城区精装两居 5000 以内 500m 地铁 → 无匹配 |
| TC-002 | Multi | 西城近地铁一居，按地铁距离排序，多轮追问 |
| TC-003 | Multi | 海淀近地铁两居排序 + 租房决策 |
