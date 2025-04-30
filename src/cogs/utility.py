"""
Utility commands for the Discord bot.
"""

import time
import random
import asyncio
import discord
import logging
import datetime
import platform
from typing import Optional
from discord.ext import commands

from utils.settings import COOLDOWNS, BOT_PREFIX


class UtilityCog(commands.Cog, name="Utility"):
    """Utility commands for the Discord bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("utility_cog")
        self.start_time = time.time()

    @commands.command(name="ping")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def ping(self, ctx: commands.Context):
        """Check the bot's latency to Discord."""
        start = time.perf_counter()
        message = await ctx.send("Pinging...")
        end = time.perf_counter()

        # Calculate different latencies
        api_latency = round(self.bot.latency * 1000)
        message_latency = round((end - start) * 1000)

        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(
            name="Message Latency", value=f"{message_latency}ms", inline=True
        )

        await message.edit(content=None, embed=embed)

    @commands.command(name="uptime")
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def uptime(self, ctx: commands.Context):
        """Display how long the bot has been online."""
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)

        # Convert seconds to days, hours, minutes, seconds
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Create a formatted uptime string
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days} day{'s' if days != 1 else ''}, "
        if hours > 0 or days > 0:
            uptime_str += f"{hours} hour{'s' if hours != 1 else ''}, "
        if minutes > 0 or hours > 0 or days > 0:
            uptime_str += f"{minutes} minute{'s' if minutes != 1 else ''}, "
        uptime_str += f"{seconds} second{'s' if seconds != 1 else ''}"

        embed = discord.Embed(
            title="Bot Uptime",
            description=f"I've been online for {uptime_str}",
            color=discord.Color.blue(),
        )

        await ctx.send(embed=embed)

    @commands.command(name="botinfo", aliases=["info"])
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.channel)
    async def botinfo(self, ctx: commands.Context):
        """Display information about the bot."""
        # Get system information
        python_version = platform.python_version()
        discord_py_version = discord.__version__

        # Get bot stats
        server_count = len(self.bot.guilds)
        member_count = sum(guild.member_count for guild in self.bot.guilds)

        # Calculate uptime
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)

        # Convert seconds to days, hours, minutes
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format uptime string
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days}d "
        if hours > 0 or days > 0:
            uptime_str += f"{hours}h "
        if minutes > 0 or hours > 0 or days > 0:
            uptime_str += f"{minutes}m "
        uptime_str += f"{seconds}s"

        # Create embed
        embed = discord.Embed(
            title=f"{self.bot.user.name} Information",
            description="A multi-purpose Discord bot with modular commands",
            color=discord.Color.blue(),
        )

        # Set bot avatar as thumbnail
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # Add basic info
        embed.add_field(
            name="Bot Version",
            value=getattr(self.bot, "app_version", "0.2.0"),
            inline=True,
        )
        embed.add_field(name="Prefix", value=BOT_PREFIX, inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)

        # Add technical info
        embed.add_field(name="Python Version", value=python_version, inline=True)
        embed.add_field(
            name="Discord.py Version", value=discord_py_version, inline=True
        )
        embed.add_field(
            name="API Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True
        )

        # Add stats
        embed.add_field(name="Servers", value=server_count, inline=True)
        embed.add_field(name="Users", value=member_count, inline=True)
        embed.add_field(name="Commands", value=len(self.bot.commands), inline=True)

        # Add links
        embed.add_field(
            name="Links",
            value="[GitHub](https://github.com/muralianand12345/discord-name-changer)",
            inline=False,
        )

        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.send(embed=embed)

    @commands.command(name="userinfo", aliases=["user", "whois"])
    @commands.guild_only()
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def userinfo(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        """
        Display information about a user.

        Args:
            member: The member to get info about (defaults to you)

        Example:
            !userinfo @user
        """
        # Default to the command invoker if no member specified
        target = member or ctx.author

        # Get join position
        join_position = (
            sorted(
                ctx.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow()
            ).index(target)
            + 1
        )

        # Get user activity
        activities = []
        for activity in target.activities:
            if isinstance(activity, discord.Game):
                activities.append(f"Playing {activity.name}")
            elif isinstance(activity, discord.Streaming):
                activities.append(f"Streaming [{activity.name}]({activity.url})")
            elif isinstance(activity, discord.Spotify):
                activities.append(f"Listening to {activity.title} by {activity.artist}")
            elif isinstance(activity, discord.CustomActivity):
                activities.append(
                    f"{activity.emoji} {activity.name}"
                    if activity.emoji
                    else activity.name
                )

        activity_text = "\n".join(activities) if activities else "No activity"

        # Create embed
        embed = discord.Embed(
            title=f"User Information - {target}",
            color=(
                target.color
                if target.color != discord.Color.default()
                else discord.Color.blue()
            ),
        )

        # Set user avatar
        embed.set_thumbnail(url=target.display_avatar.url)

        # Basic information
        embed.add_field(name="User ID", value=target.id, inline=True)
        embed.add_field(name="Nickname", value=target.nick or "None", inline=True)
        embed.add_field(name="Bot", value="Yes" if target.bot else "No", inline=True)

        # Time information
        created_at = target.created_at.strftime("%b %d, %Y • %H:%M:%S UTC")
        joined_at = (
            target.joined_at.strftime("%b %d, %Y • %H:%M:%S UTC")
            if target.joined_at
            else "Unknown"
        )

        embed.add_field(name="Account Created", value=f"{created_at}", inline=True)
        embed.add_field(name="Joined Server", value=f"{joined_at}", inline=True)
        embed.add_field(name="Join Position", value=f"#{join_position}", inline=True)

        # Status
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫",
        }

        status_text = (
            f"{status_emoji.get(target.status, '⚪')} {str(target.status).title()}"
        )
        embed.add_field(name="Status", value=status_text, inline=True)

        # Mobile, desktop, web status
        platform_status = []
        if target.desktop_status != discord.Status.offline:
            platform_status.append("Desktop")
        if target.mobile_status != discord.Status.offline:
            platform_status.append("Mobile")
        if target.web_status != discord.Status.offline:
            platform_status.append("Web")

        platform_text = ", ".join(platform_status) if platform_status else "None"
        embed.add_field(name="Platforms", value=platform_text, inline=True)

        # Activity
        embed.add_field(name="Activity", value=activity_text, inline=True)

        # Roles
        roles = [role.mention for role in target.roles if role.name != "@everyone"]
        roles.reverse()  # Display highest roles first

        if roles:
            roles_text = ", ".join(roles)
            if len(roles_text) > 1024:  # Field value character limit
                roles_text = f"{len(roles)} roles (too many to display)"
        else:
            roles_text = "No roles"

        embed.add_field(name=f"Roles ({len(roles)})", value=roles_text, inline=False)

        # Permissions
        key_permissions = []
        permissions = target.guild_permissions

        if permissions.administrator:
            key_permissions.append("Administrator")
        else:
            if permissions.manage_guild:
                key_permissions.append("Manage Server")
            if permissions.ban_members:
                key_permissions.append("Ban Members")
            if permissions.kick_members:
                key_permissions.append("Kick Members")
            if permissions.manage_channels:
                key_permissions.append("Manage Channels")
            if permissions.manage_roles:
                key_permissions.append("Manage Roles")
            if permissions.moderate_members:
                key_permissions.append("Timeout Members")
            if permissions.manage_messages:
                key_permissions.append("Manage Messages")

        perm_text = (
            ", ".join(key_permissions) if key_permissions else "No key permissions"
        )
        embed.add_field(name="Key Permissions", value=perm_text, inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.send(embed=embed)

    @commands.command(name="avatar", aliases=["av", "pfp"])
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def avatar(
        self, ctx: commands.Context, member: Optional[discord.Member] = None
    ):
        """
        Display a user's avatar.

        Args:
            member: The member whose avatar to show (defaults to you)

        Example:
            !avatar @user
        """
        target = member or ctx.author

        embed = discord.Embed(title=f"{target}'s Avatar", color=discord.Color.blue())

        # Get the avatar URL with the maximum size
        avatar_url = target.display_avatar.url

        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.send(embed=embed)

    @commands.command(name="poll")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def poll(self, ctx: commands.Context, question: str, *options):
        """
        Create a poll with up to 10 options.

        Args:
            question: The poll question
            options: Poll options (up to 10)

        Example:
            !poll "Favorite color?" Red Blue Green Yellow
        """
        if len(options) < 2:
            await ctx.send("You need at least 2 options for a poll!")
            return

        if len(options) > 10:
            await ctx.send("You can only have up to 10 options in a poll!")
            return

        # Emoji options (0-9)
        emoji_options = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        # Create the poll embed
        embed = discord.Embed(
            title=question,
            description="\n".join(
                [f"{emoji_options[i]} {option}" for i, option in enumerate(options)]
            ),
            color=discord.Color.blue(),
        )

        embed.set_footer(text=f"Poll created by {ctx.author}")

        # Send the poll and add reactions
        poll_message = await ctx.send(embed=embed)

        for i in range(len(options)):
            await poll_message.add_reaction(emoji_options[i])

        # Delete the command message if possible
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command(name="remind", aliases=["reminder"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remind(self, ctx: commands.Context, time: str, *, reminder: str):
        """
        Set a reminder.

        Args:
            time: Time until reminder (e.g., 10s, 5m, 2h, 1d)
            reminder: What to remind you about

        Example:
            !remind 1h Check on the cake in the oven
        """
        # Parse the time string
        time_unit = time[-1].lower()
        try:
            time_val = int(time[:-1])
        except ValueError:
            await ctx.send(
                "Invalid time format. Use format like '10s', '5m', '2h', '1d'."
            )
            return

        # Convert to seconds
        if time_unit == "s":
            seconds = time_val
        elif time_unit == "m":
            seconds = time_val * 60
        elif time_unit == "h":
            seconds = time_val * 3600
        elif time_unit == "d":
            seconds = time_val * 86400
        else:
            await ctx.send(
                "Invalid time unit. Use 's' for seconds, 'm' for minutes, 'h' for hours, or 'd' for days."
            )
            return

        # Set a maximum reminder time (7 days)
        if seconds > 7 * 86400:
            await ctx.send("Reminder time too long. Maximum is 7 days.")
            return

        # Confirmation message
        confirm_embed = discord.Embed(
            title="Reminder Set",
            description=f"I'll remind you about: **{reminder}**",
            color=discord.Color.green(),
        )

        # Calculate when the reminder will trigger
        remind_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
        confirm_embed.add_field(
            name="When", value=f"<t:{int(remind_time.timestamp())}:R>", inline=False
        )

        await ctx.send(embed=confirm_embed)

        # Wait for the specified time
        await asyncio.sleep(seconds)

        # Send the reminder
        reminder_embed = discord.Embed(
            title="Reminder", description=reminder, color=discord.Color.blue()
        )

        reminder_embed.add_field(
            name="From",
            value=f"[Jump to original message]({ctx.message.jump_url})",
            inline=False,
        )
        reminder_embed.set_footer(text=f"Reminder from {time} ago")

        try:
            await ctx.author.send(embed=reminder_embed)
        except discord.Forbidden:
            await ctx.send(
                f"{ctx.author.mention}, here's your reminder:", embed=reminder_embed
            )

    @commands.command(name="roll", aliases=["dice"])
    @commands.cooldown(1, COOLDOWNS.get("default", 3), commands.BucketType.user)
    async def roll(self, ctx: commands.Context, dice: str = "1d20"):
        """
        Roll dice using DnD notation.

        Args:
            dice: Dice notation (e.g., 1d20, 2d6, 3d8+5)

        Example:
            !roll 2d6
            !roll 1d20+5
        """
        # Parse the dice notation
        dice_pattern = dice.lower().replace(" ", "")

        try:
            # Handle modifiers
            modifier = 0
            if "+" in dice_pattern:
                dice_pattern, mod_str = dice_pattern.split("+")
                modifier = int(mod_str)
            elif "-" in dice_pattern:
                dice_pattern, mod_str = dice_pattern.split("-")
                modifier = -int(mod_str)

            # Parse the dice part
            if "d" not in dice_pattern:
                await ctx.send(
                    "Invalid dice notation. Use format like '1d20', '2d6', etc."
                )
                return

            num_dice, dice_sides = map(int, dice_pattern.split("d"))

            # Set reasonable limits
            if num_dice <= 0 or num_dice > 100:
                await ctx.send("Number of dice must be between 1 and 100.")
                return

            if dice_sides <= 0 or dice_sides > 1000:
                await ctx.send("Dice sides must be between 1 and 1000.")
                return

            # Roll the dice
            rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
            total = sum(rolls) + modifier

            # Create the result message
            if num_dice == 1 and modifier == 0:
                result = f"🎲 {total}"
            elif num_dice == 1:
                sign = "+" if modifier > 0 else ""
                result = f"🎲 {rolls[0]} {sign}{modifier} = {total}"
            else:
                rolls_str = " + ".join(str(r) for r in rolls)

                if modifier != 0:
                    sign = "+" if modifier > 0 else ""
                    result = f"🎲 ({rolls_str}) {sign}{modifier} = {total}"
                else:
                    result = f"🎲 {rolls_str} = {total}"

            await ctx.send(f"{ctx.author.mention} rolled **{dice}**: {result}")

        except ValueError:
            await ctx.send(
                "Invalid dice notation. Use format like '1d20', '2d6+3', etc."
            )
        except Exception as e:
            await ctx.send(f"Error rolling dice: {str(e)}")


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(UtilityCog(bot))
