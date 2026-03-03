"""Agent 入口：FastAPI 服务，监听 8190。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config import settings
from api.chat import router as chat_router
from logging_conf import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(title="租房 AI Agent", lifespan=lifespan)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.agent_port,
        reload=False,
    )
