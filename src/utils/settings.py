"""
Enhanced configuration settings for the Discord bot with improved personality settings.
"""

import os
import re
from typing import Dict, List, Any, Union

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
BOT_DESCRIPTION = os.getenv("BOT_DESCRIPTION", "A friendly multi-purpose Discord bot")
BOT_VERSION = os.getenv("BOT_VERSION", "0.4.0")

# Get GUILD_ID (enforce single guild setup)
GUILD_ID = int(os.getenv("GUILD_ID", "0") or "0")

# Extensions (Cogs) configuration
# List of enabled extensions
EXTENSIONS_ENABLED = [
    ext.strip()
    for ext in os.getenv(
        "EXTENSIONS_ENABLED", "nickname,admin,utility,moderation,fun,welcome,chatbot"
    ).split(",")
]

# Groq LLM settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
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

# Database settings
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

# Enhanced Chatbot settings
CHATBOT_ENABLED = os.getenv("CHATBOT_ENABLED", "true").lower() == "true"
CHATBOT_CHANNELS = []
# Parse channel IDs, handling both comma-separated IDs and potential whitespace
channels_str = os.getenv("CHATBOT_CHANNELS", "")
if channels_str:
    # Split by commas and clean up each ID
    for channel_id in channels_str.split(","):
        channel_id = channel_id.strip()
        if channel_id.isdigit():
            CHATBOT_CHANNELS.append(int(channel_id))

CHATBOT_MAX_HISTORY = int(os.getenv("CHATBOT_MAX_HISTORY", "15"))
CHATBOT_TEMPERATURE = float(os.getenv("CHATBOT_TEMPERATURE", "0.7"))
CHATBOT_MAX_TOKENS = int(
    os.getenv("CHATBOT_MAX_TOKENS", "300")
)  # Slightly longer for more personality
CHATBOT_NAME = os.getenv("CHATBOT_NAME", "Assistant")
CHATBOT_PERSONALITY = os.getenv("CHATBOT_PERSONALITY", "friendly, helpful and witty")

# Define conversation styles available to the bot
CONVERSATION_STYLES = {
    "friendly": {
        "friendliness": 0.9,
        "humor": 0.7,
        "helpfulness": 0.8,
        "chattiness": 0.7,
        "formality": 0.3,
    },
    "professional": {
        "friendliness": 0.6,
        "humor": 0.3,
        "helpfulness": 0.9,
        "chattiness": 0.4,
        "formality": 0.8,
    },
    "funny": {
        "friendliness": 0.8,
        "humor": 0.9,
        "helpfulness": 0.6,
        "chattiness": 0.8,
        "formality": 0.2,
    },
    "helpful": {
        "friendliness": 0.7,
        "humor": 0.4,
        "helpfulness": 0.9,
        "chattiness": 0.5,
        "formality": 0.6,
    },
}

# Default conversation style
DEFAULT_STYLE = "friendly"

# Custom emojis (for future use)
CUSTOM_EMOJIS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "smile": "😊",
    "laugh": "😄",
    "think": "🤔",
    "cool": "😎",
}

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
    # Chatbot system prompts for different personalities
    "chatbot": {
        "system_message": f"""You are {CHATBOT_NAME}, a {CHATBOT_PERSONALITY} Discord bot assistant.
Your primary goal is to engage naturally in conversations as if you're another member of the server.

Guidelines for your responses:
1. Be decisive and direct - provide information and opinions confidently
2. Keep the conversation flowing naturally by asking occasional questions
3. Use conversational, friendly language rather than formal or academic tone
4. Maintain a helpful but casual demeanor - you're a friend, not a formal assistant 
5. Keep responses concise (1-3 sentences) but engaging
6. Show personality and humor when appropriate
7. Keep the conversation in English, unless the user specifies otherwise.

DISCORD FORMATTING GUIDELINES:
- To mention a user: <@userid> (e.g., <@123456789012345678>)
- To mention a channel: <#channelid> (e.g., <#123456789012345678>)
- For timestamps: <t:unix_timestamp:R> for relative time 
- Use **bold** for emphasis
- Use *italics* for subtle emphasis
- Use `code` for technical terms

When appropriate, use these Discord-specific formatting elements naturally in your responses.

DO NOT:
- Use formal customer service language like "How may I assist you today?"
- Announce yourself as an AI assistant 
- Apologize or state limitations
- Give long, essay-style responses
- Try to steer conversations in specific directions
- Send identical templated responses to similar questions

You should feel like a fun, engaging friend in the conversation, not a utility or service.""",
        "user_message": "{{message_content}}",
        "context_format": "[{{timestamp}}] {{username}}: {{message}}\n",
    },
}


# Function to get appropriate prompt based on personality
def get_personality_prompt(personality_type: str = DEFAULT_STYLE) -> str:
    """
    Get the appropriate system prompt based on personality type.

    Args:
        personality_type: The type of personality to use

    Returns:
        System prompt string
    """
    base_prompt = PROMPTS["chatbot"]["system_message"]

    if personality_type == "professional":
        return base_prompt.replace(
            CHATBOT_PERSONALITY, "professional, knowledgeable, and respectful"
        ).replace(
            "Guidelines for your responses:",
            "Guidelines for your responses:\n1. Use a more formal tone and professional language\n2. Focus on providing accurate and helpful information\n3. Minimize casual expressions and jokes\n4. Be polite and respectful in all interactions",
        )

    elif personality_type == "funny":
        return base_prompt.replace(
            CHATBOT_PERSONALITY, "funny, entertaining, and witty"
        ).replace(
            "Guidelines for your responses:",
            "Guidelines for your responses:\n1. Use humor frequently - puns, jokes, and playful language\n2. Be lighthearted and fun in your interactions\n3. Don't take things too seriously\n4. Feel free to use casual expressions and internet slang",
        )

    elif personality_type == "helpful":
        return base_prompt.replace(
            CHATBOT_PERSONALITY, "helpful, informative, and supportive"
        ).replace(
            "Guidelines for your responses:",
            "Guidelines for your responses:\n1. Focus on providing practical and useful information\n2. Be thorough but concise in your explanations\n3. Anticipate follow-up questions and address them\n4. Show empathy and understanding when users have problems",
        )

    # Default to friendly
    return base_prompt
