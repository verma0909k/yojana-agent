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
EXPERIENCE_DIR = BASE_DIR / "experience"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMES_DIR.mkdir(parents=True, exist_ok=True)

# API Keys & Models
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")

# Agent Constants
MAX_PLANNER_STEPS = int(os.getenv("MAX_PLANNER_STEPS", "8"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")  # 'en' or 'hi'
