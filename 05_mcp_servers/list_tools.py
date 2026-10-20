"""Start each MCP server over stdio and print the tools it offers.

Run:  python 05_mcp_servers/list_tools.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from mcp_client import SERVERS, list_tools  # noqa: E402

if __name__ == "__main__":
    for server in SERVERS:
        print(f"\n{server}")
        for tool in list_tools(server):
            params = ", ".join(tool.input_schema.get("properties", {}))
            print(f"  - {tool.name}({params})\n      {tool.description.splitlines()[0]}")
