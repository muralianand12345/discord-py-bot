"""
Admin commands for server management.
"""

import discord
import asyncio
import logging
import datetime
from discord.ext import commands
from typing import Optional, Union

from utils.settings import COOLDOWNS


class AdminCog(commands.Cog, name="Admin"):
    """Admin commands for server management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("admin_cog")

    @commands.command(name="purge")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def purge(
        self,
        ctx: commands.Context,
        amount: int,
        member: Optional[discord.Member] = None,
    ):
        """
        Delete a specified number of messages, optionally from a specific user.

        Args:
            amount: Number of messages to delete (1-100)
            member: Optional member to filter messages by

        Examples:
            !purge 10
            !purge 25 @user
        """
        if amount <= 0 or amount > 100:
            await ctx.send("Please provide a number between 1 and 100.")
            return

        def check_messages(message):
            # If member specified, only delete their messages
            if member:
                return message.author.id == member.id
            return True

        try:
            deleted = await ctx.channel.purge(
                limit=amount + 1,  # +1 to include the command message
                check=check_messages,
                bulk=True,
                reason=f"Purge command used by {ctx.author}",
            )

            # Account for command message in count
            actual_deleted = len(deleted) - 1

            confirmation = await ctx.send(
                f"Deleted {actual_deleted} message{'s' if actual_deleted != 1 else ''}."
            )

            # Delete confirmation after a few seconds
            await asyncio.sleep(3)
            await confirmation.delete()

            self.logger.info(
                f"{ctx.author} purged {actual_deleted} messages in #{ctx.channel.name}"
            )

        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages.")
        except discord.HTTPException as e:
            await ctx.send(f"Error deleting messages: {str(e)}")

    @commands.command(name="kick")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: Optional[str] = None,
    ):
        """
        Kick a member from the server.

        Args:
            member: The member to kick
            reason: Reason for the kick (optional)

        Example:
            !kick @user Spamming
        """
        if member.id == ctx.author.id:
            await ctx.send("You can't kick yourself.")
            return

        if (
            member.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            await ctx.send("You can't kick someone with a higher or equal role.")
            return

        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("I can't kick this member due to role hierarchy.")
            return

        reason = reason or f"Kicked by {ctx.author}"

        try:
            await member.kick(reason=reason)
            await ctx.send(
                f"Kicked {member.mention} from the server.\nReason: {reason}"
            )
            self.logger.info(f"{ctx.author} kicked {member} for: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick members.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to kick member: {str(e)}")

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def ban(
        self,
        ctx: commands.Context,
        member: Union[discord.Member, discord.User],
        delete_days: Optional[int] = 0,
        *,
        reason: Optional[str] = None,
    ):
        """
        Ban a member or user from the server.

        Args:
            member: The member or user to ban
            delete_days: Days of messages to delete (0-7, default: 0)
            reason: Reason for the ban (optional)

        Example:
            !ban @user 1 Breaking rules
        """
        if delete_days < 0 or delete_days > 7:
            await ctx.send("The delete_days parameter must be between 0 and 7.")
            return

        if isinstance(member, discord.Member):
            if member.id == ctx.author.id:
                await ctx.send("You can't ban yourself.")
                return

            if (
                member.top_role >= ctx.author.top_role
                and ctx.author.id != ctx.guild.owner_id
            ):
                await ctx.send("You can't ban someone with a higher or equal role.")
                return

            if member.top_role >= ctx.guild.me.top_role:
                await ctx.send("I can't ban this member due to role hierarchy.")
                return

        reason = reason or f"Banned by {ctx.author}"

        try:
            await ctx.guild.ban(member, delete_message_days=delete_days, reason=reason)
            await ctx.send(
                f"Banned {member.mention} from the server.\nReason: {reason}"
            )
            self.logger.info(f"{ctx.author} banned {member} for: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban members.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to ban member: {str(e)}")

    @commands.command(name="unban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def unban(
        self, ctx: commands.Context, user_id: int, *, reason: Optional[str] = None
    ):
        """
        Unban a user from the server.

        Args:
            user_id: The ID of the user to unban
            reason: Reason for the unban (optional)

        Example:
            !unban 123456789012345678 Good behavior
        """
        reason = reason or f"Unbanned by {ctx.author}"

        try:
            # Get the ban entry for this user
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            user = ban_entry.user

            # Unban the user
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"Unbanned {user.mention} ({user}).\nReason: {reason}")
            self.logger.info(f"{ctx.author} unbanned {user} for: {reason}")
        except discord.NotFound:
            await ctx.send("This user is not banned.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban members.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to unban user: {str(e)}")

    @commands.command(name="mute")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: Optional[str] = "1h",
        *,
        reason: Optional[str] = None,
    ):
        """
        Timeout (mute) a member for a specified duration.

        Args:
            member: The member to mute
            duration: Duration of mute (format: 1d, 2h, 30m, etc.) Default: 1h
            reason: Reason for the mute (optional)

        Example:
            !mute @user 2h Spamming
        """
        if member.id == ctx.author.id:
            await ctx.send("You can't mute yourself.")
            return

        if (
            member.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            await ctx.send("You can't mute someone with a higher or equal role.")
            return

        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("I can't mute this member due to role hierarchy.")
            return

        # Parse duration (e.g., "1d", "2h", "30m")
        duration_seconds = 3600  # Default: 1 hour
        unit = duration[-1].lower()
        try:
            value = int(duration[:-1])
            if unit == "d":
                duration_seconds = value * 86400  # days
            elif unit == "h":
                duration_seconds = value * 3600  # hours
            elif unit == "m":
                duration_seconds = value * 60  # minutes
            elif unit == "s":
                duration_seconds = value  # seconds
        except ValueError:
            await ctx.send(
                "Invalid duration format. Use format like '1d', '2h', '30m', etc."
            )
            return

        # Timeout cannot exceed 28 days
        if duration_seconds > 28 * 24 * 60 * 60:
            await ctx.send("Timeout duration cannot exceed 28 days.")
            return

        reason = reason or f"Muted by {ctx.author}"

        try:
            # Calculate timeout end time
            until = discord.utils.utcnow() + datetime.timedelta(
                seconds=duration_seconds
            )

            # Apply timeout
            await member.timeout(until=until, reason=reason)

            # Format human-readable duration
            duration_str = ""
            if duration_seconds >= 86400:  # days
                days = duration_seconds // 86400
                duration_str += f"{days} day{'s' if days != 1 else ''} "
                duration_seconds %= 86400
            if duration_seconds >= 3600:  # hours
                hours = duration_seconds // 3600
                duration_str += f"{hours} hour{'s' if hours != 1 else ''} "
                duration_seconds %= 3600
            if duration_seconds >= 60:  # minutes
                minutes = duration_seconds // 60
                duration_str += f"{minutes} minute{'s' if minutes != 1 else ''} "
                duration_seconds %= 60
            if duration_seconds > 0:  # seconds
                duration_str += (
                    f"{duration_seconds} second{'s' if duration_seconds != 1 else ''}"
                )

            duration_str = duration_str.strip()

            await ctx.send(
                f"Muted {member.mention} for {duration_str}.\nReason: {reason}"
            )
            self.logger.info(
                f"{ctx.author} muted {member} for {duration_str}: {reason}"
            )
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout members.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to mute member: {str(e)}")

    @commands.command(name="unmute")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def unmute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: Optional[str] = None,
    ):
        """
        Remove a timeout (unmute) from a member.

        Args:
            member: The member to unmute
            reason: Reason for the unmute (optional)

        Example:
            !unmute @user Good behavior
        """
        if not member.is_timed_out():
            await ctx.send(f"{member.mention} is not currently muted.")
            return

        reason = reason or f"Unmuted by {ctx.author}"

        try:
            await member.timeout(until=None, reason=reason)  # Remove timeout
            await ctx.send(f"Unmuted {member.mention}.\nReason: {reason}")
            self.logger.info(f"{ctx.author} unmuted {member}: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage timeouts.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to unmute member: {str(e)}")

    @commands.command(name="server_info", aliases=["serverinfo", "server"])
    @commands.guild_only()
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.channel)
    async def server_info(self, ctx: commands.Context):
        """Display information about the current server."""
        guild = ctx.guild

        # Get counts
        total_members = len(guild.members)
        bot_count = len([m for m in guild.members if m.bot])
        human_count = total_members - bot_count

        # Get channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        # Get role count (excluding @everyone)
        role_count = len(guild.roles) - 1

        # Create embed
        embed = discord.Embed(
            title=f"{guild.name} Server Information",
            description=guild.description or "No description",
            color=discord.Color.blue(),
        )

        # Add server icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Basic info
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(
            name="Created On", value=guild.created_at.strftime("%B %d, %Y"), inline=True
        )

        # Member counts
        embed.add_field(name="Total Members", value=total_members, inline=True)
        embed.add_field(name="Humans", value=human_count, inline=True)
        embed.add_field(name="Bots", value=bot_count, inline=True)

        # Channel counts
        embed.add_field(name="Text Channels", value=text_channels, inline=True)
        embed.add_field(name="Voice Channels", value=voice_channels, inline=True)
        embed.add_field(name="Categories", value=categories, inline=True)

        # Other info
        embed.add_field(name="Roles", value=role_count, inline=True)
        embed.add_field(
            name="Verification Level",
            value=str(guild.verification_level).title(),
            inline=True,
        )
        embed.add_field(
            name="Boosts",
            value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)",
            inline=True,
        )

        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(AdminCog(bot))
