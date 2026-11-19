"""Configuration settings, paths, and environment variable loaders for YojanaAgent."""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = BASE_DIR / "shared"
BRAIN_DIR = BASE_DIR / "brain"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DATA_DIR = KNOWLEDGE_DIR
SCHEMES_DIR = KNOWLEDGE_DIR / "schemes"
CHROMA_DIR = DATA_DIR / "chroma_db"
EXPERIENCE_DIR = BASE_DIR / "experience"
OUTPUT_DIR = BASE_DIR / "output"
VAULT_DIR = DATA_DIR / "vault"
LLM_CACHE_DB = DATA_DIR / "llm_cache.db"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMES_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
VAULT_DIR.mkdir(parents=True, exist_ok=True)

# API Keys & Models
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "default")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "government_schemes")

# Privacy, Vault & Execution Mode
VAULT_KEY = os.getenv("VAULT_KEY", "")
DECISION_MODE = os.getenv("DECISION_MODE", "llm").lower()  # "llm" or "rules"
NOTIFY_DRY_RUN = os.getenv("NOTIFY_DRY_RUN", "true").lower() in ("true", "1", "yes")

# Notification / Dispatch (SMTP & Telegram)
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "alerts@yojanaagent.gov.in")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
HOURLY_RATE_LIMIT = int(os.getenv("HOURLY_RATE_LIMIT", "10"))

# Agent Constants
MAX_PLANNER_STEPS = int(os.getenv("MAX_PLANNER_STEPS", "8"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")  # 'en' or 'hi'
