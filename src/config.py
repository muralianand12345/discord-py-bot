import os


class BOT:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
    GUILD_ID = os.getenv("GUILD_ID")

    class LOG:
        LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/bot.log")
        LOG_TO_FILE = os.getenv("LOG_TO_FILE", "True").lower() == "true"
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    class DB:
        DB_PATH = "data/bot.db"

    class WELCOME:
        WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")
        ROLE_ID = os.getenv("WELCOME_ROLE_ID")

    class GOODBYE:
        GOODBYE_CHANNEL_ID = os.getenv("GOODBYE_CHANNEL_ID")


class LLM:
    class WELCOME:
        API_KEY = os.getenv("LLM_API_KEY_1")
        API_URL = os.getenv("LLM_API_URL_1", "https://api.groq.com/openai/v1")
        MODEL = os.getenv("LLM_MODEL_1", "llama-3.3-70b-versatile")

    class GOODBYE:
        API_KEY = os.getenv("LLM_API_KEY_2")
        API_URL = os.getenv("LLM_API_URL_2", "https://api.groq.com/openai/v1")
        MODEL = os.getenv("LLM_MODEL_2", "llama-3.3-70b-versatile")

    class TRANSLATOR:
        API_KEY = os.getenv("LLM_API_KEY_3")
        API_URL = os.getenv("LLM_API_URL_3", "https://api.groq.com/openai/v1")
        MODEL = os.getenv("LLM_MODEL_3", "llama-3.3-70b-versatile")

    class CHATBOT:
        API_KEY = os.getenv("LLM_API_KEY_4")
        API_URL = os.getenv("LLM_API_URL_4")
        MODEL = os.getenv("LLM_MODEL_4")

        class BOT_CONFIG:
            BOT_NAME = "Leo"
            CHATBOT_MAX_HISTORY = 10
