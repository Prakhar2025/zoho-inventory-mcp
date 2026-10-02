"""Append-only JSONL audit log for tool calls.

Records what the agent asked the connector to do, with which parameters, how
long it took, and the outcome. Tokens and secrets never enter the log; params
are whitelisted by the caller before reaching this class.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """Writes one JSON object per tool call, one line each."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def record(
        self,
        *,
        tool: str,
        params: dict[str, Any],
        status: str,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "tool": tool,
            "params": params,
            "status": status,
            "duration_ms": round(duration_ms, 1),
        }
        if error:
            entry["error"] = error[:300]
        line = json.dumps(entry, ensure_ascii=False)
        async with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                # Tiny synchronous append; blocking the loop for microseconds
                # is cheaper than fanning out to a thread for each line.
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                logger.warning("audit log write failed for %s", self._path, exc_info=True)
