"""
Moderation commands for Discord bot.
"""

import re
import discord
import logging
import asyncio
import datetime
from typing import Optional
from discord.ext import commands

from utils.settings import COOLDOWNS


class ModerationCog(commands.Cog, name="Moderation"):
    """Commands for server moderation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("moderation_cog")

        # Initialize moderation settings dict
        self.mod_settings = {}

    def _get_guild_settings(self, guild_id: int) -> dict:
        """Get moderation settings for a guild, or create defaults."""
        if guild_id not in self.mod_settings:
            self.mod_settings[guild_id] = {
                "word_filter": {
                    "enabled": False,
                    "words": [],
                    "action": "delete",  # delete, warn, mute
                },
                "invite_filter": {"enabled": False, "action": "delete"},
                "caps_filter": {
                    "enabled": False,
                    "threshold": 70,  # percentage
                    "min_length": 10,  # minimum message length to check
                    "action": "delete",
                },
            }
        return self.mod_settings[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check messages for moderation filters."""
        # Skip bot messages
        if message.author.bot:
            return

        # Skip DMs
        if not message.guild:
            return

        # Skip messages from users with manage_messages permission
        if message.author.guild_permissions.manage_messages:
            return

        # Get guild settings
        settings = self._get_guild_settings(message.guild.id)

        # Word filter
        if settings["word_filter"]["enabled"]:
            if any(
                word.lower() in message.content.lower()
                for word in settings["word_filter"]["words"]
            ):
                await self._handle_filtered_message(message, "word_filter", settings)
                return

        # Invite filter
        if settings["invite_filter"]["enabled"]:
            invite_pattern = (
                r"discord(?:\.gg|app\.com\/invite|\.com\/invite)\/[a-zA-Z0-9]+"
            )
            if re.search(invite_pattern, message.content):
                await self._handle_filtered_message(message, "invite_filter", settings)
                return

        # Caps filter
        if settings["caps_filter"]["enabled"]:
            if len(message.content) >= settings["caps_filter"]["min_length"]:
                caps_count = sum(1 for c in message.content if c.isupper())
                if caps_count > 0:
                    caps_percentage = (caps_count / len(message.content)) * 100
                    if caps_percentage >= settings["caps_filter"]["threshold"]:
                        await self._handle_filtered_message(
                            message, "caps_filter", settings
                        )
                        return

    async def _handle_filtered_message(
        self, message: discord.Message, filter_type: str, settings: dict
    ):
        """Handle a message that triggered a filter."""
        action = settings[filter_type]["action"]

        # Log the event
        self.logger.info(
            f"Filtered message in {message.guild.name} (#{message.channel.name}) by {message.author}: "
            f"Triggered {filter_type}, action: {action}"
        )

        # Perform the action
        if action == "delete":
            try:
                await message.delete()

                # Send a temporary notification
                notification = await message.channel.send(
                    f"{message.author.mention}, your message was removed because it violated the server's filter settings."
                )
                await asyncio.sleep(5)
                await notification.delete()

            except discord.Forbidden:
                self.logger.warning(
                    f"No permission to delete message in {message.guild.name}"
                )
            except discord.NotFound:
                pass  # Message was already deleted

        elif action == "warn":
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            # Send a warning
            await message.channel.send(
                f"{message.author.mention}, **Warning**: Your message violated the server's filter settings. "
                f"Please follow the server rules."
            )

        elif action == "mute":
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            # Time out the user for 10 minutes
            try:
                duration = datetime.timedelta(minutes=10)
                await message.author.timeout(
                    until=discord.utils.utcnow() + duration,
                    reason=f"Automated timeout: Triggered {filter_type}",
                )

                await message.channel.send(
                    f"{message.author.mention} has been muted for 10 minutes for violating the server's filter settings."
                )

            except discord.Forbidden:
                self.logger.warning(
                    f"No permission to timeout user in {message.guild.name}"
                )

                # Fall back to a warning
                await message.channel.send(
                    f"{message.author.mention}, **Warning**: Your message violated the server's filter settings. "
                    f"Please follow the server rules."
                )

    @commands.group(name="filter", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def filter(self, ctx: commands.Context):
        """
        Configure automatic message filtering.

        Use subcommands to configure different filters:
        - words: Filter specific words or phrases
        - invites: Filter Discord invite links
        - caps: Filter excessive capital letters
        """
        settings = self._get_guild_settings(ctx.guild.id)

        embed = discord.Embed(
            title="Filter Settings",
            description="Current filter configuration for this server",
            color=discord.Color.blue(),
        )

        # Word filter status
        word_filter = settings["word_filter"]
        word_status = (
            f"**Enabled**: {word_filter['enabled']}\n"
            f"**Action**: {word_filter['action']}\n"
            f"**Filtered Words**: {len(word_filter['words'])}"
        )
        embed.add_field(name="Word Filter", value=word_status, inline=False)

        # Invite filter status
        invite_filter = settings["invite_filter"]
        invite_status = (
            f"**Enabled**: {invite_filter['enabled']}\n"
            f"**Action**: {invite_filter['action']}"
        )
        embed.add_field(name="Invite Filter", value=invite_status, inline=False)

        # Caps filter status
        caps_filter = settings["caps_filter"]
        caps_status = (
            f"**Enabled**: {caps_filter['enabled']}\n"
            f"**Action**: {caps_filter['action']}\n"
            f"**Threshold**: {caps_filter['threshold']}%\n"
            f"**Min Length**: {caps_filter['min_length']} characters"
        )
        embed.add_field(name="Caps Filter", value=caps_status, inline=False)

        await ctx.send(embed=embed)

    @filter.command(name="words")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def filter_words(
        self, ctx: commands.Context, action: str, *, words: Optional[str] = None
    ):
        """
        Configure word filtering.

        Args:
            action: 'enable', 'disable', 'add', 'remove', 'list', or 'action'
            words: Words to add/remove or action type (delete, warn, mute)

        Examples:
            !filter words enable
            !filter words disable
            !filter words add bad word another_bad_word
            !filter words remove bad word
            !filter words list
            !filter words action delete
        """
        settings = self._get_guild_settings(ctx.guild.id)
        word_filter = settings["word_filter"]

        if action.lower() == "enable":
            word_filter["enabled"] = True
            await ctx.send("Word filter enabled.")

        elif action.lower() == "disable":
            word_filter["enabled"] = False
            await ctx.send("Word filter disabled.")

        elif action.lower() == "add":
            if not words:
                await ctx.send("Please specify words to add to the filter.")
                return

            new_words = [w.strip().lower() for w in words.split()]
            word_filter["words"].extend(
                w for w in new_words if w not in word_filter["words"]
            )
            await ctx.send(f"Added {len(new_words)} word(s) to the filter.")

        elif action.lower() == "remove":
            if not words:
                await ctx.send("Please specify words to remove from the filter.")
                return

            remove_words = [w.strip().lower() for w in words.split()]
            original_count = len(word_filter["words"])
            word_filter["words"] = [
                w for w in word_filter["words"] if w not in remove_words
            ]
            removed_count = original_count - len(word_filter["words"])

            await ctx.send(f"Removed {removed_count} word(s) from the filter.")

        elif action.lower() == "list":
            if not word_filter["words"]:
                await ctx.send("No words in the filter.")
                return

            # Send the list in DM to avoid showing filtered words in chat
            try:
                words_list = ", ".join(word_filter["words"])

                if len(words_list) > 1900:
                    words_list = words_list[:1900] + "... (list truncated)"

                await ctx.author.send(
                    f"**Filtered words in {ctx.guild.name}**:\n{words_list}"
                )
                await ctx.send(
                    "I've sent you the list of filtered words in a private message."
                )
            except discord.Forbidden:
                await ctx.send(
                    "I couldn't send you a DM. Please enable DMs from server members."
                )

        elif action.lower() == "action":
            if not words or words.lower() not in ["delete", "warn", "mute"]:
                await ctx.send(
                    "Please specify a valid action: `delete`, `warn`, or `mute`."
                )
                return

            word_filter["action"] = words.lower()
            await ctx.send(f"Word filter action set to: {words.lower()}")

        else:
            await ctx.send(
                "Invalid action. Use `enable`, `disable`, `add`, `remove`, `list`, or `action`."
            )

    @filter.command(name="invites")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def filter_invites(
        self, ctx: commands.Context, action: str, option: Optional[str] = None
    ):
        """
        Configure Discord invite link filtering.

        Args:
            action: 'enable', 'disable', or 'action'
            option: Action type if setting action (delete, warn, mute)

        Examples:
            !filter invites enable
            !filter invites disable
            !filter invites action warn
        """
        settings = self._get_guild_settings(ctx.guild.id)
        invite_filter = settings["invite_filter"]

        if action.lower() == "enable":
            invite_filter["enabled"] = True
            await ctx.send("Invite filter enabled.")

        elif action.lower() == "disable":
            invite_filter["enabled"] = False
            await ctx.send("Invite filter disabled.")

        elif action.lower() == "action":
            if not option or option.lower() not in ["delete", "warn", "mute"]:
                await ctx.send(
                    "Please specify a valid action: `delete`, `warn`, or `mute`."
                )
                return

            invite_filter["action"] = option.lower()
            await ctx.send(f"Invite filter action set to: {option.lower()}")

        else:
            await ctx.send("Invalid action. Use `enable`, `disable`, or `action`.")

    @filter.command(name="caps")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def filter_caps(
        self, ctx: commands.Context, action: str, value: Optional[int] = None
    ):
        """
        Configure excessive caps filtering.

        Args:
            action: 'enable', 'disable', 'threshold', 'minlength', or 'action'
            value: Threshold percentage, min length, or action type

        Examples:
            !filter caps enable
            !filter caps disable
            !filter caps threshold 80
            !filter caps minlength 15
            !filter caps action delete
        """
        settings = self._get_guild_settings(ctx.guild.id)
        caps_filter = settings["caps_filter"]

        if action.lower() == "enable":
            caps_filter["enabled"] = True
            await ctx.send("Caps filter enabled.")

        elif action.lower() == "disable":
            caps_filter["enabled"] = False
            await ctx.send("Caps filter disabled.")

        elif action.lower() == "threshold":
            if value is None or value < 1 or value > 100:
                await ctx.send(
                    "Please specify a valid threshold percentage between 1 and 100."
                )
                return

            caps_filter["threshold"] = value
            await ctx.send(f"Caps filter threshold set to {value}%.")

        elif action.lower() == "minlength":
            if value is None or value < 1:
                await ctx.send(
                    "Please specify a valid minimum message length (at least 1)."
                )
                return

            caps_filter["min_length"] = value
            await ctx.send(
                f"Caps filter minimum message length set to {value} characters."
            )

        elif action.lower() == "action":
            options = ["delete", "warn", "mute"]
            option = (
                value
                if isinstance(value, str)
                else (
                    ctx.message.content.split(maxsplit=3)[3]
                    if len(ctx.message.content.split()) > 3
                    else None
                )
            )

            if not option or option.lower() not in options:
                await ctx.send(
                    "Please specify a valid action: `delete`, `warn`, or `mute`."
                )
                return

            caps_filter["action"] = option.lower()
            await ctx.send(f"Caps filter action set to: {option.lower()}")

        else:
            await ctx.send(
                "Invalid action. Use `enable`, `disable`, `threshold`, `minlength`, or `action`."
            )

    @commands.command(name="clean")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def clean(self, ctx: commands.Context, amount: int = 10):
        """
        Delete bot messages and commands.

        Args:
            amount: Number of messages to check (default: 10)

        Example:
            !clean 20
        """
        if amount <= 0 or amount > 100:
            await ctx.send("Please provide a number between 1 and 100.")
            return

        def is_bot_or_command(message):
            # Check if message is from the bot or is a command
            return message.author.id == self.bot.user.id or message.content.startswith(
                ctx.prefix
            )

        try:
            deleted = await ctx.channel.purge(
                limit=amount,
                check=is_bot_or_command,
                bulk=True,
                reason=f"Clean command used by {ctx.author}",
            )

            confirmation = await ctx.send(
                f"Cleaned {len(deleted)} bot messages and commands."
            )

            # Delete confirmation after a few seconds
            await asyncio.sleep(3)
            await confirmation.delete()

            self.logger.info(
                f"{ctx.author} cleaned {len(deleted)} messages in #{ctx.channel.name}"
            )

        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages.")
        except discord.HTTPException as e:
            await ctx.send(f"Error cleaning messages: {str(e)}")

    @commands.command(name="slowmode", aliases=["slow"])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def slowmode(
        self,
        ctx: commands.Context,
        seconds: Optional[int] = None,
        channel: Optional[discord.TextChannel] = None,
    ):
        """
        Set slowmode for a channel.

        Args:
            seconds: Slowmode delay in seconds (0 to disable, max 21600 = 6 hours)
            channel: Channel to set slowmode for (defaults to current channel)

        Examples:
            !slowmode 5
            !slowmode 0
            !slowmode 10 #general
        """
        target_channel = channel or ctx.channel

        # If no seconds provided, show current setting
        if seconds is None:
            current_slowmode = target_channel.slowmode_delay
            if current_slowmode == 0:
                await ctx.send(
                    f"Slowmode is currently disabled in {target_channel.mention}."
                )
            else:
                await ctx.send(
                    f"Slowmode in {target_channel.mention} is currently set to {current_slowmode} seconds."
                )
            return

        # Validate seconds
        if seconds < 0 or seconds > 21600:
            await ctx.send(
                "Slowmode delay must be between 0 and 21600 seconds (6 hours)."
            )
            return

        try:
            await target_channel.edit(slowmode_delay=seconds)

            if seconds == 0:
                await ctx.send(f"Slowmode disabled in {target_channel.mention}.")
            else:
                await ctx.send(
                    f"Slowmode set to {seconds} seconds in {target_channel.mention}."
                )

            self.logger.info(
                f"{ctx.author} set slowmode to {seconds}s in #{target_channel.name}"
            )

        except discord.Forbidden:
            await ctx.send("I don't have permission to manage this channel.")
        except discord.HTTPException as e:
            await ctx.send(f"Error setting slowmode: {str(e)}")

    @commands.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def lock(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        *,
        reason: Optional[str] = None,
    ):
        """
        Lock a channel to prevent members from sending messages.

        Args:
            channel: Channel to lock (defaults to current channel)
            reason: Reason for locking the channel

        Examples:
            !lock
            !lock #general
            !lock #announcements Preparing for an announcement
        """
        target_channel = channel or ctx.channel
        reason = reason or f"Locked by {ctx.author}"

        # Get the default role (everyone)
        default_role = ctx.guild.default_role

        # Check current permissions
        current_perms = target_channel.permissions_for(default_role)
        if not current_perms.send_messages:
            await ctx.send(f"{target_channel.mention} is already locked.")
            return

        try:
            # Update permissions to deny send_messages
            await target_channel.set_permissions(
                default_role, send_messages=False, reason=reason
            )

            # Send confirmation
            embed = discord.Embed(
                title="🔒 Channel Locked",
                description=f"This channel has been locked by {ctx.author.mention}.",
                color=discord.Color.red(),
            )

            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)

            await target_channel.send(embed=embed)

            # Log the action
            self.logger.info(f"{ctx.author} locked #{target_channel.name}: {reason}")

        except discord.Forbidden:
            await ctx.send("I don't have permission to manage channel permissions.")
        except discord.HTTPException as e:
            await ctx.send(f"Error locking channel: {str(e)}")

    @commands.command(name="unlock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def unlock(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        *,
        reason: Optional[str] = None,
    ):
        """
        Unlock a previously locked channel.

        Args:
            channel: Channel to unlock (defaults to current channel)
            reason: Reason for unlocking the channel

        Examples:
            !unlock
            !unlock #general
            !unlock #announcements Announcement complete
        """
        target_channel = channel or ctx.channel
        reason = reason or f"Unlocked by {ctx.author}"

        # Get the default role (everyone)
        default_role = ctx.guild.default_role

        # Check current permissions
        current_perms = target_channel.permissions_for(default_role)
        if current_perms.send_messages:
            await ctx.send(f"{target_channel.mention} is already unlocked.")
            return

        try:
            # Reset permissions to allow send_messages
            await target_channel.set_permissions(
                default_role, send_messages=None, reason=reason  # Reset to default
            )

            # Send confirmation
            embed = discord.Embed(
                title="🔓 Channel Unlocked",
                description=f"This channel has been unlocked by {ctx.author.mention}.",
                color=discord.Color.green(),
            )

            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)

            await target_channel.send(embed=embed)

            # Log the action
            self.logger.info(f"{ctx.author} unlocked #{target_channel.name}: {reason}")

        except discord.Forbidden:
            await ctx.send("I don't have permission to manage channel permissions.")
        except discord.HTTPException as e:
            await ctx.send(f"Error unlocking channel: {str(e)}")


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(ModerationCog(bot))
