#!/bin/bash
# 本地完整测试：启动 Mock API、Mock LLM、Agent，然后运行测试
set -e
cd "$(dirname "$0")"

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo "请先安装 uv: https://github.com/astral-sh/uv"
    exit 1
fi

# 创建虚拟环境并安装依赖
uv sync

# 清理可能占用端口的旧进程
for port in 8081 8888 8191; do
  pid=$(lsof -ti:$port 2>/dev/null) && kill -9 $pid 2>/dev/null || true
done
sleep 2

# 设置环境变量（避免代理干扰本地请求）
export RENTAL_API_BASE_URL=http://127.0.0.1:8081
export X_USER_ID=test_user_001
export no_proxy=127.0.0.1,localhost,::1
export NO_PROXY=127.0.0.1,localhost,::1

# 启动 Mock 服务（后台）
echo "启动 Mock 租房 API (8081)..."
uv run python -m uvicorn mock_rental_api:app --host 0.0.0.0 --port 8081 &
MOCK_PID=$!

echo "启动 Mock LLM (8888)..."
uv run python -m uvicorn mock_llm:app --host 0.0.0.0 --port 8888 &
LLM_PID=$!

sleep 3

echo "启动 Agent (8191)..."
uv run python -m uvicorn agent.main:app --host 0.0.0.0 --port 8191 &
AGENT_PID=$!

# 等待服务就绪
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s http://127.0.0.1:8191/health >/dev/null 2>&1; then
    echo "Agent 已就绪"
    break
  fi
  sleep 1
done

# 运行测试
echo ""
echo "运行测试..."
uv run python tests/run_tests.py 127.0.0.1
RESULT=$?

# 清理
kill $AGENT_PID $LLM_PID $MOCK_PID 2>/dev/null || true
exit $RESULT
