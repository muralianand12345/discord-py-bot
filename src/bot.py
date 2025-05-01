import discord
import logging
from datetime import datetime

from config import BOT
from utils.logging_manager import LoggingManager

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"{BOT.LOG.LOG_FILE_PATH.rsplit('.', 1)[0]}_{current_time}.log"

logger = LoggingManager.setup_logger(
    name="discord_bot",
    console_output=True,
    file_output=BOT.LOG.LOG_TO_FILE,
    filename=log_filename,
    file_mode="w",
    level=getattr(logging, "INFO", logging.INFO),
)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class Bot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = {}
        self.status_messages = [
            f"with {BOT.BOT_PREFIX}help",
            f"in a friendly server",
            f"Use {BOT.BOT_PREFIX}help for commands!",
            "with new friends",
            "and having fun!",
        ]
        self.guildId = BOT.GUILD_ID

    