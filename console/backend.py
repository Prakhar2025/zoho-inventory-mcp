"""LoomKart ops console: FastAPI backend serving the UI and streaming agent runs.

The console is a demo harness over the same MCP server and Bedrock agent as the
CLI demo, exposed as an SSE endpoint so tool activity can be watched live.
Runs locally only (no auth by design; it reads the same fictional org).

    .venv/Scripts/python -m uvicorn console.backend:app --port 8630
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.runner import DEFAULT_MODEL_ID, make_agent, start_mcp_client
from console.events import map_stream_event, sse_frame

from zoho_inventory_mcp.config import get_settings
from zoho_inventory_mcp.errors import ZohoError

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"

_tools: list | None = None
_gate = asyncio.Semaphore(1)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Start one shared MCP server subprocess for the lifetime of the backend."""
    global _tools
    client = start_mcp_client()
    _tools = client.list_tools_sync()
    logger.info("console backend ready with %d tools", len(_tools))
    yield
    client.stop(None, None, None)


class ChatRequest(BaseModel):
    message: str


app = FastAPI(title="LoomKart Ops Console", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": DEFAULT_MODEL_ID,
        "dc": settings.zoho_dc,
        "configured": settings.is_configured,
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> StreamingResponse:
    message = payload.message.strip()
    if not message:
        frame = sse_frame(
            {"type": "error", "error_type": "BadRequest", "message": "empty message", "retryable": False}
        )
        return StreamingResponse(iter([frame]), media_type="text/event-stream")

    async def stream() -> AsyncIterator[str]:
        state: dict[str, Any] = {"seen_tools": set()}
        started = time.perf_counter()
        try:
            agent = make_agent(_tools)  # fresh message history per question
            async with _gate:  # serialize runs: one Zoho-paced agent at a time
                async for event in agent.stream_async(message):
                    for out in map_stream_event(event, state):
                        yield sse_frame(out)
            yield sse_frame({"type": "meta", "duration_ms": round((time.perf_counter() - started) * 1000)})
        except ZohoError as exc:
            yield sse_frame(
                {
                    "type": "error",
                    "error_type": type(exc).__name__,
                    "message": exc.message,
                    "retryable": exc.retryable,
                }
            )
        except Exception as exc:
            # The stream must always terminate with a frame the UI can render.
            logger.exception("agent run failed")
            yield sse_frame(
                {"type": "error", "error_type": "ServerError", "message": str(exc)[:200], "retryable": False}
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="console")
