"""Agent 主入口：FastAPI 服务，监听 8191"""
import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from agent.api_logger import rotate_log_on_startup
from agent.config import DEFAULT_USER_ID, RENTAL_API_BASE_URL
from agent.handler import handle_chat

app = FastAPI(title="租房 AI Agent", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    """Agent 启动时备份旧日志，为本次运行创建独立日志文件"""
    log_path = rotate_log_on_startup()
    print(f"[API Log] 本次运行日志: {log_path}")


class ChatRequest(BaseModel):
    model_ip: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    tool_results: list[Any] = []
    timestamp: int
    duration_ms: int


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """接收判题器输入，完成 Agent 处理，返回结果"""
    result = handle_chat(
        model_ip=req.model_ip,
        session_id=req.session_id,
        message=req.message,
        user_id=DEFAULT_USER_ID,
        rental_base_url=RENTAL_API_BASE_URL,
    )
    return ChatResponse(
        session_id=req.session_id,
        response=result["response"],
        status=result["status"],
        tool_results=result.get("tool_results", []),
        timestamp=int(time.time()),
        duration_ms=result["duration_ms"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def run() -> None:
    import uvicorn
    from agent.config import AGENT_PORT
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)


if __name__ == "__main__":
    run()
