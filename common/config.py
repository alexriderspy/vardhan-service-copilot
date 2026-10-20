"""All paths and settings in one place, read from .env."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Everything generated, downloaded or trained goes here (git-ignored).
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

# Keep downloaded models inside the project, and switch off Chroma telemetry.
os.environ.setdefault("HF_HOME", str(ARTIFACTS / "hf_cache"))
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

# Chapter 1 output: the client's messy legacy system
LEGACY_DIR = ARTIFACTS / "legacy"
LEGACY_DB = LEGACY_DIR / "legacy.db"
LEGACY_EXPORTS = LEGACY_DIR / "exports"
CLIENT_DOCS = ROOT / "01_legacy_data" / "client_docs"  # manuals + warranty policy

# Chapter 2 output: the clean database (SQLite fallback if no Postgres)
SQLITE_DB = ARTIFACTS / "vardhan.db"
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{SQLITE_DB}"
AGENT_DATABASE_URL = os.getenv("AGENT_DATABASE_URL") or DATABASE_URL
AGENT_DB_PASSWORD = os.getenv("AGENT_DB_PASSWORD", "change-me")

# Chapter 3: classifier
INTENTS = ["order_status", "service_booking", "warranty_claim", "technical_question", "complaint", "other"]
CLASSIFIER_DATA = ARTIFACTS / "classifier_data"
CLASSIFIER_MODEL = ARTIFACTS / "intent_model"
BASE_ENCODER = "distilbert-base-uncased"

# Chapter 4: RAG
CHROMA_DIR = ARTIFACTS / "chroma"
EMBEDDINGS = os.getenv("EMBEDDINGS", "local")
LOCAL_EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# Chapter 5: Gmail + Calendar
GOOGLE_MODE = os.getenv("GOOGLE_MODE", "mock")  # "mock" or "real"
MOCK_GMAIL = ARTIFACTS / "mock_gmail.json"
MOCK_CALENDAR = ARTIFACTS / "mock_calendar.json"
GOOGLE_CREDENTIALS = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", ROOT / "credentials.json"))
GOOGLE_TOKEN = ARTIFACTS / "google_token.json"
SUPPORT_EMAIL = "support@vardhanpumps.example"

# Chapter 6: agent
CHECKPOINT_DB = ARTIFACTS / "agent_checkpoints.db"

# LLM (see common/llm.py)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")


def use_chapter(folder: str) -> None:
    """Make a chapter folder importable.

    Python can't `import 03_classifier` (names can't start with a digit),
    so we add the folder to sys.path and import its modules by file name.
    """
    path = str(ROOT / folder)
    if path not in sys.path:
        sys.path.insert(0, path)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
