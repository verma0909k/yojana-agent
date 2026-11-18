"""Configuration settings, paths, and environment variable loaders for YojanaAgent."""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PACKAGE_DIR = BASE_DIR / "yojanaagent"
SHARED_DIR = PACKAGE_DIR / "shared"
BRAIN_DIR = PACKAGE_DIR / "brain"
KNOWLEDGE_DIR = PACKAGE_DIR / "knowledge"
SCHEMES_DIR = KNOWLEDGE_DIR / "schemes"
EXPERIENCE_DIR = PACKAGE_DIR / "experience"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMES_DIR.mkdir(parents=True, exist_ok=True)

# API Keys & Models
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Agent Constants
MAX_PLANNER_STEPS = int(os.getenv("MAX_PLANNER_STEPS", "8"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")  # 'en' or 'hi'
