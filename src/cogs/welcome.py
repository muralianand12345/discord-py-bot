"""
Welcome and goodbye message handling for Discord bot.
Includes auto-role assignment for new members.
"""

import asyncio
import datetime
import logging
import random
import discord
from discord.ext import commands
from typing import Optional

from utils.llm import LLM
from utils.settings import (
    WELCOME_CHANNEL_ID,
    GOODBYE_CHANNEL_ID,
    DEFAULT_ROLE_ID,
    WELCOME_EMBED_COLOR,
    GOODBYE_EMBED_COLOR,
    PROMPTS,
)


class WelcomeCog(commands.Cog, name="Welcome"):
    """Welcome and goodbye message handling for Discord server."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("welcome_cog")
        self.llm = LLM()

        # Fallback messages in case LLM fails
        self.fallback_welcome_messages = [
            "Welcome to the server! We're glad to have you with us.",
            "A new member has arrived! Welcome to our community.",
            "Everyone please welcome our newest member to the server!",
            "Welcome aboard! We hope you enjoy your stay with us.",
            "Thanks for joining us! Feel free to introduce yourself.",
        ]

        self.fallback_goodbye_messages = [
            "Goodbye! We hope to see you again soon.",
            "A member has left the server. They will be missed!",
            "Farewell and best wishes on your journey!",
            "Sad to see you go. Take care!",
            "We're sorry to see you leave. You're always welcome back!",
        ]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event triggered when a member joins the server.
        Sends welcome message and assigns default role.
        """
        try:
            # Get welcome channel
            welcome_channel = None
            if WELCOME_CHANNEL_ID:
                welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
                if not welcome_channel:
                    self.logger.warning(
                        f"Welcome channel with ID {WELCOME_CHANNEL_ID} not found!"
                    )

            # Get default role
            default_role = None
            if DEFAULT_ROLE_ID:
                default_role = member.guild.get_role(DEFAULT_ROLE_ID)
                if not default_role:
                    self.logger.warning(
                        f"Default role with ID {DEFAULT_ROLE_ID} not found!"
                    )

            # Send welcome message if channel is configured
            if welcome_channel:
                await self._send_welcome_message(member, welcome_channel)

            # Assign default role if configured
            if default_role:
                await self._assign_role(member, default_role)

        except Exception as e:
            self.logger.error(f"Error in on_member_join event: {str(e)}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        Event triggered when a member leaves the server.
        Sends goodbye message.
        """
        try:
            # Get goodbye channel
            goodbye_channel = None
            if GOODBYE_CHANNEL_ID:
                goodbye_channel = self.bot.get_channel(GOODBYE_CHANNEL_ID)
                if not goodbye_channel:
                    self.logger.warning(
                        f"Goodbye channel with ID {GOODBYE_CHANNEL_ID} not found!"
                    )

            # Send goodbye message if channel is configured
            if goodbye_channel:
                await self._send_goodbye_message(member, goodbye_channel)

        except Exception as e:
            self.logger.error(f"Error in on_member_remove event: {str(e)}")

    async def _generate_message_with_llm(
        self, prompt_type: str, username: str, server_name: str
    ) -> str:
        """Generate a message using the LLM."""
        try:
            # Get the prompts
            prompts = PROMPTS.get(prompt_type, {})
            if not prompts:
                raise ValueError(f"No prompts found for type: {prompt_type}")

            system_message = prompts.get("system_message", "")
            user_message = prompts.get("user_message", "").format(
                username=username, server_name=server_name
            )

            # Prepare messages for LLM
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]

            # Call the LLM
            response = await self.llm.invoke(messages, max_tokens=150)
            return response

        except Exception as e:
            self.logger.error(
                f"Error generating {prompt_type} message with LLM: {str(e)}"
            )
            # Return a fallback message
            if prompt_type == "welcome":
                return random.choice(self.fallback_welcome_messages)
            else:
                return random.choice(self.fallback_goodbye_messages)

    async def _send_welcome_message(
        self, member: discord.Member, channel: discord.TextChannel
    ):
        """Send a welcome embed message."""
        try:
            # Generate welcome message
            welcome_text = await self._generate_message_with_llm(
                "welcome", member.display_name, member.guild.name
            )

            # Create embed
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}! 🎉",
                description=welcome_text,
                color=WELCOME_EMBED_COLOR,
                timestamp=discord.utils.utcnow(),
            )

            # Add member info
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name="Member", value=f"{member.mention} ({member.name})", inline=True
            )
            embed.add_field(
                name="Account Created",
                value=f"<t:{int(member.created_at.timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="Member Count", value=f"{member.guild.member_count}", inline=True
            )

            # Add footer (safely)
            footer_text = f"ID: {member.id}"
            footer_icon = None
            if member.guild.icon:
                footer_icon = member.guild.icon.url

            embed.set_footer(text=footer_text, icon_url=footer_icon)

            # Send the embed
            await channel.send(embed=embed)
            self.logger.info(f"Sent welcome message for {member.name}")

        except Exception as e:
            self.logger.error(f"Error sending welcome message: {str(e)}")

    async def _send_goodbye_message(
        self, member: discord.Member, channel: discord.TextChannel
    ):
        """Send a goodbye embed message."""
        try:
            # Generate goodbye message
            goodbye_text = await self._generate_message_with_llm(
                "goodbye", member.display_name, member.guild.name
            )

            # Create embed
            embed = discord.Embed(
                title=f"Goodbye! 👋",
                description=goodbye_text,
                color=GOODBYE_EMBED_COLOR,
                timestamp=discord.utils.utcnow(),
            )

            # Add member info
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Member", value=f"{member.name}", inline=True)

            # Calculate time on server if possible
            if member.joined_at:
                time_on_server = discord.utils.utcnow() - member.joined_at
                days = time_on_server.days
                hours, remainder = divmod(time_on_server.seconds, 3600)
                minutes, _ = divmod(remainder, 60)

                time_str = ""
                if days > 0:
                    time_str += f"{days} day{'s' if days != 1 else ''} "
                if hours > 0 or days > 0:
                    time_str += f"{hours} hour{'s' if hours != 1 else ''} "
                time_str += f"{minutes} minute{'s' if minutes != 1 else ''}"

                embed.add_field(name="Time on Server", value=time_str, inline=True)

            embed.add_field(
                name="Member Count", value=f"{member.guild.member_count}", inline=True
            )

            # Add footer (safely)
            footer_text = f"ID: {member.id}"
            footer_icon = None
            if member.guild.icon:
                footer_icon = member.guild.icon.url

            embed.set_footer(text=footer_text, icon_url=footer_icon)

            # Send the embed
            await channel.send(embed=embed)
            self.logger.info(f"Sent goodbye message for {member.name}")

        except Exception as e:
            self.logger.error(f"Error sending goodbye message: {str(e)}")

    async def _assign_role(self, member: discord.Member, role: discord.Role):
        """Assign a role to a member."""
        try:
            await member.add_roles(
                role, reason="Automatic role assignment for new member"
            )
            self.logger.info(f"Assigned role {role.name} to {member.name}")
        except discord.Forbidden:
            self.logger.error(f"No permission to add roles to {member.name}")
        except Exception as e:
            self.logger.error(f"Error assigning role: {str(e)}")

    @commands.command(name="setwelcomechannel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Set the welcome message channel.

        Args:
            channel: The channel to send welcome messages to. If not provided, shows current channel.
        """
        if not channel:
            current_channel = (
                self.bot.get_channel(WELCOME_CHANNEL_ID) if WELCOME_CHANNEL_ID else None
            )

            if current_channel:
                await ctx.send(f"Current welcome channel is {current_channel.mention}")
            else:
                await ctx.send("No welcome channel is currently set.")

            await ctx.send(
                f"Use `{ctx.prefix}setwelcomechannel #channel` to set a new channel."
            )
            return

        # In a real implementation, you would update this in a database
        # For now, we'll just acknowledge the command
        await ctx.send(f"Welcome channel would be set to {channel.mention}")
        await ctx.send(
            "Note: This command is just a placeholder. "
            f"To actually set the channel, update WELCOME_CHANNEL_ID in your .env file to: {channel.id}"
        )

    @commands.command(name="setgoodbyechannel")
    @commands.has_permissions(administrator=True)
    async def set_goodbye_channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Set the goodbye message channel.

        Args:
            channel: The channel to send goodbye messages to. If not provided, shows current channel.
        """
        if not channel:
            current_channel = (
                self.bot.get_channel(GOODBYE_CHANNEL_ID) if GOODBYE_CHANNEL_ID else None
            )

            if current_channel:
                await ctx.send(f"Current goodbye channel is {current_channel.mention}")
            else:
                await ctx.send("No goodbye channel is currently set.")

            await ctx.send(
                f"Use `{ctx.prefix}setgoodbyechannel #channel` to set a new channel."
            )
            return

        # In a real implementation, you would update this in a database
        # For now, we'll just acknowledge the command
        await ctx.send(f"Goodbye channel would be set to {channel.mention}")
        await ctx.send(
            "Note: This command is just a placeholder. "
            f"To actually set the channel, update GOODBYE_CHANNEL_ID in your .env file to: {channel.id}"
        )

    @commands.command(name="setdefaultrole")
    @commands.has_permissions(administrator=True)
    async def set_default_role(self, ctx: commands.Context, role: discord.Role = None):
        """
        Set the default role for new members.

        Args:
            role: The role to assign to new members. If not provided, shows current role.
        """
        if not role:
            current_role = (
                ctx.guild.get_role(DEFAULT_ROLE_ID) if DEFAULT_ROLE_ID else None
            )

            if current_role:
                await ctx.send(f"Current default role is {current_role.mention}")
            else:
                await ctx.send("No default role is currently set.")

            await ctx.send(
                f"Use `{ctx.prefix}setdefaultrole @role` to set a new default role."
            )
            return

        # In a real implementation, you would update this in a database
        # For now, we'll just acknowledge the command
        await ctx.send(f"Default role would be set to {role.mention}")
        await ctx.send(
            "Note: This command is just a placeholder. "
            f"To actually set the role, update DEFAULT_ROLE_ID in your .env file to: {role.id}"
        )

    @commands.command(name="testwelcome")
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx: commands.Context):
        """Test the welcome message by sending one for yourself."""
        welcome_channel = None
        if WELCOME_CHANNEL_ID:
            welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)

        if not welcome_channel:
            await ctx.send(
                "No welcome channel configured. Set WELCOME_CHANNEL_ID in your .env file."
            )
            return

        await self._send_welcome_message(ctx.author, welcome_channel)
        await ctx.send(f"Test welcome message sent to {welcome_channel.mention}")

    @commands.command(name="testgoodbye")
    @commands.has_permissions(administrator=True)
    async def test_goodbye(self, ctx: commands.Context):
        """Test the goodbye message by sending one for yourself."""
        goodbye_channel = None
        if GOODBYE_CHANNEL_ID:
            goodbye_channel = self.bot.get_channel(GOODBYE_CHANNEL_ID)

        if not goodbye_channel:
            await ctx.send(
                "No goodbye channel configured. Set GOODBYE_CHANNEL_ID in your .env file."
            )
            return

        await self._send_goodbye_message(ctx.author, goodbye_channel)
        await ctx.send(f"Test goodbye message sent to {goodbye_channel.mention}")


async def setup(bot: commands.Bot):
    """Add this cog to the bot."""
    await bot.add_cog(WelcomeCog(bot))
