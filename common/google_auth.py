"""Google OAuth for REAL mode (Gmail + Calendar). Not used in mock mode.

One-time login:  python 05_mcp_servers/google_login.py
It opens a browser, you approve, and the token is saved to artifacts/google_token.json.
"""

from common.config import GOOGLE_CREDENTIALS, GOOGLE_TOKEN

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",     # read, label as read, drafts, send
    "https://www.googleapis.com/auth/calendar",          # free/busy + create events
]


def get_credentials(allow_browser: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN), SCOPES) if GOOGLE_TOKEN.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif allow_browser:
        if not GOOGLE_CREDENTIALS.exists():
            raise FileNotFoundError(f"Put your OAuth client file at {GOOGLE_CREDENTIALS} (see README: real Google mode).")
        creds = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDENTIALS), SCOPES).run_local_server(port=0)
    else:
        raise RuntimeError("Not logged in to Google. Run: python 05_mcp_servers/google_login.py")
    GOOGLE_TOKEN.write_text(creds.to_json())
    return creds


def google_service(name: str, version: str):
    from googleapiclient.discovery import build
    return build(name, version, credentials=get_credentials(), cache_discovery=False)
