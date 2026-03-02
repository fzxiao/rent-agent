"""
租房 Agent 主入口：启动 HTTP 服务，监听 POST /api/v1/chat
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .agent import process_message
from .api_logger import ApiLogger
from .config import AGENT_PORT
from .session_manager import SessionManager


class ChatRequest(BaseModel):
    model_ip: str
    session_id: str
    message: str


session_manager = SessionManager()
api_logger = ApiLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown if needed


app = FastAPI(title="租房 AI Agent", lifespan=lifespan)


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """接收判题器 POST，返回约定格式的响应"""
    try:
        result = await process_message(
            model_ip=request.model_ip,
            session_id=request.session_id,
            message=request.message,
            session_manager=session_manager,
            api_logger=api_logger,
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "session_id": request.session_id,
                "response": f"处理失败：{str(e)}",
                "status": "error",
                "tool_results": [],
                "timestamp": 0,
                "duration_ms": 0,
            },
        )


def run():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)


if __name__ == "__main__":
    run()
