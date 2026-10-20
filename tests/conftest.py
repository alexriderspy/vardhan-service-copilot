"""Make every chapter folder importable in tests."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in ["", "02_migration", "03_classifier", "04_rag", "05_mcp_servers", "06_agent", "08_evals"]:
    sys.path.insert(0, str(ROOT / folder))

os.environ["MCP_TRANSPORT"] = "inprocess"   # tests talk to MCP servers in memory
