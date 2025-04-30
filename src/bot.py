"""
Discord bot with modular command structure and extensible features.
"""

import discord
from discord.ext import commands
from typing import List, Dict, Any

from utils.logging_manager import LoggingManager
from utils.settings import BOT_TOKEN, BOT_PREFIX, EXTENSIONS_ENABLED

# Set up logging
logger = LoggingManager.setup_logger(
    name="discord_bot",
    console_output=True,
    file_output=True,
    filename="logs/bot.log",
    file_mode="w",
)

# Configure bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Required for prefixed commands


# Create bot instance with custom help command
class CustomBot(commands.Bot):
    """Extended Bot class with additional functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_version = "0.2.0"
        self.startup_extensions: List[str] = EXTENSIONS_ENABLED
        self.settings = {}  # Bot-wide settings store

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        await self._load_extensions()
        logger.info(f"Bot setup complete. Version {self.app_version}")

    async def _load_extensions(self) -> None:
        """Load all enabled cog extensions."""
        for extension in self.startup_extensions:
            try:
                await self.load_extension(f"cogs.{extension}")
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Global error handler for commands."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
            )
            return

        # Log unexpected errors
        logger.error(f"Command '{ctx.command}' raised an error: {error}")
        await ctx.send(f"An error occurred while executing the command: {error}")


# Create bot instance
bot = CustomBot(command_prefix=commands.when_mentioned_or(BOT_PREFIX), intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f"Bot is ready: {bot.user}")
    logger.info(f"Using command prefix: {BOT_PREFIX}")
    logger.info(f"Connected to {len(bot.guilds)} guilds")

    # Set up custom status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, name=f"{BOT_PREFIX}help"
        )
    )


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Handle when the bot joins a new guild."""
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

    # Try to send welcome message to system channel or first available text channel
    welcome_channel = guild.system_channel
    if not welcome_channel:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break

    if welcome_channel:
        await welcome_channel.send(
            f"Hello! I'm a multi-purpose Discord bot. Use `{BOT_PREFIX}help` to see my commands."
        )
