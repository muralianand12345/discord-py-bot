"""
Enhanced Discord bot with modular command structure and friendly personality.
"""

import logging
import platform
import asyncio
import random
from typing import List, Dict, Any, Optional

import discord
from discord.ext import commands, tasks

from utils.logging_manager import LoggingManager
from utils.settings import (
    BOT_PREFIX,
    BOT_VERSION,
    BOT_DESCRIPTION,
    EXTENSIONS_ENABLED,
    GUILD_ID,
    CUSTOM_EMOJIS,
)

# Set up logging
logger = LoggingManager.setup_logger(
    name="discord_bot",
    console_output=True,
    file_output=True,
    filename="logs/bot.log",
    file_mode="a",
)

# Configure intents with better defaults for engagement
intents = discord.Intents.all()  # Enable all intents for maximum engagement
intents.typing = False  # Disable typing events to reduce processing overhead


class CustomBot(commands.Bot):
    """Extended Bot class with enhanced functionality and friendly personality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_version = BOT_VERSION
        self.startup_extensions: List[str] = EXTENSIONS_ENABLED
        self.settings = {}  # Bot-wide settings store
        self.uptime_start = None
        self.emoji = CUSTOM_EMOJIS
        self.status_messages = [
            f"with {BOT_PREFIX}help",
            f"in a friendly server",
            f"Use {BOT_PREFIX}help for commands!",
            "with new friends",
            "and having fun!",
            "version " + BOT_VERSION,
        ]
        self.last_error = None

        # Single guild mode
        self.single_guild_id = GUILD_ID
        self.main_guild = None

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        self.uptime_start = discord.utils.utcnow()

        # Load all extensions
        await self._load_extensions()
        logger.info(f"Bot setup complete. Version {self.app_version}")

        # Start background tasks
        self.change_status.start()

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        logger.info(f"Bot is ready: {self.user}")
        logger.info(f"Using command prefix: {BOT_PREFIX}")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Set up main guild if in single guild mode
        if self.single_guild_id:
            self.main_guild = self.get_guild(self.single_guild_id)
            if self.main_guild:
                logger.info(
                    f"Main guild set to: {self.main_guild.name} (ID: {self.main_guild.id})"
                )
                logger.info(f"Member count: {self.main_guild.member_count}")
            else:
                logger.warning(
                    f"Could not find main guild with ID {self.single_guild_id}"
                )

        await self._log_system_info()

    async def _load_extensions(self) -> None:
        """Load all enabled cog extensions."""
        for extension in self.startup_extensions:
            try:
                await self.load_extension(f"cogs.{extension}")
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

    async def _log_system_info(self) -> None:
        """Log detailed system and environment information."""
        system_info = {
            "Python Version": platform.python_version(),
            "Discord.py Version": discord.__version__,
            "OS": f"{platform.system()} {platform.release()} ({platform.version()})",
            "CPU Architecture": platform.machine(),
            "Bot Version": self.app_version,
            "Intents Enabled": ", ".join([k for k, v in self.intents if v]),
        }

        logger.info("System Information:")
        for key, value in system_info.items():
            logger.info(f"  {key}: {value}")

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Enhanced global error handler for commands with user-friendly messages."""
        # Store last error for debugging
        self.last_error = error

        # Don't respond to command not found
        if isinstance(error, commands.CommandNotFound):
            return

        # Common errors with friendly messages
        if isinstance(error, commands.MissingPermissions):
            # Format missing permissions to be more readable
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]
            message = (
                f"You need {', '.join(missing)} permission(s) to use this command."
            )
            await ctx.send(f"{self.emoji['error']} {message}")
            return

        if isinstance(error, commands.BotMissingPermissions):
            # Format missing permissions to be more readable
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]
            message = f"I need {', '.join(missing)} permission(s) to run this command."
            await ctx.send(f"{self.emoji['error']} {message}")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            param_name = error.param.name.replace("_", " ")
            message = f"Oops! You're missing the `{param_name}` argument.\n"
            message += f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            await ctx.send(f"{self.emoji['warning']} {message}")
            return

        if isinstance(error, commands.CommandOnCooldown):
            message = (
                f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
            )
            await ctx.send(f"{self.emoji['warning']} {message}")
            return

        if isinstance(error, commands.UserInputError):
            message = f"I couldn't understand that. Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            await ctx.send(f"{self.emoji['warning']} {message}")
            return

        if isinstance(error, commands.NotOwner):
            await ctx.send(
                f"{self.emoji['error']} This command can only be used by the bot owner."
            )
            return

        if isinstance(error, commands.CheckFailure):
            # Generic check failure - might be permissions or custom checks
            await ctx.send(
                f"{self.emoji['error']} You don't have permission to use this command."
            )
            return

        # For all other errors, log but give a friendly message
        logger.error(f"Command '{ctx.command}' raised an error: {error}")
        await ctx.send(
            f"{self.emoji['error']} Something went wrong with that command. The error has been logged."
        )

    async def on_guild_join(self, guild: discord.Guild):
        """Handle when the bot joins a new guild with a friendly introduction."""
        # In single guild mode, we only care about the main guild
        if self.single_guild_id and guild.id != self.single_guild_id:
            logger.warning(
                f"Bot added to guild {guild.name} (ID: {guild.id}) but running in single guild mode."
            )
            return

        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        # Try to find a suitable channel for introduction
        welcome_channel = None
        channel_preference = [
            guild.system_channel,  # System channel (usually #general)
            guild.public_updates_channel,  # Announcements channel
            discord.utils.get(guild.text_channels, name="general"),  # #general
            discord.utils.get(guild.text_channels, name="lobby"),  # #lobby
            discord.utils.get(guild.text_channels, name="welcome"),  # #welcome
        ]

        # Try each channel in preference order
        for channel in channel_preference:
            if channel and channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break

        # If we still don't have a channel, find the first one we can post in
        if not welcome_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    welcome_channel = channel
                    break

        if welcome_channel:
            # Create a friendly introduction embed
            embed = discord.Embed(
                title=f"Hello, {guild.name}! 👋",
                description=(
                    f"Thanks for inviting me! I'm a friendly multi-purpose bot "
                    f"with utility commands, moderation tools, and fun features."
                ),
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Getting Started",
                value=f"Use `{BOT_PREFIX}help` to see all available commands.",
                inline=False,
            )

            embed.add_field(
                name="Features",
                value=(
                    "• Chatbot with friendly personality\n"
                    "• Moderation & admin commands\n"
                    "• Fun games and activities\n"
                    "• Nickname translation\n"
                    "• Welcome/goodbye messages"
                ),
                inline=False,
            )

            embed.set_thumbnail(url=self.user.display_avatar.url)
            embed.set_footer(text=f"Version {self.app_version}")

            await welcome_channel.send(embed=embed)

    @tasks.loop(minutes=30)
    async def change_status(self):
        """Periodically change the bot's status message for variety."""
        status = random.choice(self.status_messages)
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name=status)
        )

    @change_status.before_loop
    async def before_status_change(self):
        """Wait until the bot is ready before starting status rotation."""
        await self.wait_until_ready()

    def get_uptime(self) -> str:
        """Get a formatted string of the bot's uptime."""
        if not self.uptime_start:
            return "Bot just started"

        delta = discord.utils.utcnow() - self.uptime_start

        # Calculate days, hours, minutes, seconds
        days, remainder = divmod(int(delta.total_seconds()), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format with only the non-zero units
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:  # Always include seconds if no other units
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return ", ".join(parts)


# Create bot instance
bot = CustomBot(
    command_prefix=commands.when_mentioned_or(BOT_PREFIX),
    intents=intents,
    description=BOT_DESCRIPTION,
    activity=discord.Activity(
        type=discord.ActivityType.listening, name=f"{BOT_PREFIX}help"
    ),
    case_insensitive=True,  # Make commands case insensitive
    strip_after_prefix=True,  # Remove whitespace after prefix
    allowed_mentions=discord.AllowedMentions(
        everyone=False,  # Don't allow @everyone or @here
        users=True,  # Allow mentioning users
        roles=False,  # Don't allow mentioning roles
        replied_user=True,  # Allow mentioning replied user
    ),
)
