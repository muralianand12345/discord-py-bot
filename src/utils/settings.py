"""
Configuration settings for the Discord bot.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
BOT_DESCRIPTION = os.getenv("BOT_DESCRIPTION", "A multi-purpose Discord bot")

# Extensions (Cogs) configuration
# List of enabled extensions
EXTENSIONS_ENABLED = [
    ext.strip()
    for ext in os.getenv(
        "EXTENSIONS_ENABLED", "nickname,admin,utility,moderation,fun,welcome"
    ).split(",")
]

# Groq LLM settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "10.0"))
LLM_COOLDOWN_SECONDS = float(os.getenv("LLM_COOLDOWN_SECONDS", "1.0"))

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

# Database settings (for future use)
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")

# Command cooldowns (in seconds)
COOLDOWNS = {
    "default": int(os.getenv("COOLDOWN_DEFAULT", "3")),
    "translation": int(os.getenv("COOLDOWN_TRANSLATION", "5")),
    "batch_operations": int(os.getenv("COOLDOWN_BATCH_OPERATIONS", "30")),
}

# Feature flags
FEATURES = {
    "auto_translation": os.getenv("FEATURE_AUTO_TRANSLATION", "true").lower() == "true",
    "moderation": os.getenv("FEATURE_MODERATION", "true").lower() == "true",
    "fun_commands": os.getenv("FEATURE_FUN_COMMANDS", "true").lower() == "true",
}

# Welcome/Goodbye Settings
# Use 0 as default for IDs so the bot doesn't crash if they're not set
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0") or "0")
GOODBYE_CHANNEL_ID = int(os.getenv("GOODBYE_CHANNEL_ID", "0") or "0")
DEFAULT_ROLE_ID = int(os.getenv("DEFAULT_ROLE_ID", "0") or "0")
WELCOME_EMBED_COLOR = int(os.getenv("WELCOME_EMBED_COLOR", "0x5CDBF0"), 0)
GOODBYE_EMBED_COLOR = int(os.getenv("GOODBYE_EMBED_COLOR", "0xED4245"), 0)

# LLM Prompts
PROMPTS = {
    # Translation prompts
    "translation": {
        "system_message": "You are a translator that specializes in converting names to {language}. "
        "Respond with ONLY the translated name.",
        "user_message": "Translate this name to {language}: {text}",
    },
    # Welcome/Goodbye message prompts
    "welcome": {
        "system_message": "You are a friendly Discord bot that creates personalized welcome messages. "
        "Your messages should be warm, friendly, and around 2-3 sentences long. "
        "Do not use emojis or formatting in your response.",
        "user_message": "Create a warm welcome message for a new Discord member named {username} "
        "who just joined a server called {server_name}. Make it personal and inviting.",
    },
    "goodbye": {
        "system_message": "You are a friendly Discord bot that creates personalized goodbye messages. "
        "Your messages should be respectful, a bit sad but positive, and around 2-3 sentences long. "
        "Do not use emojis or formatting in your response.",
        "user_message": "Create a goodbye message for a Discord member named {username} "
        "who just left a server called {server_name}.",
    },
}
