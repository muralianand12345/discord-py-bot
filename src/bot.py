import asyncio
import discord
import logging
from datetime import datetime
from discord.ext import commands

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


class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=BOT.BOT_PREFIX,
            intents=intents,
            description="A multi-purpose Discord bot with modular features",
        )
        self.settings = {}
        self.status_messages = [
            f"with {BOT.BOT_PREFIX}help",
            f"in a friendly server",
            f"Use {BOT.BOT_PREFIX}help for commands!",
            "with new friends",
            "and having fun!",
        ]
        self.guild_id = int(BOT.GUILD_ID) if BOT.GUILD_ID else None

    async def setup_hook(self):
        """Initialize bot extensions and load event listeners."""
        await self.load_event_handlers()
        await self.load_commands()
        logger.info("Bot setup complete.")

    async def load_event_handlers(self):
        """Load all event handlers from the events directory."""
        try:
            # Import all event handlers
            from events import all_events

            logger.info("Loaded event handlers successfully")
        except Exception as e:
            logger.error(f"Failed to load event handlers: {str(e)}")

    async def load_commands(self):
        """Load all commands from the commands directory."""
        try:
            # Import all commands
            from commands import all_commands

            logger.info("Loaded commands successfully")
        except Exception as e:
            logger.error(f"Failed to load commands: {str(e)}")

    async def on_ready(self):
        """Called when the bot is ready and connected."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        if self.guild_id:
            guild = self.get_guild(self.guild_id)
            if guild:
                logger.info(f"Primary guild: {guild.name} (ID: {guild.id})")
            else:
                logger.warning(f"Could not find primary guild with ID: {self.guild_id}")

        await self.change_presence(activity=discord.Game(name=self.status_messages[0]))

        # Start status rotation task
        self.rotate_status_task = self.loop.create_task(self.rotate_status())

    async def rotate_status(self):
        """Rotate through status messages periodically."""
        status_index = 0

        while not self.is_closed():
            status_index = (status_index + 1) % len(self.status_messages)
            await self.change_presence(
                activity=discord.Game(name=self.status_messages[status_index])
            )
            await asyncio.sleep(300)  # Change status every 5 minutes

    async def close(self):
        """Clean up before closing the bot."""
        logger.info("Bot is shutting down...")

        # Cancel any ongoing tasks
        if hasattr(self, "rotate_status_task"):
            self.rotate_status_task.cancel()

        await super().close()


# Create bot instance
bot = CustomBot()
