"""
Configuration settings for the Discord name changer bot.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")

# Groq LLM settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")

# Translation settings
TRANSLATION_CACHE_SIZE = int(os.getenv("TRANSLATION_CACHE_SIZE", "100"))
TRANSLATION_COOLDOWN_SECONDS = float(os.getenv("TRANSLATION_COOLDOWN_SECONDS", "1.0"))
MAX_TRANSLATION_LENGTH = int(os.getenv("MAX_TRANSLATION_LENGTH", "100"))
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "50"))
USE_ROMANIZATION_FALLBACK = (
    os.getenv("USE_ROMANIZATION_FALLBACK", "true").lower() == "true"
)

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/bot.log")
