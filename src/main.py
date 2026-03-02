"""租房 Agent 主入口 - HTTP 服务"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .agent import process_message
from .config import AGENT_PORT


class ChatRequest(BaseModel):
    model_ip: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    tool_results: list
    timestamp: int
    duration_ms: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="租房 Agent", lifespan=lifespan)


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> JSONResponse:
    """接收判题器 POST，处理消息并返回约定格式"""
    start = time.perf_counter()
    try:
        response, tool_results, _ = await process_message(
            session_id=req.session_id,
            message=req.message,
            model_ip=req.model_ip,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        return JSONResponse(
            content={
                "session_id": req.session_id,
                "response": response,
                "status": "success",
                "tool_results": tool_results,
                "timestamp": int(time.time()),
                "duration_ms": duration_ms,
            }
        )
    except Exception as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return JSONResponse(
            status_code=500,
            content={
                "session_id": req.session_id,
                "response": f"抱歉，处理出错：{str(e)}",
                "status": "error",
                "tool_results": [],
                "timestamp": int(time.time()),
                "duration_ms": duration_ms,
            },
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


def main() -> None:
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=AGENT_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
