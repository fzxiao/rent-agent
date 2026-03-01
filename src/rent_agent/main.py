"""FastAPI 服务入口：POST /api/v1/chat。"""

import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from rent_agent import agent, logger

app = FastAPI(title="租房 AI Agent")


class ChatRequest(BaseModel):
    model_ip: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    tool_results: list[dict[str, Any]]
    timestamp: int
    duration_ms: int


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    start = time.time()
    tool_results: list[dict[str, Any]] = []
    try:
        response = agent.process(req.message, req.session_id, req.model_ip)
        status = "success"
    except Exception as e:
        response = str(e)
        status = "error"
        tool_results.append({"name": "error", "success": False, "output": str(e)})

    duration_ms = int((time.time() - start) * 1000)
    return ChatResponse(
        session_id=req.session_id,
        response=response,
        status=status,
        tool_results=tool_results,
        timestamp=int(time.time()),
        duration_ms=duration_ms,
    )


def run(host: str = "0.0.0.0", port: int = 8191) -> None:
    import uvicorn
    logger.prepare_log_for_new_run()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
