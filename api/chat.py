"""POST /api/v1/chat 路由。"""
import time
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.handler import handle_chat
from logging_conf import get_logger, setup_logging

router = APIRouter()


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


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    request_id = str(uuid.uuid4())[:8]
    log = get_logger("chat").bind(session_id=req.session_id, request_id=request_id)
    log.info("judge_request", model_ip=req.model_ip, message_preview=(req.message[:80] + "..." if len(req.message) > 80 else req.message))
    start = time.time()
    try:
        response, tool_results = await handle_chat(req.model_ip, req.session_id, req.message)
    except Exception as e:
        log.error("handle_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    duration_ms = int((time.time() - start) * 1000)
    log.info("judge_response", duration_ms=duration_ms, response_preview=(response[:100] + "..." if response and len(response) > 100 else (response or "")))
    return ChatResponse(
        session_id=req.session_id,
        response=response or "",
        status="success",
        tool_results=[{"name": "tool", "success": r["success"], "output": r["output"]} for r in tool_results],
        timestamp=int(start),
        duration_ms=duration_ms,
    )
