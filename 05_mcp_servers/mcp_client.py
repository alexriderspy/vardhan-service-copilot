"""A tiny client the agent uses to call tools on our three MCP servers.

MCP_TRANSPORT=stdio (default): start the server as a subprocess and talk over stdin/stdout,
                               exactly how Claude Desktop or any MCP host would.
MCP_TRANSPORT=inprocess:       connect to the same server object in memory (fast, used by evals/tests).
"""

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
SERVERS = {
    "company-db": "company_db_server",
    "gmail": "gmail_server",
    "calendar": "calendar_server",
}


def _target(server: str):
    module_name = SERVERS[server]
    if os.getenv("MCP_TRANSPORT", "stdio") == "inprocess":
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        return importlib.import_module(module_name).mcp
    return StdioServerParameters(command=sys.executable, args=[str(HERE / f"{module_name}.py")], env=dict(os.environ))


async def _call(server: str, tool: str, args: dict):
    async with Client(_target(server)) as client:
        result = await client.call_tool(tool, args)
    if result.is_error:
        raise RuntimeError(f"{server}.{tool} failed: {result.content[0].text if result.content else 'unknown error'}")
    if result.structured_content is not None:
        content = result.structured_content
        return content.get("result", content) if isinstance(content, dict) and list(content) == ["result"] else content
    if not result.content:
        return None
    texts = [block.text for block in result.content]
    parsed = [json.loads(t) for t in texts]
    return parsed[0] if len(parsed) == 1 else parsed


def call_tool(server: str, tool: str, args: dict | None = None):
    """Call one MCP tool and return its result as plain Python data."""
    return asyncio.run(_call(server, tool, args or {}))


async def _list(server: str) -> list:
    async with Client(_target(server)) as client:
        return (await client.list_tools()).tools


def list_tools(server: str) -> list:
    return asyncio.run(_list(server))
