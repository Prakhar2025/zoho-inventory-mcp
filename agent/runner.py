"""Shared wiring for agent-side tooling (demo, evals).

Both entry points run the connector's MCP server as a subprocess and drive a
Bedrock-backed Strands agent with its six read-only tools. Keeping this in one
module means the demo and the eval suite exercise identical configuration.

Note: scripts import this with the repo root on sys.path (namespace package).
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

REPO_ROOT = Path(__file__).resolve().parent.parent

# Amazon Nova 2 Lite: first-party Bedrock model, no marketplace subscription
# required (Anthropic models need a payment instrument this account lacks).
# Override with BEDROCK_MODEL_ID in .env.
DEFAULT_MODEL_ID = "global.amazon.nova-2-lite-v1:0"

AGENT_SYSTEM_PROMPT = (
    "You are the commerce assistant for LoomKart, a direct-to-consumer home goods "
    "brand. You answer merchant questions using the Zoho Inventory tools available "
    "to you. Never invent data: look it up with the tools and cite order numbers and "
    "item names in your answers. Keep answers short and factual."
)


def start_mcp_client() -> MCPClient:
    """Start the connector's MCP server as a subprocess and connect to it."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "zoho_inventory_mcp"])
    client = MCPClient(lambda: stdio_client(params))
    client.start()
    return client


def make_agent(tools: list) -> Agent:
    """Create a fresh agent (empty message history) over the shared tools."""
    from zoho_inventory_mcp.config import get_settings

    override = getattr(get_settings(), "bedrock_model_id", "")
    model_id = override or DEFAULT_MODEL_ID
    return Agent(
        model=BedrockModel(model_id=model_id, region_name="us-east-1"),
        tools=tools,
        system_prompt=AGENT_SYSTEM_PROMPT,
    )


def used_tool_names(result) -> set[str]:
    """Extract the names of every tool the agent actually called."""
    metrics = getattr(result, "metrics", None)
    tool_metrics = getattr(metrics, "tool_metrics", None) or {}
    return set(tool_metrics)
