"""One-time Google login for REAL mode. Opens a browser for consent.

Run:  python 05_mcp_servers/google_login.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.google_auth import get_credentials  # noqa: E402

if __name__ == "__main__":
    get_credentials(allow_browser=True)
    print("Logged in. Token saved. Set GOOGLE_MODE=real in .env to use your real Gmail + Calendar.")
