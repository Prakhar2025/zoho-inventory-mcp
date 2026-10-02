"""Console event protocol: pure functions, no FastAPI, no agent runtime.

These helpers translate Strands stream events into the console's SSE protocol
and are tested hermetically (tests never import the backend, so CI does not
need the agent or console dependency groups to run the suite).
"""

from __future__ import annotations

import json
from typing import Any


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


def build_done_event(result: Any) -> dict[str, Any]:
    """Public alias: build the final event for one question from a result."""
    return _done_event(result)


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

    tokens_in, tokens_out = _usage_pair(metrics)
    return {
        "type": "done",
        "answer": str(result).strip(),
        "tools": tool_rows,
        "stats": {
            "tool_calls": total_calls,
            "avg_tool_ms": round(total_ms / total_calls) if total_calls else None,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
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
