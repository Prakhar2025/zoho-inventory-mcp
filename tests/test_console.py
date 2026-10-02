"""Console backend pure helpers: SSE framing and Strands event translation."""

import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from console.backend import map_stream_event, sse_frame


def test_sse_frame_shape():
    assert sse_frame({"type": "token", "text": "hi"}) == 'data: {"type": "token", "text": "hi"}\n\n'


def test_data_chunk_becomes_token_event():
    state = {"seen_tools": set()}
    events = map_stream_event({"data": "Hello"}, state)
    assert events == [{"type": "token", "text": "Hello"}]


def test_tool_start_is_deduplicated_per_id():
    state = {"seen_tools": set()}
    tool_use = {"toolUseId": "t1", "name": "inventory_search_items", "input": {"query": "jaipur"}}
    first = map_stream_event({"current_tool_use": tool_use}, state)
    second = map_stream_event({"current_tool_use": tool_use}, state)

    assert len(first) == 1 and first[0]["type"] == "tool_start" and first[0]["name"].startswith("inventory")
    assert second == []


class FakeResult:
    """Mimics the surface of AgentResult that map_stream_event relies on."""

    def __init__(self, metrics, answer):
        self.metrics = metrics
        self._answer = answer

    def __str__(self) -> str:
        return self._answer


def test_result_event_becomes_done_with_tool_aggregates():
    state = {"seen_tools": set()}
    metrics = SimpleNamespace(
        tool_metrics={
            "orders_list_sales_orders": SimpleNamespace(call_count=2, total_time=1.5, error_count=0),
        },
        accumulated_usage=SimpleNamespace(inputTokens=120, outputTokens=45),
    )
    result = FakeResult(metrics, "final answer")

    events = map_stream_event({"result": result}, state)

    assert len(events) == 1
    done = events[0]
    assert done["type"] == "done"
    assert done["answer"] == "final answer"
    assert done["tools"] == [
        {"name": "orders_list_sales_orders", "calls": 2, "duration_ms": 1500, "errors": 0}
    ]
    assert done["stats"] == {
        "tool_calls": 2,
        "avg_tool_ms": 750,
        "tokens_in": 120,
        "tokens_out": 45,
    }


def test_result_without_metrics_still_emits_done():
    state = {"seen_tools": set()}
    result = FakeResult(None, "ok")

    done = map_stream_event({"result": result}, state)[0]

    assert done["type"] == "done"
    assert done["tools"] == []
    assert done["stats"]["tool_calls"] == 0
    assert done["stats"]["avg_tool_ms"] is None
