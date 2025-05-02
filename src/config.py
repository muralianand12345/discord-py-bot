import os


class BOT:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
    GUILD_ID = os.getenv("GUILD_ID")

    class LOG:
        LOG_FILE_PATH = "logs/bot.log"
        LOG_TO_FILE = True
        LOG_LEVEL = "INFO"

    class WELCOME:
        WELCOME_CHANNEL_ID = "1367170633120743465"
        ROLE_ID = "1366827175436746782"

    class GOODBYE:
        GOODBYE_CHANNEL_ID = "1367170655132586054"


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
        API_URL = os.getenv("LLM_API_URL_4", None)  # https://api.perplexity.ai
        MODEL = os.getenv("LLM_MODEL_4", "gpt-4o-search-preview")  # sonar-pro

        # Vision model settings
        VISION_MODEL = os.getenv("LLM_VISION_MODEL", "gpt-4-vision-preview")
        VISION_API_FORMAT = os.getenv("LLM_VISION_API_FORMAT", "openai")

        class BOT_CONFIG:
            BOT_NAME = "Leo"
            CHANNEL_ID = "1367584360198570064"
            CHATBOT_MAX_HISTORY = 10
            CHATBOT_HISTORY_FILE = "data/chatbot_history.json"

            # Image settings
            ALLOW_IMAGES = os.getenv("ALLOW_IMAGES", "true").lower() == "true"
            MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
            MAX_IMAGE_WIDTH = int(os.getenv("MAX_IMAGE_WIDTH", "1024"))
            MAX_IMAGE_HEIGHT = int(os.getenv("MAX_IMAGE_HEIGHT", "1024"))
            ALLOWED_IMAGE_FORMATS = os.getenv(
                "ALLOWED_IMAGE_FORMATS", ".jpg,.jpeg,.png,.webp"
            ).split(",")
