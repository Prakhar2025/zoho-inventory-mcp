"""LoomKart ops console: FastAPI backend serving the UI and streaming agent runs.

The console is a demo harness over the same MCP server and Bedrock agent as the
CLI demo, exposed as an SSE endpoint so tool activity can be watched live.
Runs locally only (no auth by design; it reads the same fictional org).

    .venv/Scripts/python -m uvicorn console.backend:app --port 8630
"""

from __future__ import annotations

import asyncio
import json
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

from zoho_inventory_mcp.config import get_settings
from zoho_inventory_mcp.errors import ZohoError

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"


def sse_frame(event: dict[str, Any]) -> str:
    """Format one server-sent event frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def map_stream_event(event: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate one Strands stream event into zero or more console protocol events.

    Tool starts are deduplicated by toolUseId (Strands re-emits the in-flight
    tool block across chunks); final per-tool aggregates come from the result
    metrics, which are the authoritative numbers.
    """
    out: list[dict[str, Any]] = []
    chunk = event.get("data")
    if isinstance(chunk, str) and chunk:
        out.append({"type": "token", "text": chunk})

    tool_use = event.get("current_tool_use") or {}
    tool_id = tool_use.get("toolUseId")
    if tool_use.get("name") and tool_id and tool_id not in state["seen_tools"]:
        state["seen_tools"].add(tool_id)
        out.append(
            {
                "type": "tool_start",
                "id": tool_id,
                "name": tool_use["name"],
                "args": _as_dict(tool_use.get("input")),
            }
        )

    if "result" in event:
        out.append(_done_event(event["result"]))
    return out


def _as_dict(value: Any) -> dict[str, Any]:
    """Normalize tool input, which Strands may deliver as a dict or a JSON string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"input": value}
        except ValueError:
            return {"input": value}
    return {}


def _done_event(result: Any) -> dict[str, Any]:
    """Build the final event for one question from the agent result."""
    metrics = getattr(result, "metrics", None)
    tool_rows: list[dict[str, Any]] = []
    total_calls, total_ms = 0, 0.0
    for name, tm in sorted((getattr(metrics, "tool_metrics", None) or {}).items()):
        calls = int(getattr(tm, "call_count", 0))
        duration_ms = float(getattr(tm, "total_time", 0.0)) * 1000
        tool_rows.append(
            {
                "name": name,
                "calls": calls,
                "duration_ms": round(duration_ms),
                "errors": int(getattr(tm, "error_count", 0)),
            }
        )
        total_calls += calls
        total_ms += duration_ms

    usage = _usage_pair(metrics)
    return {
        "type": "done",
        "answer": str(result).strip(),
        "tools": tool_rows,
        "stats": {
            "tool_calls": total_calls,
            "avg_tool_ms": round(total_ms / total_calls) if total_calls else None,
            "tokens_in": usage[0],
            "tokens_out": usage[1],
        },
    }


def _usage_pair(metrics: Any) -> tuple[int, int]:
    """Best-effort token counts: prefer the last invocation's cycle usage."""
    invocations = getattr(metrics, "agent_invocations", None) or []
    for invocation in reversed(invocations):
        cycles = getattr(invocation, "cycles", None) or []
        for cycle in reversed(cycles):
            usage = getattr(cycle, "usage", None)
            if isinstance(usage, dict) and (usage.get("inputTokens") or usage.get("outputTokens")):
                return int(usage.get("inputTokens") or 0), int(usage.get("outputTokens") or 0)
    usage = getattr(metrics, "accumulated_usage", None)
    return (
        int(getattr(usage, "inputTokens", 0) or 0),
        int(getattr(usage, "outputTokens", 0) or 0),
    )


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
