"""Merchant demo: a Strands agent on AWS Bedrock using the connector over MCP.

Asks three scripted merchant questions end to end and writes the answers to
agent/transcript.md. Every tool call lands in logs/audit.jsonl with arguments
and timings. Safe to rerun; read-only and costs pennies.

    .venv/Scripts/python agent/demo.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.runner import make_agent, start_mcp_client

TRANSCRIPT_PATH = REPO_ROOT / "agent" / "transcript.md"

QUESTIONS = [
    "What products do we sell, and what do they cost? One line per product.",
    "Find any orders from Sneha Iyer and tell me exactly what she bought.",
    "Which orders are still in draft status and who placed them?",
]


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    client = start_mcp_client()
    lines = [
        "# Demo transcript: merchant questions against the LoomKart org",
        "",
        "Answers were produced by a Strands agent backed by AWS Bedrock, using only",
        "the six read-only MCP tools exposed by this connector. Every tool call is",
        "recorded with arguments and timings in logs/audit.jsonl.",
        "",
    ]
    try:
        tools = client.list_tools_sync()
        for question in QUESTIONS:
            print(f"\nMerchant: {question}")
            result = make_agent(tools)(question)
            answer = str(result).strip()
            print(f"Agent: {answer}\n")
            lines += ["## Merchant", "", f"> {question}", "", f"**Agent:** {answer}", ""]
    finally:
        client.stop(None, None, None)

    TRANSCRIPT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"transcript written to {TRANSCRIPT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
